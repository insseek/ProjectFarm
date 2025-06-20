from __future__ import unicode_literals

from django.db import migrations


def get_new_score(score):
    new_score = int(score + 0.5)  # 四舍五入
    if new_score <= 0:
        new_score = 1
    elif new_score > 5:
        new_score = 5
    return new_score


def data_migrate_projects_job_position_score(apps, schema_editor):
    JobReview = apps.get_model("projects", "JobReview")
    JobStandardScore = apps.get_model("projects", "JobStandardScore")

    job_reviews = JobReview.objects.all()
    for job_review in job_reviews:
        job_position = job_review.job_position
        communication = get_new_score(job_review.communication * 2.5)
        efficiency = get_new_score(job_review.efficiency * 2.5)
        quality = get_new_score((job_review.quality + job_review.bug + job_review.code_style) / 3 * 2.5)
        execute = get_new_score((quality + efficiency + communication) / 3)

        score = JobStandardScore.objects.create(efficiency=efficiency, communication=communication, quality=quality,
                                                execute=execute, job_position=job_position)
        score.created_at = job_review.created_at
        score.modified_at = job_review.modified_at
        score.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0167_auto_20201016_1744'),
    ]

    operations = [
        migrations.RunPython(data_migrate_projects_job_position_score, migrations.RunPython.noop),
    ]
