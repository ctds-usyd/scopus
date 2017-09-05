# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Scopus', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='authorship',
            name='organization1',
        ),
        migrations.RemoveField(
            model_name='authorship',
            name='organization2',
        ),
        migrations.RemoveField(
            model_name='authorship',
            name='organization3',
        ),
        migrations.AddField(
            model_name='authorship',
            name='affiliation',
            field=models.TextField(help_text='Text from all organization nodes, separated by newline characters', default=''),
        ),
    ]
