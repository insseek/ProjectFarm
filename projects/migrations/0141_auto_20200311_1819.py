# Generated by Django 2.0 on 2020-03-11 18:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0140_clientcalendar_creator'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='product_manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_manage_projects', to=settings.AUTH_USER_MODEL, verbose_name='产品经理'),
        ),
        migrations.AlterField(
            model_name='project',
            name='manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='manage_projects', to=settings.AUTH_USER_MODEL, verbose_name='项目经理'),
        ),
    ]
