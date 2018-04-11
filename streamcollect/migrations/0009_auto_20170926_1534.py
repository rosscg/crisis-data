# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-09-26 15:34
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0008_event'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeoPoint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
            ],
        ),
        migrations.RemoveField(
            model_name='event',
            name='lat_1',
        ),
        migrations.RemoveField(
            model_name='event',
            name='lat_2',
        ),
        migrations.RemoveField(
            model_name='event',
            name='long_1',
        ),
        migrations.RemoveField(
            model_name='event',
            name='long_2',
        ),
        migrations.AlterField(
            model_name='event',
            name='gps_stream_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='kw_stream_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='name',
            field=models.TextField(max_length=20),
        ),
        migrations.AlterField(
            model_name='event',
            name='time_end',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='time_start',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='geopoint',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='geopoint', to='streamcollect.Event'),
        ),
    ]