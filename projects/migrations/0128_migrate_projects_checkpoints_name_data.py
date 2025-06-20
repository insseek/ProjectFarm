from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.models import Group


def migrate_projects_checkpoints_name_position(apps, schema_editor):
    pass
    # CheckPoint = apps.get_model("projects", "CheckPoint")
    # checkpoints = CheckPoint.objects.all()
    #
    # test_group, created = Group.objects.get_or_create(name='测试')
    # tpm_group, created = Group.objects.get_or_create(name='TPM')
    #
    # checkpoints.filter(name="工程师评分", post_id=tpm_group.id).update(name='工程师评分一')
    # checkpoints.filter(name="工程师评分", post_id=test_group.id).update(name='工程师评分二')
    # checkpoints.filter(name="中期代码审核").update(is_active=False)
    # checkpoints.filter(name="UI确认").update(name="设计确认")
    # checkpoints.filter(name="PRD确认").update(name="原型确认")



class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0127_migrate_projects_schedules_data'),
    ]

    operations = [
        migrations.RunPython(migrate_projects_checkpoints_name_position, migrations.RunPython.noop),
    ]
