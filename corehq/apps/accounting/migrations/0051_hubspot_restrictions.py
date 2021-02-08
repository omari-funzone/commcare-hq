# Generated by Django 2.2.16 on 2020-10-15 17:48

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0050_app_user_profiles'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingaccount',
            name='block_email_domains_from_hubspot',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=253, null=True), default=list, blank=True, null=True, size=None),
        ),
        migrations.AddField(
            model_name='billingaccount',
            name='block_hubspot_data_for_all_users',
            field=models.BooleanField(default=False),
        ),
    ]
