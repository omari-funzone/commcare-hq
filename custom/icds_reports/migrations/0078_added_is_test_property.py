# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-11 14:13
from __future__ import unicode_literals
from __future__ import absolute_import

from django.db import migrations

from corehq.sql_db.operations import RawSQLMigration


migrator = RawSQLMigration(('custom', 'icds_reports', 'migrations', 'sql_templates'))


class Migration(migrations.Migration):

    dependencies = [
        ('icds_reports', '0078_add_phone_number_to_child_health_monthly'),
    ]

    operations = [
        migrator.get_migration('update_tables33.sql'),
    ]
