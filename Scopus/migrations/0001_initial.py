# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Authorship',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('author_id', models.BigIntegerField(help_text=b"Scopus's auid", null=True, db_index=True, blank=True)),
                ('initials', models.CharField(default=b'', max_length=20)),
                ('surname', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField(default=0, help_text=b'1 for first author, etc. Can have multiple Authorship entries for one value of order.')),
                ('affiliation_id', models.IntegerField(help_text=b"Scopus's afid", null=True, db_index=True)),
                ('organization', models.CharField(default=b'', help_text=b'Name from 1st organization node in affiliation details', max_length=300, db_index=True)),
                ('department', models.CharField(default=b'', help_text=b'Name from 2nd organization node in affiliation details', max_length=200)),
                ('country', models.CharField(max_length=10)),
                ('city', models.CharField(help_text=b'Not currently stored', max_length=30)),
            ],
            options={
                'db_table': 'authorship',
            },
        ),
        migrations.CreateModel(
            name='Citation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cite_to', models.BigIntegerField(default=-1, help_text=b'EID of document being cited', db_index=True)),
                ('cite_from', models.BigIntegerField(default=-1, help_text=b'EID (or group ID?) of citing document', db_index=True)),
            ],
            options={
                'db_table': 'citation',
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('eid', models.BigIntegerField(help_text=b'A unique identifier for the record; but see group_id', serialize=False, primary_key=True, db_index=True)),
                ('doi', models.CharField(help_text=b'DOI', max_length=150, null=True)),
                ('pub_year', models.IntegerField(default=-1, help_text=b'Publication year recorded in xocs:pub-year, backing off to xocs:sort-year where pub-year is unavailable', db_index=True)),
                ('group_id', models.BigIntegerField(help_text=b'An EID shared by likely duplicate doc entries', null=True, db_index=True, blank=True)),
                ('title', models.CharField(help_text=b'The original (untranslated) title', max_length=400)),
                ('citation_count', models.IntegerField(default=0, help_text=b'Citation count from citedby.xml')),
                ('title_language', models.CharField(default=b'', help_text=b'The language of the original title', max_length=5)),
                ('abstract', models.CharField(default=b'', help_text=b'Abstract is not currently imported', max_length=1000)),
                ('citation_type', models.CharField(default=b'', help_text=b'The type of document', max_length=5, choices=[(b'ab', b'ab = Abstract Report'), (b'ar', b'ar = Article'), (b'ba', b'ba'), (b'bk', b'bk = Book'), (b'br', b'br = Book Review'), (b'bz', b'bz = Business Article'), (b'cb', b'cb = Conference Abstract'), (b'ch', b'ch = Chapter'), (b'cp', b'cp = Conference Paper'), (b'cr', b'cr = Conference Review'), (b'di', b'di = Dissertation'), (b'ed', b'ed = Editorial'), (b'er', b'er = Erratum'), (b'ip', b'ip = Article in Press'), (b'le', b'le = Letter'), (b'no', b'no = Note'), (b'pa', b'pa = Patent'), (b'pr', b'pr = Press Release'), (b're', b're = Review'), (b'rf', b'rf'), (b'rp', b'rp = Report'), (b'sh', b'sh = Short Survey'), (b'wp', b'wp = Working Paper')])),
            ],
            options={
                'db_table': 'document',
            },
        ),
        migrations.CreateModel(
            name='ItemID',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('item_id', models.CharField(help_text=b'The identifier', max_length=20, db_index=True)),
                ('item_type', models.CharField(help_text=b'ItemID type (see Scopus documentation)', max_length=40)),
                ('document', models.ForeignKey(to='Scopus.Document')),
            ],
            options={
                'db_table': 'itemid',
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('source_id', models.BigIntegerField(default=-1, help_text=b"Scopus's srcid", db_index=True)),
                ('source_type', models.CharField(help_text=b'Source type', max_length=1, null=True, db_index=True, choices=[(b'b', b'b = Book'), (b'd', b'd = Trade Journal'), (b'j', b'j = Journal'), (b'k', b'k = Book Series'), (b'm', b'm = Multi-volume Reference Works'), (b'p', b'p = Conference Proceeding'), (b'r', b'r = Report'), (b'n', b'n = Newsletter'), (b'w', b'w = Newspaper')])),
                ('source_title', models.CharField(max_length=350)),
                ('source_abbrev', models.CharField(max_length=150)),
                ('issn_print', models.CharField(max_length=15, null=True, db_index=True)),
                ('issn_electronic', models.CharField(max_length=15, null=True, db_index=True)),
            ],
            options={
                'db_table': 'source',
            },
        ),
        migrations.AlterUniqueTogether(
            name='source',
            unique_together=set([('source_id', 'issn_print', 'issn_electronic')]),
        ),
        migrations.AddField(
            model_name='document',
            name='source',
            field=models.ForeignKey(blank=True, to='Scopus.Source', help_text=b'Where the document is published', null=True),
        ),
        migrations.AddField(
            model_name='authorship',
            name='document',
            field=models.ForeignKey(to='Scopus.Document'),
        ),
    ]
