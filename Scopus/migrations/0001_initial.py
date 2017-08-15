# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Abstract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('abstract', models.TextField(max_length=10000, default='', help_text='The article abstract')),
            ],
            options={
                'db_table': 'abstract',
            },
        ),
        migrations.CreateModel(
            name='Authorship',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('author_id', models.BigIntegerField(blank=True, null=True, db_index=True, help_text="Scopus's auid")),
                ('initials', models.CharField(max_length=20, default='')),
                ('surname', models.CharField(max_length=100)),
                ('order', models.PositiveIntegerField(default=0, help_text='1 for first author, etc. Can have multiple Authorship entries for one value of order.')),
                ('affiliation_id', models.IntegerField(null=True, db_index=True, help_text="Scopus's afid")),
                ('organization1', models.CharField(max_length=300, db_index=True, default='', help_text='Name from 1st organization node in affiliation details')),
                ('organization2', models.CharField(max_length=300, db_index=True, default='', help_text='Name from 2nd organization node in affiliation details')),
                ('organization3', models.CharField(max_length=300, db_index=True, default='', help_text='Name from 3rd organization node in affiliation details')),
                ('country', models.CharField(max_length=10)),
                ('city', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'authorship',
            },
        ),
        migrations.CreateModel(
            name='Citation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('cite_to', models.BigIntegerField(db_index=True, default=-1, help_text='EID of document being cited')),
                ('cite_from', models.BigIntegerField(db_index=True, default=-1, help_text='EID (or group ID?) of citing document')),
            ],
            options={
                'db_table': 'citation',
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('eid', models.BigIntegerField(primary_key=True, db_index=True, serialize=False, help_text='A unique identifier for the record; but see group_id')),
                ('doi', models.CharField(max_length=150, null=True, help_text='DOI')),
                ('pub_year', models.IntegerField(db_index=True, default=-1, help_text='Publication year recorded in xocs:pub-year, backing off to xocs:sort-year where pub-year is unavailable')),
                ('group_id', models.BigIntegerField(blank=True, null=True, db_index=True, help_text='An EID shared by likely duplicate doc entries')),
                ('title', models.CharField(max_length=500, help_text='The original (untranslated) title')),
                ('citation_count', models.IntegerField(default=0, help_text='Citation count from citedby.xml')),
                ('title_language', models.CharField(max_length=5, default='', help_text='The language of the original title')),
                ('citation_type', models.CharField(max_length=5, default='', choices=[('ab', 'ab = Abstract Report'), ('ar', 'ar = Article'), ('ba', 'ba'), ('bk', 'bk = Book'), ('br', 'br = Book Review'), ('bz', 'bz = Business Article'), ('cb', 'cb = Conference Abstract'), ('ch', 'ch = Chapter'), ('cp', 'cp = Conference Paper'), ('cr', 'cr = Conference Review'), ('di', 'di = Dissertation'), ('ed', 'ed = Editorial'), ('er', 'er = Erratum'), ('ip', 'ip = Article in Press'), ('le', 'le = Letter'), ('no', 'no = Note'), ('pa', 'pa = Patent'), ('pr', 'pr = Press Release'), ('re', 're = Review'), ('rf', 'rf'), ('rp', 'rp = Report'), ('sh', 'sh = Short Survey'), ('wp', 'wp = Working Paper')], help_text='The type of document')),
            ],
            options={
                'db_table': 'document',
            },
        ),
        migrations.CreateModel(
            name='ItemID',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('item_id', models.CharField(max_length=20, db_index=True, help_text='The identifier')),
                ('item_type', models.CharField(max_length=40, help_text='ItemID type (see Scopus documentation)')),
                ('document', models.ForeignKey(to='Scopus.Document')),
            ],
            options={
                'db_table': 'itemid',
            },
        ),
        migrations.CreateModel(
            name='Source',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('scopus_source_id', models.BigIntegerField(db_index=True, default=-1, help_text="Scopus's srcid")),
                ('source_type', models.CharField(max_length=1, null=True, db_index=True, choices=[('b', 'b = Book'), ('d', 'd = Trade Journal'), ('j', 'j = Journal'), ('k', 'k = Book Series'), ('m', 'm = Multi-volume Reference Works'), ('p', 'p = Conference Proceeding'), ('r', 'r = Report'), ('n', 'n = Newsletter'), ('w', 'w = Newspaper')], help_text='Source type')),
                ('source_title', models.CharField(max_length=400)),
                ('source_abbrev', models.CharField(max_length=200)),
                ('issn_print', models.CharField(max_length=15, null=True, db_index=True)),
                ('issn_electronic', models.CharField(max_length=15, null=True, db_index=True)),
            ],
            options={
                'db_table': 'source',
            },
        ),
        migrations.AlterUniqueTogether(
            name='source',
            unique_together=set([('scopus_source_id', 'issn_print', 'issn_electronic')]),
        ),
        migrations.AddField(
            model_name='document',
            name='source',
            field=models.ForeignKey(blank=True, null=True, help_text='Where the document is published', to='Scopus.Source'),
        ),
        migrations.AddField(
            model_name='authorship',
            name='document',
            field=models.ForeignKey(to='Scopus.Document'),
        ),
        migrations.AddField(
            model_name='abstract',
            name='document',
            field=models.ForeignKey(to='Scopus.Document'),
        ),
    ]
