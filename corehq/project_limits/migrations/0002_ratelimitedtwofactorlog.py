# Generated by Django 2.2.16 on 2020-10-13 12:47

from django.db import migrations, models
from architect.commands import partition


def add_partitions(apps, schema_editor):
    partition.run({'module': 'corehq.project_limits.models'})


class Migration(migrations.Migration):

    dependencies = [
        ('project_limits', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RateLimitedTwoFactorLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('username', models.CharField(db_index=True, max_length=255)),
                ('ip_address', models.CharField(db_index=True, max_length=45)),
                ('phone_number', models.CharField(db_index=True, max_length=127)),
                ('method', models.CharField(max_length=4)),
                ('window', models.CharField(max_length=15)),
                ('status', models.CharField(max_length=31)),
            ],
        ),
        migrations.RunPython(add_partitions),
    ]
