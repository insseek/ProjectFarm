# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from proposals.models import Proposal, Industry, ApplicationPlatform, ProductType


def data_migrate_reports_tags(apps, schema_editor):
    # Industry = apps.get_model("proposals", "Industry")
    # ApplicationPlatform = apps.get_model("proposals", "ApplicationPlatform")
    # ProductType = apps.get_model("proposals", "ProductType")

    industry_init_data = Industry.INIT_DATA
    application_platform_init_data = ApplicationPlatform.INIT_DATA
    product_type_init_data = ProductType.INIT_DATA
    for index, obj_data in enumerate(industry_init_data):
        obj_data['index'] = index
        Industry.objects.get_or_create(**obj_data)

    for index, obj_data in enumerate(application_platform_init_data):
        obj_data['index'] = index
        ApplicationPlatform.objects.get_or_create(**obj_data)

    for index, obj_data in enumerate(product_type_init_data):
        obj_data['index'] = index
        children = obj_data.pop('children', [])
        product_type, created = ProductType.objects.get_or_create(**obj_data)
        if children:
            for child_index, child_data in enumerate(children):
                child_data['index'] = child_index
                child_data['parent'] = product_type
                ProductType.objects.get_or_create(**child_data)


class Migration(migrations.Migration):
    dependencies = [
        ('proposals', '0054_auto_20200506_1304'),
    ]

    operations = [
        migrations.RunPython(data_migrate_reports_tags, migrations.RunPython.noop),
    ]
