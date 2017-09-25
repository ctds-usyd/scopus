#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import multiprocessing
import sys
import time
import os
import tarfile
import zipfile
import itertools
import functools
import warnings
from collections import defaultdict

import django
from django.utils.encoding import smart_str, smart_text
import django.db
from django.db import transaction

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
                         context={'eid': eid, 'obj': smart_text(obj)})
                setattr(obj, name, val[:max_length])

        return obj  # allow chaining

    for item_name, item_id in document['itemid'].items():
        itemids.append(truncate_fields(ItemID(document_id=eid, item_id=item_id, item_type=item_name)))

    (scopus_source_id,
     source_title,
     source_abbrev,
     source_type,
     issn_print,
     issn_electronic) = document['source']
    # NOTE: this table has a separate unique primary key
    source = Source(scopus_source_id=scopus_source_id,
                    issn_print=issn_print,
                    issn_electronic=issn_electronic,
                    source_type=smart_str(source_type),
                    source_title=smart_str(source_title),
                    source_abbrev=smart_str(source_abbrev),
                    )
    truncate_fields(source)

    documents.append(Document(eid=eid,
                              doi=smart_str(document['doi']),
                              group_id=document['group-id'],
                              title=smart_str(document['title']),
                              source=source,
                              citation_count=item['citation']['count'],
                              pub_year=document['pub-year'],
                              title_language=document['title_language'],
                              citation_type=document['citation_type']
                              ))

    truncate_fields(documents[-1])

    if document['abstract']:
        abstracts.append(Abstract(document_id=eid,
                                  abstract=document['abstract']))
        truncate_fields(abstracts[-1])

    for (author_id, initials, surname, order), affiliations in document['authors'].items():
        for afid, (affiliation_lines, country, city) in affiliations.items():
            authorships.append(Authorship(author_id=author_id,
                                          initials=smart_str(initials),
                                          surname=smart_str(surname),
                                          order=order,
                                          document_id=int(eid),
                                          affiliation_id=afid,
                                          affiliation='\n'.join(affiliation_lines),
                                          country=country,
                                          city=city,
                                          ))
            truncate_fields(authorships[-1])

    for citation in item['citation']['eid']:
        citations.append(Citation(cite_to=eid, cite_from=citation))

    return documents[-1], itemids, authorships, citations, abstracts


def _with_retry(func, retries=3, wait=1, wait_mul=5):
    # By default, wait 1s, 5s, 25s, 125s
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            if not retries:
                raise
            time.sleep(wait)
            return _with_retry(func,
                               retries=retries - 1,
                               wait=wait * wait_mul,
                               wait_mul=wait_mul)(*args, **kwargs)
    return wrapper


@transaction.atomic
def bulk_create(doc_records):
    documents, itemids, authorships, citations, abstracts = zip(*doc_records)
    Document.objects.bulk_create(documents)
    ItemID.objects.bulk_create(sum(itemids, []))
    Authorship.objects.bulk_create(sum(authorships, []))
    Citation.objects.bulk_create(sum(citations, []))
    Abstract.objects.bulk_create(sum(abstracts, []))


@transaction.atomic
def create_doc(doc_record):
    _with_retry(doc_record[0].save)()
    for same_model_objs in doc_record[1:]:
        for obj in same_model_objs:
            _with_retry(obj.save)()


def load_to_db(doc_records):
    """Save Django objects

    Save referenced sources first, then attempt to bulk create
    all documents and associated records atomically, falling
    back to creating each document and associated records atomically.
    """

    for doc_record in doc_records:
        doc = doc_record[0]
        source = doc.source
        try:
            db_source, created = _with_retry(Source.get_or_create)(
                scopus_source_id=source.scopus_source_id,
                issn_print=source.issn_print,
                issn_electronic=source.issn_electronic)
        except Exception:
            json_log(error='Loading to database failed',
                     context={'object': source},
                     exception=True)
        source.pk = db_source.pk
        if created:
            source.save()

    try:
        bulk_create(doc_records)
    except Exception:
        json_log(error='Falling back to one-by-one',
                 method=logging.debug)
        # When transaction as bulk is failed, then go through each query
        # one by one and create them. Also, log failed queries.
        for doc_record in doc_records:
            try:
                create_doc(doc_record)
            except Exception:
                json_log(error='Loading to database failed',
                         context={'eid': doc_record[0].eid},
                         exception=True)
    finally:
        # Avoid memory leak when DEBUG == True
        django.db.reset_queries()


def _generate_files(path):
    # XXX: Had some problems on windows with opening files. Will do so with
    # retries.
    if os.path.isdir(path):
        for child in os.listdir(path):
            child = os.path.join(path, child)
            if child.endswith('.xml'):
                yield child, _with_retry(open)(child, 'rb')
            else:
                for tup in _generate_files(child):
                    yield tup
    elif tarfile.is_tarfile(path):
        with _with_retry(tarfile.open)(path, 'r') as archive:
            for info in archive:
                yield info.path, archive.extractfile(info)
    elif zipfile.is_zipfile(path):
        archive = _with_retry(zipfile.ZipFile)(path, 'r')
        for info in archive.filelist:
            # zipfile cannot concurrently open multiple files :(
            yield info.filename, _with_retry(archive.open)(info)


