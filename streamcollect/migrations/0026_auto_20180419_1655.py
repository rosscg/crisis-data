# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-04-19 16:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0025_auto_20180413_0144'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datacode',
            name='name',
            field=models.CharField(max_length=40),
        ),
    ]
