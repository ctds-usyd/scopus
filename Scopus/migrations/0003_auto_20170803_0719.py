# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Scopus', '0002_auto_20170803_0600'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='authorship',
            name='department',
        ),
        migrations.RemoveField(
            model_name='authorship',
            name='organization',
        ),
        migrations.AddField(
            model_name='authorship',
            name='organization1',
            field=models.CharField(help_text='Name from 1st organization node in affiliation details', default='', db_index=True, max_length=300),
        ),
        migrations.AddField(
            model_name='authorship',
            name='organization2',
            field=models.CharField(help_text='Name from 2nd organization node in affiliation details', default='', db_index=True, max_length=300),
        ),
        migrations.AddField(
            model_name='authorship',
            name='organization3',
            field=models.CharField(help_text='Name from 3rd organization node in affiliation details', default='', db_index=True, max_length=300),
        ),
    ]
