# Generated by Django 2.0 on 2021-01-09 01:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('testing', '0020_auto_20210105_1700'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bug',
            name='platform',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bugs', to='testing.ProjectPlatform', verbose_name='平台'),
        ),
    ]
