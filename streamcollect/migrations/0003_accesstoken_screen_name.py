# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-17 14:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0002_mention'),
    ]

    operations = [
        migrations.AddField(
            model_name='accesstoken',
            name='screen_name',
            field=models.CharField(max_length=40, null=True, unique=True),
        ),
    ]
