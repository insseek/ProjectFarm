from __future__ import unicode_literals
from django.db import migrations


def init_job_position_review_status(apps, schema_editor):
    JobPosition = apps.get_model("projects", "JobPosition")
    JobReview = apps.get_model("projects", "JobReview")

    for job_position in JobPosition.objects.all():
        if JobReview.objects.filter(pk=job_position.id).exists():
            job_position.review_status = 1
            job_position.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0058_jobposition_review_status'),
    ]

    operations = [
        migrations.RunPython(init_job_position_review_status, migrations.RunPython.noop),
    ]
