# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-05 18:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0002_auto_20170505_1810'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='relevant_in_degree',
            field=models.IntegerField(default=0),
        ),
    ]