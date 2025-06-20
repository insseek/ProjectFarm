from __future__ import unicode_literals

from django.db import migrations


def migrate_projects_gantt_tasks_catalogues(apps, schema_editor):
    GanttTaskCatalogue = apps.get_model("projects", "GanttTaskCatalogue")
    GanttTaskTopic = apps.get_model("projects", "GanttTaskTopic")

    no_catalogue_topics = GanttTaskTopic.objects.filter(catalogue_id__isnull=True)

    for topic in no_catalogue_topics:
        catalogue = GanttTaskCatalogue.objects.create(gantt_chart=topic.gantt_chart, name=topic.name,
                                                      number=topic.number)
        topic.catalogue = catalogue
        topic.number = 1
        topic.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0130_auto_20191202_1756'),
    ]

    operations = [
        migrations.RunPython(migrate_projects_gantt_tasks_catalogues, migrations.RunPython.noop),
    ]
