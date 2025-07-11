# Generated by Django 2.0 on 2018-11-18 00:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0085_project_mentor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='checkpoint',
            name='post',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='checkpoints', to='auth.Group', verbose_name='负责职位'),
        ),
        migrations.AlterField(
            model_name='checkpoint',
            name='principal',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='checkpoints', to=settings.AUTH_USER_MODEL, verbose_name='负责人'),
        ),
        migrations.AlterField(
            model_name='deliverydocument',
            name='document_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='projects.DeliveryDocumentType', verbose_name='交付文件类别'),
        ),
        migrations.AlterField(
            model_name='jobposition',
            name='developer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='job_positions', to='developers.Developer', verbose_name='工程师'),
        ),
        migrations.AlterField(
            model_name='jobposition',
            name='role',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='developers.Role', verbose_name='职位'),
        ),
        migrations.AlterField(
            model_name='jobpositioncandidate',
            name='developer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='position_candidates', to='developers.Developer', verbose_name='工程师'),
        ),
        migrations.AlterField(
            model_name='milestone',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='milestones', to='projects.Project', verbose_name='项目'),
        ),
        migrations.AlterField(
            model_name='project',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='projects', to='clients.Client', verbose_name='项目客户'),
        ),
        migrations.AlterField(
            model_name='project',
            name='manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='manage_projects', to=settings.AUTH_USER_MODEL, verbose_name='产品经理'),
        ),
        migrations.AlterField(
            model_name='project',
            name='test_engineer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='test_projects', to=settings.AUTH_USER_MODEL, verbose_name='测试工程师'),
        ),
        migrations.AlterField(
            model_name='project',
            name='tpm',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tpm_projects', to=settings.AUTH_USER_MODEL, verbose_name='技术产品经理'),
        ),
    ]
