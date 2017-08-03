# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Scopus', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abstract',
            name='abstract',
            field=models.TextField(default='', help_text='The article abstract', max_length=10000),
        ),
        migrations.AlterField(
            model_name='authorship',
            name='affiliation_id',
            field=models.IntegerField(null=True, help_text="Scopus's afid", db_index=True),
        ),
        migrations.AlterField(
            model_name='authorship',
            name='author_id',
            field=models.BigIntegerField(null=True, help_text="Scopus's auid", db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='authorship',
            name='city',
            field=models.CharField(help_text='Not currently stored', max_length=30),
        ),
        migrations.AlterField(
            model_name='authorship',
            name='department',
            field=models.CharField(default='', help_text='Name from 2nd organization node in affiliation details', max_length=200),
        ),
        migrations.AlterField(
            model_name='authorship',
            name='initials',
            field=models.CharField(default='', max_length=20),
        ),
        migrations.AlterField(
            model_name='authorship',
            name='order',
            field=models.PositiveIntegerField(default=0, help_text='1 for first author, etc. Can have multiple Authorship entries for one value of order.'),
        ),
        migrations.AlterField(
            model_name='authorship',
            name='organization',
            field=models.CharField(default='', help_text='Name from 1st organization node in affiliation details', db_index=True, max_length=300),
        ),
        migrations.AlterField(
            model_name='citation',
            name='cite_from',
            field=models.BigIntegerField(default=-1, help_text='EID (or group ID?) of citing document', db_index=True),
        ),
        migrations.AlterField(
            model_name='citation',
            name='cite_to',
            field=models.BigIntegerField(default=-1, help_text='EID of document being cited', db_index=True),
        ),
        migrations.AlterField(
            model_name='document',
            name='citation_count',
            field=models.IntegerField(default=0, help_text='Citation count from citedby.xml'),
        ),
        migrations.AlterField(
            model_name='document',
            name='citation_type',
            field=models.CharField(default='', choices=[('ab', 'ab = Abstract Report'), ('ar', 'ar = Article'), ('ba', 'ba'), ('bk', 'bk = Book'), ('br', 'br = Book Review'), ('bz', 'bz = Business Article'), ('cb', 'cb = Conference Abstract'), ('ch', 'ch = Chapter'), ('cp', 'cp = Conference Paper'), ('cr', 'cr = Conference Review'), ('di', 'di = Dissertation'), ('ed', 'ed = Editorial'), ('er', 'er = Erratum'), ('ip', 'ip = Article in Press'), ('le', 'le = Letter'), ('no', 'no = Note'), ('pa', 'pa = Patent'), ('pr', 'pr = Press Release'), ('re', 're = Review'), ('rf', 'rf'), ('rp', 'rp = Report'), ('sh', 'sh = Short Survey'), ('wp', 'wp = Working Paper')], help_text='The type of document', max_length=5),
        ),
        migrations.AlterField(
            model_name='document',
            name='doi',
            field=models.CharField(null=True, help_text='DOI', max_length=150),
        ),
        migrations.AlterField(
            model_name='document',
            name='eid',
            field=models.BigIntegerField(help_text='A unique identifier for the record; but see group_id', serialize=False, primary_key=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='document',
            name='group_id',
            field=models.BigIntegerField(null=True, help_text='An EID shared by likely duplicate doc entries', db_index=True, blank=True),
        ),
        migrations.AlterField(
            model_name='document',
            name='pub_year',
            field=models.IntegerField(default=-1, help_text='Publication year recorded in xocs:pub-year, backing off to xocs:sort-year where pub-year is unavailable', db_index=True),
        ),
        migrations.AlterField(
            model_name='document',
            name='source',
            field=models.ForeignKey(null=True, to='Scopus.Source', help_text='Where the document is published', blank=True),
        ),
        migrations.AlterField(
            model_name='document',
            name='title',
            field=models.CharField(help_text='The original (untranslated) title', max_length=500),
        ),
        migrations.AlterField(
            model_name='document',
            name='title_language',
            field=models.CharField(default='', help_text='The language of the original title', max_length=5),
        ),
        migrations.AlterField(
            model_name='itemid',
            name='item_id',
            field=models.CharField(help_text='The identifier', db_index=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='itemid',
            name='item_type',
            field=models.CharField(help_text='ItemID type (see Scopus documentation)', max_length=40),
        ),
        migrations.AlterField(
            model_name='source',
            name='scopus_source_id',
            field=models.BigIntegerField(default=-1, help_text="Scopus's srcid", db_index=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='source_type',
            field=models.CharField(null=True, choices=[('b', 'b = Book'), ('d', 'd = Trade Journal'), ('j', 'j = Journal'), ('k', 'k = Book Series'), ('m', 'm = Multi-volume Reference Works'), ('p', 'p = Conference Proceeding'), ('r', 'r = Report'), ('n', 'n = Newsletter'), ('w', 'w = Newspaper')], help_text='Source type', db_index=True, max_length=1),
        ),
    ]
