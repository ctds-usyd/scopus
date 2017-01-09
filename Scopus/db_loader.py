#!/usr/bin/env python
# coding: utf-8

import logging
import multiprocessing
import sys
import time
import os
import tarfile
import zipfile

import django
from django.utils.encoding import smart_str
import django.db

django.setup()

from Scopus.models import (
    ItemID,
    Source,
    Document,
    Citation,
    Authorship,
    Abstract,
)
from Scopus.xml_extract import (
    extract_document_information,
    extract_document_citations,
    json_log,
)


# Higher value for MAX_BATCH_SIZE increases the speed of loading data to DB since
# it opens/closes the connection once per MAX_BATCH_SIZE of records.
MAX_BATCH_SIZE = 5000


def aggregate_records(item):
    """Creates Django model objects from an object produced in xml_extract

    Parameters
    ----------
    item : dict
        Key 'document' points to the output of `extract_document_information`.
        Key 'citation' points to the output of `extract_document_citations`.
    """
    itemids = []
    authorships = []
    citations = []
    documents = []
    abstracts = []

    document = item['document']
    eid = document['eid']

    def truncate_fields(obj):
        try:
            # memoize
            trunc_data = obj._meta.trunc_data
        except AttributeError:
            trunc_data = [(f.name, f.max_length)
                          for f in obj._meta.get_fields()
                          if getattr(f, 'max_length', None) is not None]
            obj._meta.trunc_data = trunc_data

        for name, max_length in trunc_data:
            val = getattr(obj, name, None)
            if val is not None and len(val) > max_length:
                json_log(error='Truncation of oversize {}.{} (max_length={})'.format(type(obj).__name__, name, max_length),
                         length=len(val),
                         context={'eid': eid, 'obj': str(obj)})
                setattr(obj, name, val[:max_length])

        return obj  # allow chaining

    for item_name, item_id in document['itemid'].items():
        itemids.append(truncate_fields(ItemID(document_id=eid, item_id=item_id, item_type=item_name)))

    (source_id,
     source_title,
     source_abbrev,
     source_type,
     issn_print,
     issn_electronic) = document['source']
    db_source, created = Source.get_or_create(source_id=source_id,
                                              issn_print=issn_print,
                                              issn_electronic=issn_electronic)
    if created:
        db_source.source_type = smart_str(source_type)
        db_source.source_title = smart_str(source_title)
        db_source.source_abbrev = smart_str(source_abbrev)
        truncate_fields(db_source)
        db_source.save()

    documents.append(Document(eid=eid,
                              doi=document['doi'],
                              group_id=document['group-id'],
                              title=smart_str(document['title']),
                              source=db_source,
                              citation_count=item['citation']['count'],
                              pub_year=document['pub-year'],
                              title_language=document['title_language'],
                              citation_type=document['citation_type']
                              ))

    truncate_fields(documents[-1])

    abstracts.append(Abstract(document_id=eid,
                              abstract=document['abstract']))
    truncate_fields(abstracts[-1])

    for (author_id, initials, surname, order), affiliations in document['authors'].items():
        for afid, (department, organization, country, city) in affiliations.items():
            authorships.append(Authorship(author_id=author_id,
                                          initials=smart_str(initials),
                                          surname=smart_str(surname),
                                          order=order,
                                          document_id=int(eid),
                                          affiliation_id=afid,
                                          organization=smart_str(organization),
                                          department=smart_str(department),
                                          country=country,
                                          city=city))
            truncate_fields(authorships[-1])

    for citation in item['citation']['eid']:
        citations.append(Citation(cite_to=eid, cite_from=citation))

    return itemids, authorships, citations, documents, abstracts


def create_queries_one_by_one(queries):
    """Creates objects in DB individually
    
    Used when bulk create fails
    """
    # iterates over each query
    for query in queries:
        try:
            query.save()
        except Exception:
            json_log(error='Loading to database failed', context=str(query), exception=True)


