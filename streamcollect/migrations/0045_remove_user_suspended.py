# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2019-08-28 13:58
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0044_auto_20190426_1225'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='suspended',
        ),
    ]
