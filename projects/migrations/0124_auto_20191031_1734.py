# Generated by Django 2.0 on 2019-10-31 17:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0123_auto_20191031_0228'),
    ]

    operations = [
        migrations.RenameField(
            model_name='projectlinks',
            old_name='engineer_contact_docs',
            new_name='engineer_contact_folder',
        ),
    ]
