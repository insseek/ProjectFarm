# Generated by Django 2.0 on 2019-12-17 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0134_auto_20191217_1808'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectganttchart',
            name='template_init_status',
            field=models.CharField(choices=[('uninitialized', '未初始化'), ('skipped', '跳过'), ('initialized', '已初始化')], default='uninitialized', max_length=20, verbose_name='模板导入状态'),
        ),
    ]
