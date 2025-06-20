from django.contrib import admin
from .models import JobPayment, JobContract, ProjectPayment

from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, NoDeleteModelAdmin


# Register your models here.
class JobPaymentAdmin(ReadOnlyModelAdmin):
    list_display = ('name', 'status', 'amount', 'expected_at', 'id')


class ProjectPaymentAdmin(NoDeleteModelAdmin):
    list_display = ('project', 'contract_name', 'capital_account')


admin.site.register(ProjectPayment, ProjectPaymentAdmin)


admin.site.register(JobPayment, JobPaymentAdmin)

admin.site.register(JobContract)
