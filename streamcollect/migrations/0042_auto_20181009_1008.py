# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-10-09 10:08
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0041_auto_20180912_1958'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CeleryTask',
        ),
        migrations.AddField(
            model_name='user',
            name='user_followers_update',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(), null=True, size=None),
        ),
        migrations.AddField(
            model_name='user',
            name='user_following_update',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(), null=True, size=None),
        ),
        migrations.AddField(
            model_name='user',
            name='user_network_update_observed_at',
            field=models.DateTimeField(null=True),
        ),
    ]