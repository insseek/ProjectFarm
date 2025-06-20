from django.contrib import admin
from .models import HuaWeiVoiceCallAuth, CallRecord
from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, AddOnlyModelAdmin


# Register your models here.
class HuaWeiVoiceCallAuthAdmin(AddOnlyModelAdmin):
    list_display = ('username',)


admin.site.register(HuaWeiVoiceCallAuth, HuaWeiVoiceCallAuthAdmin)
admin.site.register(CallRecord, ReadOnlyModelAdmin)
