# Generated by Django 2.0 on 2019-09-20 16:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('proposals', '0049_auto_20190827_1155'),
        ('workorder', '0005_auto_20190911_1952'),
    ]

    operations = [
        migrations.AddField(
            model_name='designworkorder',
            name='proposal',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='design_work_orders', to='proposals.Proposal', verbose_name='需求'),
        ),
        migrations.AlterField(
            model_name='designworkorder',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='design_work_orders', to='projects.Project', verbose_name='项目'),
        ),
    ]
