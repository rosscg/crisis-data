# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-07-31 17:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('streamcollect', '0028_rename_coder'),
    ]

    operations = [
        migrations.RenameField(
            model_name='coding',
            old_name='coder_id',
            new_name='coding_id',
        ),
        migrations.AddField(
            model_name='coding',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='coding_for_user', to='streamcollect.User'),
        ),
        migrations.AddField(
            model_name='datacode',
            name='users',
            field=models.ManyToManyField(through='streamcollect.Coding', to='streamcollect.User'),
        ),
        migrations.AlterField(
            model_name='coding',
            name='tweet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='coding_for_tweet', to='streamcollect.Tweet'),
        ),
        migrations.AlterUniqueTogether(
            name='coding',
            unique_together=set([('coding_id', 'data_code', 'user')]),
        ),
    ]
