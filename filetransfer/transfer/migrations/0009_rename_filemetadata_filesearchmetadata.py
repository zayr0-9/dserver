# Generated by Django 5.0.7 on 2024-11-08 17:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transfer', '0008_directory_allow_sub_dir'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='FileMetadata',
            new_name='FileSearchMetadata',
        ),
    ]