# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-03-20 16:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0021_auto_20180320_1609'),
    ]

    operations = [
        migrations.AddField(
            model_name='datacode',
            name='data_code_id',
            field=models.IntegerField(default=3, unique=True),
            preserve_default=False,
        ),
    ]
