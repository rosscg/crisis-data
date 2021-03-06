# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-03-19 21:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0016_auto_20170926_2125'),
    ]

    operations = [
        migrations.AddField(
            model_name='tweet',
            name='data_code',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='geopoint',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='geopoint', to='streamcollect.Event'),
        ),
        migrations.AlterField(
            model_name='keyword',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='keyword', to='streamcollect.Event'),
        ),
    ]
