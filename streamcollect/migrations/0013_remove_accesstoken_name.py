# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-27 17:53
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0012_accesstoken'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accesstoken',
            name='name',
        ),
    ]