def bulk_create(queries):
    """Create all objects in the database

    Objects in queries must all be of the same class
    """
    model = queries[0].__class__
    try:
        model.objects.bulk_create(queries)
    except Exception:
        # When transaction as bulk is failed, then go through each query
        # one by one and create them. Also, log failed queries.
        create_queries_one_by_one(queries=queries)

    # Avoid memory leak when DEBUG == True
    django.db.reset_queries()


def load_to_db(itemids, authorships, citations, documents, abstracts):
    """Save Django objects in bulk"""
    bulk_create(queries=documents)
    bulk_create(queries=itemids)
    bulk_create(queries=authorships)
    bulk_create(queries=citations)
    bulk_create(queries=abstracts)


def _generate_files(path):
    if os.path.isdir(path):
        for child in os.listdir(path):
            child = os.path.join(path, child)
            if child.endswith('.xml'):
                yield child, open(child, 'rb')
            else:
                for tup in _generate_files(child):
                    yield tup
    elif tarfile.is_tarfile(path):
        with tarfile.open(path, 'r') as archive:
            for info in archive:
                yield info.path, archive.extractfile(info)
    elif zipfile.is_zipfile(path):
        archive = zipfile.ZipFile(path, 'r')
        for info in archive.filelist:
            # zipfile cannot concurrently open multiple files :(
            yield info.filename, archive.open(info)


def generate_xml_pairs(path):
    """Finds and returns contents for pairs of XML documents and citedby

    path may be:
        * a directory in which to find XML/TAR/ZIP files
        * a tar file
        * a zip file
    """
    backlog = {}
    for path, f in _generate_files(path):
        if not path.endswith('.xml'):
            continue
        xml = f.read()
        key = os.path.dirname(path)
        if key in backlog:
            other_path, other_xml = backlog.pop(key)
            if other_path == path:
                logging.error('Found duplicate xmls for %r' % path)
                backlog[key] = (path, xml)
                continue
            if path.endswith('citedby.xml'):
                yield other_path, other_xml, xml
            else:
                assert other_path.endswith('citedby.xml'), other_path
                yield path, xml, other_xml

        else:
            backlog[key] = (path, xml)

    if backlog:
        json_log(error='Found unpaired XML files: %s' % [path for path, _ in backlog.values()], exception=True)


def extract_and_load_docs(path):
    """Main driver for loading all XML from a path to a database

    Parameters
    ----------
    path : string

        This can either be a directory to be recursed (containing XML or Zip or
        TAR), or a single Zip or TAR file.
    """
    counter = -1
    itemid_batch = []
    authorship_batch = []
    document_batch = []
    citation_batch = []
    abstract_batch = []

    for counter, (path, doc_file, citedby_file) in enumerate(generate_xml_pairs(path)):
        if counter % MAX_BATCH_SIZE == 0:
            if counter > 0:
                logging.info('Saving after %d records' % counter)
                load_to_db(itemid_batch, authorship_batch,
                           citation_batch, document_batch,
                           abstract_batch)
            itemid_batch = []
            authorship_batch = []
            document_batch = []
            citation_batch = []
            abstract_batch = []

        item = {'document': extract_document_information(doc_file),
                'citation': extract_document_citations(citedby_file)}

        if item['document'] is not None:
            (itemids, authorships, citations, documents, abstracts) = aggregate_records(item)
            itemid_batch.extend(itemids)
            authorship_batch.extend(authorships)
            citation_batch.extend(citations)
            document_batch.extend(documents)
            abstract_batch.extend(abstracts)

    if counter < 0:
        json_log(error='Processed 0 records!', exception=True)
        return

    # At end of the year, flush out all remaining records
    logging.info('Saving after %d records' % counter)
    load_to_db(itemid_batch, authorship_batch, citation_batch, document_batch, abstract_batch)
    logging.info('Done')


class Process(multiprocessing.Process):
    def __init__(self, path):
        super(Process, self).__init__()
        self.path = path

    def run(self):
        json_log(info='Started {}'.format(self.path))
        start = time.time()
        extract_and_load_docs(self.path)
        json_log(info='Processing of {} took {} seconds'.format(self.path, time.time() - start))

if __name__ == '__main__':
    paths = sys.argv[1:]
    for path in paths:
        Process(path).start()
