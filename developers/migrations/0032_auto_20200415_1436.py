# Generated by Django 2.0 on 2020-04-15 14:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('developers', '0031_dailywork_dailyworktask'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dailyworktask',
            name='daily_work',
        ),
        migrations.RemoveField(
            model_name='dailyworktask',
            name='gantt_task',
        ),
        migrations.AddField(
            model_name='dailywork',
            name='gantt_tasks',
            field=models.TextField(blank=True, null=True, verbose_name='甘特图任务'),
        ),
        migrations.AddField(
            model_name='dailywork',
            name='gantt_tasks_plan',
            field=models.TextField(blank=True, null=True, verbose_name='甘特图任务计划'),
        ),
        migrations.AddField(
            model_name='dailywork',
            name='other_task',
            field=models.TextField(blank=True, null=True, verbose_name='其他任务'),
        ),
        migrations.AddField(
            model_name='dailywork',
            name='other_task_plan',
            field=models.TextField(blank=True, null=True, verbose_name='其他任务计划'),
        ),
        migrations.DeleteModel(
            name='DailyWorkTask',
        ),
    ]
