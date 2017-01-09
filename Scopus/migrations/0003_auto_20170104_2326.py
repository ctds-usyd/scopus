# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Scopus', '0002_auto_20170104_2301'),
    ]

    operations = [
        migrations.AlterField(
            model_name='source',
            name='source_abbrev',
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name='source',
            name='source_title',
            field=models.CharField(max_length=400),
        ),
    ]
