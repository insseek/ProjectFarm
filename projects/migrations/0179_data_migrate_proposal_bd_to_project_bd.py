from __future__ import unicode_literals

from django.db import migrations


def data_migrate_proposal_bd_to_project_bd(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Proposal = apps.get_model("proposals", "Proposal")
    queryset = Project.objects.all()
    for obj in queryset:
        proposal = Proposal.objects.filter(project_id=obj.id).first()
        if proposal and proposal.bd:
            obj.bd = proposal.bd
            obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0178_project_bd'),
    ]

    operations = [
        migrations.RunPython(data_migrate_proposal_bd_to_project_bd, migrations.RunPython.noop),
    ]
