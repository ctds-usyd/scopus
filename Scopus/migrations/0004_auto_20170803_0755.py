# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Scopus', '0003_auto_20170803_0719'),
    ]

    operations = [
        migrations.AlterField(
            model_name='authorship',
            name='city',
            field=models.CharField(max_length=100),
        ),
    ]
