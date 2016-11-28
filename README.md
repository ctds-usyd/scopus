# Elsevier Scopus custom data extraction and RDBMS export

<h1> Dependencies </h1>

* Python 2.7 or >=3.3
* MySQL

<h1> Setup and Running </h1>

<h3> MySQL </h3>

* Create a database in MySQL shell of the server 
    * `create database <DATABASE_NAME>; 
    * If using MySQL 7.1, add `character set utf8 collate utf8_general_ci;` 
    to the end of the above command
* Ensure batch processing is enabled on database:
    * `set global net_buffer_length=1000000;`
    * `set global max_allowed_packet=1000000000;`

<h3> Code </h3>

Copy the code to the server at `LINK_TO_THE_PROJECT_DIRECTORY`

<h3> Server </h3>
If there is a virtualenv on the server, type `workon <VM_NAME>` in shell to start the VM. Otherwise, 
create one as following:

* Install `pip`
* Install python virtualenv as
    * `pip install --upgrade virtualenv`
    * `pip install --upgrade virtualenvwrapper` (if it gives error 
   add `--ignore-installed six` to the end of the line)
    * In `~/.profile`, add
        *  `export WORKON_HOME=$HOME/.virtualenvs`
        *  `export PROJECT_HOME=$HOME/Projects`
        *  `source /usr/local/bin/virtualenvwrapper.sh`
    * Create `scopus_vm` virtual vm (as an example)
        * `mkvirtualenv scopus_vm --python=$HOME/<LINK_TO_PYTHON>`
    * In `~/.virtualenvs/scopus_vm/bin/postactivate` add
        * `cd <LINK_TO_THE_PROJECT_DIRECTORY>`
    * Start VM by typing `workon scopus_vm` 

<h3> Install python packages </h3>

* Start VM by typing `workon scopus_vm`  
* `pip install -r requirements.txt`

<h3> Create tables in database </h3>

* Modify the database settings in the `DATABASES` at `Scopus/settings.py`.
* `./manage.py migrate  # set up DB tables`

<h3> Running </h3>

* Ensure the data is decrypted and available in Zips.
You can use the included script `batch_ungpg.sh` to do this easily.

* `./extract_to_db.sh /path/to/zipfile1.zip /path/to/zipfile2.zip ...`
  
  as an example is: 
  
  `nohup ./extract_to_db.sh /home/compressed-scopus/2011/ > 2011.txt`



## Schema

We only attmept to represent a limited subset of the fields per document.

`Scopus/models.py` uses the [Django Object Relational Model
(ORM)](https://docs.djangoproject.com/en/1.10/topics/db/) to represent the
relational schema for the fields we extract. (Although tested with MySQL, it
should be possible to use this ORM with other database backends like
PostgreSQL, SQLite, etc.)

The tables ("models" in Django terminology) we store are:

* `Document`: an article with a unique Scopus EID
* `Source`: where the document was published
* `Authorship`: authors, their order and affiliation
* `ItemID`: list of alternative IDs registered for the docoument
* `Citation`: which publications in the Scopus database cited a document

We use **Scopus IDs** where we can, notably:

* `Document.eid` (the table's primary key) is the document's EID
* `Document.group_id`, to our understanding is used when Elsevier discovers
  that multiple EIDs correspond to the same document.
* `Source.source_id` (the table's primary key) is Elsevier's ID for a source (`srcid`)
* `Authorship.author_id` is Elsevier's ID for an author (`auid`)
* `Authorship.affiliation_id` is Elsevier's ID for an affiliation (`afid`)

While we tend to avoid explicit foriegn keys to avoid database overhead, the
following **relationships** hold between tables:

* `Document.source_id` refers to `Source.source_id`
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

We also store at most one print and electronic ISSN on each `Source` record,
although it is *possible* that there are multiple ISSNs for each Scopus
`source_id`.

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

The data and its relationships can be viewed and searched using a largely automatic interface provided by django.

After the data is loaded, first create a user:

```bash
$ ./manage.py createsuperuser
```

then run a server instance (note that `runserver` is not very secure; see
[deployment docs](https://docs.djangoproject.com/en/1.10/howto/deployment/) for
more robust configurations):

```bash
$ ./manage.py runserver
Performing system checks...
System check identified no issues (0 silenced).
November 09, 2016 - 01:25:22
Django version 1.10.2, using settings 'Scopus.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

Open `http://127.0.0.1:8000/admin` to browse.
