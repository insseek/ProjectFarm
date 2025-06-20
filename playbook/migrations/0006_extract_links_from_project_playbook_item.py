# -*- coding: utf-8 -*-
import re

from django.contrib.contenttypes.models import ContentType
from django.db import migrations


def migrate_existing_project_playbook_data(apps, schema_editor):
    InfoItem = apps.get_model("playbook", "InfoItem")
    ChecklistItem = apps.get_model("playbook", "ChecklistItem")
    LinkItem = apps.get_model("playbook", "LinkItem")
    ContentType.objects.get_for_model(ChecklistItem)
    ContentType.objects.get_for_model(InfoItem)

    checklist_type = ContentType.objects.get(app_label="playbook", model="checklistitem")
    project_type = ContentType.objects.get(app_label="projects", model="project")
    info_item_type = ContentType.objects.get(app_label="playbook", model="infoitem")
    info_items = InfoItem.objects.filter(content_type_id=project_type.id).all()
    checklist_items = ChecklistItem.objects.filter(content_type_id=project_type.id).all()
    for item in info_items:
        description = item.description
        pattern = '\[<a href="([^"]+?)"\s*?target="_blank">(.*?)</a>\]'
        link_list = re.findall(pattern, description)
        if link_list:
            for link_position, (url, name) in enumerate(link_list):
                LinkItem.objects.create(name=name, url=url, position=link_position, content_type_id=info_item_type.id,
                                        object_id=item.id)
            new_description = re.sub(pattern, lambda m: '', description).strip()
            item.description = new_description
            item.save()

    for item in checklist_items:
        description = item.description
        pattern = '\[<a href="([^"]+?)"\s*?target="_blank">(.*?)</a>\]'
        link_list = re.findall(pattern, description)
        if link_list:
            for link_position, (url, name) in enumerate(link_list):
                LinkItem.objects.create(name=name, url=url, position=link_position, content_type_id=checklist_type.id,
                                        object_id=item.id)
            new_description = re.sub(pattern, lambda m: '', description).strip()
            item.description = new_description
            item.save()


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0005_migrate_existing_project_playbook_data'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_project_playbook_data, migrations.RunPython.noop),
    ]
