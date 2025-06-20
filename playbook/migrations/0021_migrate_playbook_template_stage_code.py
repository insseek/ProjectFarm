from django.db import migrations
from itertools import chain

from django.db.models import Case, IntegerField, Q, Sum, When, F
from playbook.tasks import rebuild_playbook_template_cache_data


def migrate_playbook_stage_code(apps, schema_editor):
    Stage = apps.get_model("playbook", "Stage")
    TemplateStage = apps.get_model("playbook", "TemplateStage")
    template_stages = TemplateStage.objects.all()
    stages = Stage.objects.all()
    PROJECT_STATUS = (
        ('prd', '原型'),
        ('design', '设计'),
        ('development', '开发'),
        ('test', '测试'),
        ('acceptance', '验收'),
        ('completion', '完成'),
    )
    PROPOSAL_STATUS = (
        ('pending', '等待认领'),
        ('contact', '等待沟通'),
        ('ongoing', '进行中'),
        ('biz_opp', '商机'),
        ('contract', '成单交接'),
        ('deal', '成单'),
        ('no_deal', '未成单'),
    )
    for code, name in chain(PROJECT_STATUS, PROPOSAL_STATUS):
        template_stages.filter(Q(name__icontains=name) | Q(name__icontains=code)).update(stage_code=code)
        stages.filter(Q(name__icontains=name) | Q(name__icontains=code)).update(stage_code=code)

    rebuild_playbook_template_cache_data()


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0020_auto_20200529_1736'),
    ]

    operations = [
        migrations.RunPython(migrate_playbook_stage_code, migrations.RunPython.noop),
    ]
