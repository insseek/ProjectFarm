# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def create_project_delivery_document_type(apps, schema_editor):
    DeliveryDocumentType = apps.get_model("projects", "DeliveryDocumentType")
    INIT_DATA = (
        {'name': '交付文档', 'suffix': 'zip', 'number': 0},

        {'name': '交付文档说明', 'suffix': 'pdf', 'number': 1},
        {'name': '源代码', 'suffix': 'zip', 'number': 2},
        {'name': '产品需求文档', 'suffix': 'pdf', 'number': 3},
        {'name': '产品原型', 'suffix': 'zip', 'number': 4},
        {'name': '产品原型源文件', 'suffix': 'zip', 'number': 5},
        {'name': 'UI设计效果图', 'suffix': 'zip', 'number': 6},
        {'name': 'UI设计图源文件', 'suffix': 'zip', 'number': 7},
        {'name': '项目操作说明', 'suffix': 'pdf', 'number': 8},
        {'name': '部署文档', 'suffix': 'pdf', 'number': 9},
        {'name': '数据库设计文档', 'suffix': 'pdf', 'number': 10},
        {'name': '接口文档', 'suffix': 'pdf', 'number': 11},
        {'name': '相关账号信息', 'suffix': 'pdf', 'number': 12},

        {'name': '其他文档', 'suffix': '', 'number': 13},
    )

    for file_document in INIT_DATA:
        DeliveryDocumentType.objects.get_or_create(name=file_document['name'], suffix=file_document['suffix'],
                                                   number=file_document['number'])


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0040_auto_20180122_1551'),
    ]
    operations = [
        migrations.RunPython(create_project_delivery_document_type, migrations.RunPython.noop),
    ]
