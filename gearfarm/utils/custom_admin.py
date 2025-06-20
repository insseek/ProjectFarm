from django.contrib import admin


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """ModelAdmin class that prevents modifications through the admin.

    The changelist and the detail view work, but a 403 is returned
    if one actually tries to edit an object.
    """

    actions = None

    def get_readonly_fields(self, request, obj=None):
        return self.fields or [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return True

    # Allow viewing objects but not actually changing them
    def has_change_permission(self, request, obj=None):
        if request.method not in ('GET', 'HEAD'):
            return False
        return super(ReadOnlyModelAdmin, self).has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


class AddOnlyModelAdmin(admin.ModelAdmin):
    """ModelAdmin class that prevents modifications through the admin.

    The changelist and the detail view work, but a 403 is returned
    if one actually tries to edit an object.
    """
    actions = None

    # def get_readonly_fields(self, request, obj=None):
    #     return self.fields or [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return True

    # Allow viewing objects but not actually changing them
    def has_change_permission(self, request, obj=None):
        if request.method not in ('GET', 'HEAD'):
            return False
        return super(AddOnlyModelAdmin, self).has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


class NoDeleteModelAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        # Disable delete
        actions = super(NoDeleteModelAdmin, self).get_actions(request)
        if actions.get('delete_selected'):
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        return False
