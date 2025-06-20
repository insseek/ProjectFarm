from django.contrib import admin
from .models import TopUser, TopToken
from gearfarm.utils.custom_admin import NoDeleteModelAdmin


class TopTokenInline(admin.StackedInline):
    model = TopToken
    max_num = 1
    can_delete = False


class UserAdmin(NoDeleteModelAdmin):
    inlines = [TopTokenInline]


admin.site.register(TopUser, UserAdmin)

admin.site.register(TopToken, NoDeleteModelAdmin)
