# Elsevier Scopus custom data extraction and RDBMS export

This tool extacts data from the Elsevier Scopus Snapshot XML to a more usable Relational Database Structure.

The loader is incremental and atomically consistent, such that it should be possible to start, stop and restart extraction on the same dataset without making the documents stalled inconsistent.
This incrementality, however, assumes that the documents and related data are fixed across restarts.

The below documentation describes running the tool and the schema of the database.

## Setup and Running

The loading script should ideally be on the same machine as the source data,
which can remain zipped (but not encrypted; see below) for the process to run.
If it is not on the same machine, it should be mounted/mapped locally.

The loading script need not be on the same machine as the target database.

### Windows and MSSQL setup

This presents running the loader Windows for a MSSQL instance. As an alternative, you could run the loader on a non-Windows machine using [`django-pyodbc`](https://pypi.python.org/pypi/django-pyodbc).

#### Python setup

The simplest way to install Python with libxml etc. is to [get Anaconda](https://www.continuum.io/downloads) for Python 2 ([version at time of writing](https://repo.continuum.io/archive/Anaconda2-4.4.0-Windows-x86_64.exe)). Install it and check the option to include Anaconda on the `PATH`.

#### Loader setup

[Download this repository](https://github.com/ctds-usyd/scopus/archive/master.zip)
and extract it to a new directory, say `E:\scopus-extract`.

In the command prompt, go to `E:\scopus-extract` and run the following two commands:

```
E:\scopus-extract> conda install -y lxml
E:\scopus-extract> pip install django-mssql==1.8 --editable=.
```

#### Create tables in database

* **Modify the file `~/scopus-extract/Scopus/db_settings.py` to reflect your MSSQL database instance.** For instance:

  ```
  DATABASES = {
      'default': {
          'ENGINE': 'sqlserver_ado',
          'NAME': '<INSERT DB NAME>',
          'USER': '<INSERT USER>',
          'PASSWORD': '<INSERT PASSWORD>',
          'HOST': '<INSERT HOST URL>',
          'OPTIONS': {
              'provider': 'SQLOLEDB',
              'use_legacy_date_fields': 'True'
          },
      }
  }
  ```

* Run `python manage.py migrate` in the terminal to set up the DB tables


#### Run the loading

* Ensure the data is decrypted and available in Zips.

* If all the zipped scopus data is in a directory `E:\path\to\scopus-data` you can simply use:
  `extract_to_db.bat E:\path\to\scopus-data 2> logfile.txt`.

* Tips:

    * you could also specify the individual Zip files instead of their containing directory
    * you should log the output to a file
    * in case something breaks or needs to be stopped, it should be safe to run the
      extraction multiple times on the same data

### Linux/Unix and MySQL setup

#### Requirements

You require the following in the loading environment:

* a Bash terminal
* Python 2.7 or >=3.3
* MySQL client libraries on the loading machine
* libxml2

#### MySQL setup

* Create a database in MySQL shell of the server
    * `create database <DATABASE_NAME> CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;`
      (MySQL doesn't support complete utf-8 encoding, so the encoding should be converted to `utf8mb4`)
    to the end of the above command
* Ensure batch processing is enabled on database ( if using MySQL < 5.5):
    * `set global net_buffer_length=1000000;`
    * `set global max_allowed_packet=1000000000;`

#### Loader setup

[Download this repository](https://github.com/ctds-usyd/scopus/archive/master.zip)
and extract it to a new directory, say `~/scopus-extract`.

In `~/scopus-extract`, run

```bash
$ pip install mysqlclient --editable=.
```

#### Create tables in database

* **Modify the file `~/scopus-extract/Scopus/db_settings.py` to reflect your MySQL database instance.**
* Run `python manage.py migrate` in the terminal to set up the DB tables

#### Run the loading


* Ensure the data is decrypted and available in Zips.
You can use the included script `batch_ungpg.sh` to do this easily in Linux/Unix.

* If all the zipped scopus data is in a directory `/path/to/scopus-data` you can simply use:
  `./extract_to_db.sh /path/to/scopus-data`.

* Tips:

    * you could also specify the individual Zip files instead of their containing directory
    * you might want to use `nohup` to avoid the process closing when the session ends
    * you should log the output to a file
    * in case something breaks or needs to be stopped, it should be safe to run the
      extraction multiple times on the same data

An example invocation:

```bash
$ nohup ./extract_to_db.sh /home/compressed-scopus/2011/ 2> 2011.txt
```

## Schema

We only attmept to represent a limited subset of the fields per document.

`Scopus/models.py` uses the [Django Object Relational Model
(ORM)](https://docs.djangoproject.com/en/1.10/topics/db/) to represent the
relational schema for the fields we extract. (Although tested with MySQL, it
should be possible to use this ORM with other database backends like
PostgreSQL, SQLite, etc.)

The tables ("models" in Django terminology) we store are:

* `Document`: an article with a unique Scopus EID
* `Source`: where the document was published (a particular journal, conference proceedings, etc.)
* `Authorship`: authors, their order and affiliation. Note that the affiliation name is given as a text field with affiliations (e.g. department and university) separated by newline characters.
* `ItemID`: list of alternative IDs registered for the docoument
* `Citation`: which publications in the Scopus database cited a document
* `Abstract`: the abstract fields of documents

We use **Scopus IDs** where we can, notably:

* `Document.eid` (the table's primary key) is the document's EID
* `Document.group_id`, to our understanding is used when Elsevier discovers
  that multiple EIDs correspond to the same document. Usually, `group_id` and `eid` are identical. In practice, it might be good to ignore records with `eid` differing from `group_id`.
* `Source.scopus_source_id` is Elsevier's ID for a source (`srcid`). It can, for instance be plugged into `https://www.scopus.com/sourceid/<scopus_source_id>` to get Elsevier's web-based representation of the source.
* `Authorship.author_id` is Elsevier's ID for an author (`auid`)
* `Authorship.affiliation_id` is Elsevier's ID for an affiliation (`afid`)

While we tend to avoid explicit foriegn keys to avoid database overhead, the
following **relationships** hold between tables:

* `Document.source_id` refers to `Source.id`
  (NOTE: *not* `Source.scopus_source_id`)
* `Authorship.document_id` refers to `Document.eid`
* `ItemID.document_id` refers to `Document.eid`
* `Citation.cite_to` refers to `Document.eid`
* `Citation.cite_from` refers to `Document.eid`

Fields are described in the `models.py` file and in the Django-admin interface
(see below).

Please note that for a `ForeignKey` declaration like the following, Django
appends `_id` to create the actual field name stored in the relational DB:

```python
class Document(django.db.models.Model):
    ...
    source = django.db.models.ForeignKey(Source)
    ...
```

results in:

```sql
CREATE TABLE "document" (
...
"source_id" BIGINT NULL REFERENCES "source" ("source_id")
...
);
```

### Limited source details

In order to keep the `Source` table simple, we do not include many details,
such as volume and issue number, or ISBN for monographs.

We also store at most one print and electronic ISSN on each `Source` record.
Since a single journal may have, for instance, changed names over time, and
hence may have multiple ISSNs over time, there may be multiple `Source`
records for what Scopus considers a single source ID.

### Multiple authorship

Rather than store authors and affiliations as distinct tables, we denormalise
the data for authorship. The order of authorship (first author, second author,
etc.) is indicated by the `Authorship.order` fields. There may be multiple
`Authorship` records for each `(document, order)` pair. This usually happens
when an author has *multiple affiliations*. Thus each record should indicate
the relationship between a document, an author, and an affiliation.
(Some documents in the dataset lack an affiliation or author ID, so these may
be `NULL`.)

## Input

The Scopus data is provided as a series of XML files, grouped together and
compressed with Zip, then encrypted with GPG.

Since XML tends to have high compression rates, our loader works directly with
Zip files (please decrypt first), rather than worry about disk/network I/O
latency for transferring large quantities of raw XML.

Within the Zip, each document is represented by two files, such as:

* `2014/eids-from-100001-to-110000/2-s2.0-84893747227/2-s2.0-84893747227.xml`
* `2014/eids-from-100001-to-110000/2-s2.0-84893747227/citedby.xml`

Here the document's ID, called an EID, is an integer `84893747227`. The prefix
`2-s2.0-` is constant and appears to references the Scopus extraction version.

The first file, `2-s2.0-84893747227.xml` stores most of the data about a single
article, as defined by [this
XSD](http://schema.elsevier.com/dtds/document/abstracts/xocs-ani512.xsd) and
[documented
here](http://ebrp.elsevier.com/pdf/Scopus_Custom_Data_Documentation_v4.pdf).
`citedby.xml` stores information about the documents that cite EID
`84893747227`.

## XML to Python dicts

`Scopus/xml_extract.py` initially extracts the fields we need from XML. It uses
[XPath](http://www.w3schools.com/xml/xpath_intro.asp) via
[`lxml.etree`](http://lxml.de/) to extract specific elements from the document,
and performs some cleaning on the result, to produce an intermediate
representation.

### Quality assurance in the loader

The relational schema tends to rely on fields having single values, while XML
(when licensed by the XSD) allows them to have zero or more values. We try to
ensure that we have identified anomalies in the data. To do so we use a helper
function, `xpath_get_one` which will, by default, give a warning if no element
matches the XPath query, or if more than one matches the XPath query. After
analysing some cases where warnings were triggered, we have resolved issues and
disabled warnings where we felt appropriate.

Exceptions raised in the extraction process are also logged.

Log messages here are output as valid JSON so that they can be aggregated and
analysed using any tools capable of processing JSON.

### Standalone extraction

The extraction code is written to be independent of the database schema and
storage. You can therefore:

* run it as a standalone script: given XML paths on the command-line, it will
  pretty-print out the extracted Python dicts.
* use it as a library: using `extract_document_information` from
  `Scopus.xml_extract` processes a main path (like `2-s2.0-84893747227.xml`)
  and `extract_document_citations` processes a `citedby.xml`. Both return the
  internally used dict structures.

This allows the extraction to be used to feed into a different storage
solution (e.g. a graph database).

## Python dicts to relational database

`Scopus/db_loader.py` manages loading into a relational database, making use of
`xml_extract`. It will output progress messages such as:
```
WARNING:root:Record 2-s2.0-0142168590.xml from 2003 was processed.
```
Records are stored in large batches, so progress reporting is infrequent.

## Viewing the data with Django-admin

**This feature is currently disabled in order to handle the shambles of MSSQL support!**

The data and its relationships can be viewed and searched using a largely automatic interface provided by django.

After the data is loaded, first create a user:

```bash
$ ./manage.py createsuperuser
```

then run a server instance (note that `runserver` is not very secure; see
[deployment docs](https://docs.djangoproject.com/en/1.10/howto/deployment/) for
more robust configurations, and do not open `runserver` to a public IP address):

```bash
$ ./manage.py runserver
Performing system checks...
System check identified no issues (0 silenced).
November 09, 2016 - 01:25:22
Django version 1.10.2, using settings 'Scopus.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

Open `http://127.0.0.1:8000/` to browse.

## Advanced: Log analysis

Most errors and warnings in the loader logs will be output with each log entry
as a separate JSON object.  They can be analysed using UNIX tools and
[jq](https://stedolan.github.io/jq/) or another tool for analysing JSON.

The following will find the most frequent issues in the log files:

```
cat *.log | grep -o '{"context.*' |
    jq -c 'del(.context) | del(.length) | del(.exception)' |
    sort | uniq -c | sort -n
```

The following will print any exception tracebacks:

```
cat *.log | grep -o '{"context.*' |
    jq -r 'select(.error == "Loading to database failed") |
           "::\(. | del(.exception))::\n \(.exception)"'
```

## Authors

This package has been developed by Nikzad Babaii Rizvandi and Joel Nothman within the Sydney Informatics Hub. Copyright ©2016-2017, University of Sydney.
