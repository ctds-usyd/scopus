from lxml import etree
from collections import defaultdict
import logging
import json
import traceback
import re

from django.utils.encoding import smart_text


def id_to_int(x):
    """Clean Scopus ID string used in filenames"""
    return int(x.split('2-s2.0-')[1])


def json_log(method=logging.warning, **kwargs):
    """Issue a log as a JSON object"""
    if kwargs.get('exception'):
        kwargs['exception'] = traceback.format_exc()
    method(json.dumps(kwargs, sort_keys=True))


NAMESPACES = {
    'xocs': "http://www.elsevier.com/xml/xocs/dtd",
    'cto': "http://www.elsevier.com/xml/cto/dtd",
    'ce': "http://www.elsevier.com/xml/ani/common",
}


def xpath_get_one(root, path, context=None, default=None, warn_zero=True):
    """Match an XPath that is expected to return exactly one result

    Assures quality by logging when this expectation is violated, i.e. the
    XPath returns 0 results (logged if warn_zero is True) or more than 1.

    Parameters
    ----------
    root : lXML element
        Evaluate XPath relative to this node
    path : string
        An XPath
    context : dict, optional
        Information to report in an error
    default : any, optional
        If no object is matched, return this value
    warn_zero : boolean, default True
        Whether it is offensive for the query to return no results,
        and therefore a warning should be logged.
    """
    out = root.xpath(path, namespaces=NAMESPACES)
    if len(out) == 1:
        return out[0]
    if len(out) > 1:
        json_log(error='Got {} expected 1'.format(len(out)),
                 xpath=path,
                 context=context)
        return out[0]
    # Got zero
    if warn_zero:
        json_log(error='Got 0 expected 1',
                 xpath=path,
                 context=context)
    return default


def int_or_none(x):
    if x is None:
        return None
    return int(x)


