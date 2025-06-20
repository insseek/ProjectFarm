from __future__ import unicode_literals

from django.db import migrations


def data_migrate_prototype_public_status(apps, schema_editor):
    ProjectPrototype = apps.get_model("projects", "ProjectPrototype")
    queryset = ProjectPrototype.objects.all()
    for obj in queryset:
        if obj.is_public:
            obj.public_status = 'public'
            obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0171_projectprototype_public_status'),
    ]

    operations = [
        migrations.RunPython(data_migrate_prototype_public_status, migrations.RunPython.noop),
    ]
