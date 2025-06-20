from django.contrib import admin
from developers.models import Role, Developer, TaggedDevelopmentLanguage, TaggedFrameworks, DocumentSyncLog
from gearfarm.utils.custom_admin import NoDeleteModelAdmin


class RoleAdmin(NoDeleteModelAdmin):
    list_display = ('name',)


class DeveloperAdmin(NoDeleteModelAdmin):
    list_display = ('name', 'status',)


admin.site.register(Role, RoleAdmin)
admin.site.register(Developer, DeveloperAdmin)
admin.site.register(TaggedDevelopmentLanguage, NoDeleteModelAdmin)
admin.site.register(TaggedFrameworks, NoDeleteModelAdmin)
admin.site.register(DocumentSyncLog)
