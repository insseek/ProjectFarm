from __future__ import unicode_literals

from django.db import migrations


def exchange_project_payment_name_and_payment_account_name(apps, schema_editor):
    ProjectPayment = apps.get_model("projects", "ProjectPayment")
    for project_payment in ProjectPayment.objects.all():
        project_payment.name, project_payment.payment_account_name = project_payment.payment_account_name, project_payment.name,
        project_payment.save()


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0056_auto_20180327_1131'),
    ]

    operations = [
        migrations.RunPython(exchange_project_payment_name_and_payment_account_name, migrations.RunPython.noop),
    ]