def generate_xml_pairs(path, eid_filter=None, count_only=False):
    """Finds and returns contents for pairs of XML documents and citedby

    path may be:
        * a directory in which to find XML/TAR/ZIP files
        * a tar file
        * a zip file
    """
    n_skips = 0
    backlog = {}
    for path, f in _generate_files(path):
        if not path.endswith('.xml'):
            if f is not None:
                f.close()
            continue

        # TODO: filter before opening, or after pairing to avoid DB queries
        if eid_filter is not None \
           and eid_filter(int(os.path.dirname(path).rsplit('-')[-1])):
            n_skips += 1
            if n_skips % 100000 == 0:
                json_log(info='Skipped %d files so far' % n_skips,
                         method=logging.info)
            f.close()
            continue
        if count_only:
            xml = None
        else:
            xml = f.read()
            f.close()
        key = os.path.dirname(path)
        if key in backlog:
            other_path, other_xml = backlog.pop(key)
            if other_path == path:
                json_log(error='Found duplicate xmls for %r' % path,
                         method=logging.error)
                backlog[key] = (path, xml)
                continue
            if path.endswith('citedby.xml'):
                yield other_path, other_xml, xml
            else:
                assert other_path.endswith('citedby.xml'), other_path
                yield path, xml, other_xml

        else:
            backlog[key] = (path, xml)

    if n_skips:
        json_log(info='Skipped %d files (two per doc) altogether' % n_skips,
                 method=logging.warning)
    if backlog:
        json_log(error='Found unpaired XML files: %s'
                 % [path for path, _ in backlog.values()],
                 exception=True,
                 method=logging.error)


def _process_one(tup):
    path, doc_file, citedby_file = tup
    try:
        item = {'document': extract_document_information(doc_file),
                'citation': extract_document_citations(citedby_file)}
    except Exception:
        json_log(error='Uncaught error in extraction from XML',
                 context={'path': path},
                 exception=True)

    if item['document'] is not None:
        try:
            return aggregate_records(item)
        except Exception:
            json_log(error='Uncaught error in producing django records',
                     context={'eid': item['document'].get('eid')},
                     exception=True)


try:
    basestring
except NameError:
    basestring = str


def extract_and_load_docs(paths, pool=None):
    """Main driver for loading all XML from a path to a database

    Parameters
    ----------
    path : string

        This can either be a directory to be recursed (containing XML or Zip or
        TAR), or a single Zip or TAR file.
    """
    if isinstance(paths, basestring):
        paths = [paths]

    def already_saved(eid):
        return Document.objects.filter(eid=eid).exists()

    xml_pairs = itertools.chain.from_iterable(
        generate_xml_pairs(path, _with_retry(already_saved))
        for path in paths)

    if pool is None:
        try:
            from itertools import imap
        except ImportError:
            imap = map
    else:
        imap = functools.partial(pool.imap_unordered, chunksize=200)

    counter = -1
    doc_records = []

    for counter, doc_record in enumerate(imap(_process_one, xml_pairs)):
        if counter % MAX_BATCH_SIZE == 0:
            if counter > 0:
                logging.info('Saving after %d records' % counter)
                load_to_db(doc_records)
            doc_records = []

        if doc_record is None:
            continue

        doc_records.append(doc_record)

    if counter < 0:
        json_log(error='Processed 0 records!', method=logging.error)
        return

    # At end of the year, flush out all remaining records
    logging.info('Saving after %d records' % counter)
    load_to_db(doc_records)
    logging.info('Done')


def main():
    ap = argparse.ArgumentParser('Extract Scopus snapshot to database')
    ap.add_argument('-j', '--jobs', type=int, default=1,
                    help='Number of concurrent workers. FIXME: this appears to degrade performance significantly, at least on Windows')
    ap.add_argument('--count-only', action='store_true', default=False,
                    help='Do not load. Only count how many documents there are to load.')
    ap.add_argument('paths', nargs='+',
                    help='Scopus XML files or directories, zips or tars thereof')
    args = ap.parse_args()

    FORMAT = "%(asctime)-15s %(message)s"
    logging.basicConfig(format=FORMAT)

    if args.count_only:
        logging.warning('COUNTING ONLY')
        count = -1
        gen = itertools.chain.from_iterable(generate_xml_pairs(path, count_only=True)
                                            for path in args.paths)
        for count, (path, _, _) in enumerate(gen):
            if (count + 1) % 100000 == 0:
                logging.warning('Found %d XML pairs so far. Up to %s' % (count + 1, path))
        logging.warning('Found %d XML pairs (i.e. Documents)'
                        % (count + 1,))
        return

    logging.info('Extracting from XML in %d processes' % max(1, args.jobs))
    if args.jobs > 1:
        pool = multiprocessing.Pool(processes=args.jobs)
    else:
        pool = None

    warnings.filterwarnings('ignore', category=UnicodeWarning,
                            module='.*sqlserver_ado.*')
    extract_and_load_docs(args.paths, pool=pool)

    if pool is not None:
        pool.close()
        pool.join()


if __name__ == '__main__':
    main()
