from django.contrib import admin
from tasks.models import Task

from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, AddOnlyModelAdmin, NoDeleteModelAdmin

class TaskAdmin(NoDeleteModelAdmin):
    list_display = ('name', 'creator', 'created_at', 'expected_at', 'is_done',)


admin.site.register(Task, TaskAdmin)