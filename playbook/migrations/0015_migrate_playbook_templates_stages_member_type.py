from django.db import migrations


def migrate_playbook_template_member_type(apps, schema_editor):
    PlaybookTemplate = apps.get_model("playbook", "Template")
    Stage = apps.get_model("playbook", "Stage")
    # 现在历史数据中只有
    PlaybookTemplate.objects.filter(template_type='project').update(member_type='manager')
    Stage.objects.filter(content_type__model='project').update(member_type='manager')


class Migration(migrations.Migration):
    dependencies = [
        ('playbook', '0014_auto_20200319_1449'),
    ]

    operations = [
        migrations.RunPython(migrate_playbook_template_member_type, migrations.RunPython.noop),
    ]
