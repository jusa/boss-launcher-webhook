# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-30 13:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_auto_20170330_1606'),
    ]

    operations = [
        migrations.AddField(
            model_name='webhookmapping',
            name='placeholder',
            field=models.BooleanField(default=False, editable=False, help_text=b'Marks automatically created placehollders'),
        ),
    ]
