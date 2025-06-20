from django.contrib import admin
from .models import EmailRecord, EmailTemplate
from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, AddOnlyModelAdmin, NoDeleteModelAdmin


# Register your models here.
class EmailRecordAdmin(ReadOnlyModelAdmin):
    list_display = ('user', 'subject', 'from_email', 'to')


class EmailTemplateAdmin(NoDeleteModelAdmin):
    list_display = ('title', 'subject', 'cc')


admin.site.register(EmailRecord, EmailRecordAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
