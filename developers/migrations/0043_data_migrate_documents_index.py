# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def data_migrate_documents_index(apps, schema_editor):
    Document = apps.get_model("developers", "Document")
    documents = Document.objects.filter(deleted=False).order_by('created_at')
    for index, document in enumerate(documents):
        document.index = index
        document.save()


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0042_document_index'),
    ]
    operations = [
        migrations.RunPython(data_migrate_documents_index, migrations.RunPython.noop),
    ]
