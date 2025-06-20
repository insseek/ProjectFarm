from django.contrib import admin

from gearfarm.utils.custom_admin import NoDeleteModelAdmin
from testing.models import TestCase, ProjectTestCase


def recover(modeladmin, request, queryset):
    queryset.update(is_active=True)


recover.short_description = "恢复所选被删除的用例"


class ProjectTestCaseAdmin(NoDeleteModelAdmin):
    list_display = ['project', 'module', 'description', 'creator', 'created_at', 'updated_at', 'is_active']
    ordering = ['-updated_at']
    actions = [recover]


class TestCaseAdmin(NoDeleteModelAdmin):
    list_display = ['module', 'description', 'creator', 'created_at', 'updated_at', 'is_active']
    ordering = ['-updated_at']
    actions = [recover]


admin.site.register(ProjectTestCase, ProjectTestCaseAdmin)

admin.site.register(TestCase, TestCaseAdmin)
