from django.contrib import admin
from .models import Profile, Documents, FunctionModule, FunctionPermission
from django.contrib.auth.models import User, Permission
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from gearfarm.utils.custom_admin import NoDeleteModelAdmin, ReadOnlyModelAdmin


class UserProfileInline(admin.StackedInline):
    model = Profile
    max_num = 1
    can_delete = False


class UserAdmin(AuthUserAdmin, NoDeleteModelAdmin):
    inlines = [UserProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Documents, NoDeleteModelAdmin)
admin.site.register(FunctionModule, NoDeleteModelAdmin)
admin.site.register(FunctionPermission, NoDeleteModelAdmin)
