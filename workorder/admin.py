from django.contrib import admin
from workorder.models import CommonWorkOrder


class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'submitter', 'principal', 'description')


admin.site.register(CommonWorkOrder, WorkOrderAdmin)
