# Generated by Django 3.0.6 on 2020-08-19 13:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20200818_1957'),
    ]

    operations = [
        migrations.RenameField(
            model_name='address',
            old_name='is_delete',
            new_name='is_deleted',
        ),
    ]
