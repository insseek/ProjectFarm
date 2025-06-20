from __future__ import unicode_literals
import json

from django.db import migrations


def data_migrate_projects_calendars_ui_links(apps, schema_editor):
    ClientCalendar = apps.get_model("projects", "ClientCalendar")
    ProjectLinks = apps.get_model("projects", "ProjectLinks")
    Project = apps.get_model("projects", "Project")

    ongoing_projects = Project.objects.filter(done_at__isnull=True)
    for p in ongoing_projects:
        calendar = ClientCalendar.objects.filter(project_id=p.id).order_by('-created_at').first()
        if calendar:
            calendar.is_public = True
            calendar.save()
    projects_links = ProjectLinks.objects.all()
    for p_l in projects_links:
        ui_link = p_l.ui_link
        if ui_link:
            ui_links = [{"name": "UI设计稿", "link": ui_link}]
            p_l.ui_links = json.dumps(ui_links, ensure_ascii=False)
            p_l.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0162_auto_20200827_1848'),
    ]

    operations = [
        migrations.RunPython(data_migrate_projects_calendars_ui_links, migrations.RunPython.noop),
    ]
