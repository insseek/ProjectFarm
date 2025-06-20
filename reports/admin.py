from django.contrib import admin
from .models import Report
from .models import Grade

from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, AddOnlyModelAdmin, NoDeleteModelAdmin


class GradeAdmin(ReadOnlyModelAdmin):
    list_display = ('report', 'rate', 'created_at')


class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'author', 'uid', 'created_at', 'is_public', 'expired_at', 'expired')
    search_fields = ['title', 'uid']
    readonly_fields = ('expired',)

    def expired(self, obj):
        return obj.is_expired()


class FrameDiagramAdmin(AddOnlyModelAdmin):
    list_display = ('id', 'filename', 'is_standard', 'is_deleted')


admin.site.register(Grade, GradeAdmin)
admin.site.register(Report, ReportAdmin)
