from django.contrib import admin
from files.models import File

from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, AddOnlyModelAdmin

admin.site.register(File, ReadOnlyModelAdmin)