def _get_data_from_doc(document, eid):
    def doc_get_one(path, **kwargs):
        return xpath_get_one(document, path, context={'eid': eid}, **kwargs)

    def _handle_unicode(text, default='', encoding='utf-8', errors='ignore'):
        try:
            return smart_text(text, encoding=encoding, errors=errors)
        except Exception:
            json_log(error='Encoding to `utf-8` failed', context={'eid': eid}, exception=True)
            return default

    def clean_text(node, default=''):
        if node is None:
            return default
        text = "".join(x for x in node.itertext())
        return _handle_unicode(text=re.sub('\s+', ' ', text).strip(), default=default)

    abstract_node = doc_get_one('/xocs:doc/xocs:item/item/bibrecord/head/abstracts/abstract[@original="y"]//ce:para', warn_zero=False)
    pub_year = int(doc_get_one('/xocs:doc/xocs:meta/xocs:pub-year/text()', default=-1, warn_zero=False))
    if pub_year == -1:
        pub_year = int(doc_get_one('/xocs:doc/xocs:meta/xocs:sort-year/text()', default=-1))

    doi_node = doc_get_one('/xocs:doc/xocs:meta/xocs:doi/text()', warn_zero=False)
    data = {
        'eid': eid,
        'pub-year': pub_year,
        'group-id': int(doc_get_one('/xocs:doc/xocs:meta/cto:group-id/text()')),
        'title': clean_text(doc_get_one('/xocs:doc/xocs:item/item/bibrecord/head/citation-title/titletext[@original="y"]')),
        'citation_type': doc_get_one('/xocs:doc/xocs:item/item/bibrecord/head/citation-info/citation-type/@*', default = ''),
        'title_language': doc_get_one('/xocs:doc/xocs:item/item/bibrecord/head/citation-title/titletext[@original="y"]/@xml:lang',
                                      default='und') or 'und',  # language undetermined as per http://www.loc.gov/standards/iso639-2/faq.html#25
        'abstract': clean_text(abstract_node),
        'doi': _handle_unicode(doi_node),
    }

    itemids = document.xpath('/xocs:doc/xocs:item/item/bibrecord/item-info/itemidlist/itemid', namespaces=NAMESPACES)
    try:
        data['itemid'] = {item.attrib['idtype']: item.text for item in itemids}
    except KeyError:
        json_log(eid=eid, error='Could not get idtype for itemid {!r}'.format(item.text), exception=True)

    source = doc_get_one('/xocs:doc/xocs:item/item/bibrecord/head/source')
    if source is None:
        data['source'] = (None,) * 6
    else:
        abbrev = source.find('sourcetitle-abbrev')
        srcid = source.get('srcid', -1)
        data['source'] = (srcid,
                          clean_text(source.find('sourcetitle')),
                          clean_text(abbrev) if abbrev is not None else '',
                          xpath_get_one(source, './@type', context={'eid': eid, 'srcid': srcid}, warn_zero=False, default=''),
                          xpath_get_one(source, './/issn[@type=\'print\']/text()', context={'eid': eid, 'srcid': srcid}, warn_zero=False),
                          xpath_get_one(source, './/issn[@type=\'electronic\']/text()', context={'eid': eid, 'srcid': srcid}, warn_zero=False),
                          )

    authors_groups = document.xpath('/xocs:doc/xocs:item/item/bibrecord/head/author-group', namespaces=NAMESPACES)

    authors_list = defaultdict(dict)
    for authors_group in authors_groups:
        affiliation = xpath_get_one(authors_group, './/affiliation', context={'eid': eid}, warn_zero=False)
        country, city = '', ''
        organization_lines = []
        afid = None
        try:
            if affiliation is not None:
                afid = int_or_none(affiliation.get('afid'))
                country = affiliation.get('country', '')
                city_group = affiliation.get('city-group', '')
                state = affiliation.get('state', '')
                city = affiliation.get('city', '')
                if not city:
                    city = city_group
                elif city_group:
                    json_log(context={'eid': eid},
                             error='city-group and city elements both present: '
                                   'city={!r}, city-group={!r}'.format(city, city_group))
                if state:
                    city += ', ' + state
                organization_list = affiliation.findall('organization')
                organization_lines = [clean_text(el) for el in organization_list]
        except Exception as e:
            json_log(context={'eid': eid, 'afid': afid}, exception=True)

        for author in authors_group.findall('author'):
            author_context = {'eid': eid, 'afid': afid}
            author_id = int_or_none(xpath_get_one(author, '@auid', context=author_context, warn_zero=False))
            author_context['auid'] = author_id
            seq = xpath_get_one(author, '@seq', context=author_context, default=1, warn_zero=False)
            if seq == '':
                seq = 1
                n_authors = len(document.xpath('/xocs:doc/xocs:item/item/bibrecord/head//author',
                                               namespaces=NAMESPACES))
                json_log(context=author_context, error='Found empty string in `seq` attribute. Setting to 1',
                         n_author_nodes=n_authors)
            surname = clean_text(xpath_get_one(author, './ce:surname', context=author_context))
            initials_node = xpath_get_one(author, './ce:initials', context=author_context, warn_zero=False)
            initials = clean_text(initials_node) if initials_node is not None else None
            authors_list[author_id, initials, surname, seq][afid] = (organization_lines, country, city)

    if len(set(seq for _, _, _, seq in authors_list)) < len(authors_list):
        # Happens quite frequently, with multiple alternative name extractions for same author
        json_log(error='Found duplicate `seq` values for authors: {!r}'.format(authors_list.keys()),
                 context={'eid': eid},
                 method=logging.debug)

    data['authors'] = dict(authors_list)

    return data


def _parse(f):
    if hasattr(f, 'startswith') and f.startswith(b'<'):
        return etree.fromstring(f)
    return etree.parse(f)


def extract_document_information(document):
    """Extract information from XML file of the document.

    Information includes but not limited to:
    - title
    - authors
    - authors' affiliations
    - number of citations and their ids
    - description
    - keywords (if any)
    - catagory

    Parameters
    ----------
    document : XML string, path string or file object

    Returns
    -------
    data : None in case of exception; otherwise dict
        The returned dict has a custom structure
    """
    document = _parse(document)

    eid = id_to_int(xpath_get_one(document, '/xocs:doc/xocs:meta/xocs:eid/text()'))
    try:
        data = _get_data_from_doc(document, eid)
    except Exception:
        json_log(method=logging.error, context={'eid': eid}, exception=True)
        return

    return data


def extract_document_citations(citation):
    """Extract information from citedby XML file.

    Parameters
    ----------
    document : XML string, path string or file object

    Returns
    -------
    dict
    """
    citation = _parse(citation)
    citations = citation.findall('citing-doc')
    count = int(citation.find('count').text)
    return {'count': count,
            'eid': [id_to_int(ct.find('eid').text)
                    for ct in citations if citations]}


if __name__ == '__main__':
    import sys
    import os
    import pprint
    for path in sys.argv[1:]:
        with open(path) as f:
            if os.path.basename(path) == 'citedby.xml':
                print(path)
                pprint.pprint(extract_document_citations(f))
            else:
                print(path)
                pprint.pprint(extract_document_information(f))

    # Logs can be analysed with:
    #  cat | cut -d: -f3- | jq -c '.context_keys = (.context | keys) | del(.context)' | sort | uniq -c | sort -n
