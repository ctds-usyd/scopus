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
            field=models.CharField(default=b'', help_text=b'The article abstract', max_length=10000),
        ),
    ]
