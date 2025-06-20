from django.contrib import admin
from .models import RequirementInfo, Lead, LeadTrack, TrackCodeFile

from gearfarm.utils.custom_admin import NoDeleteModelAdmin, ReadOnlyModelAdmin


class LeadTrackAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'track_code', 'url')


class LeadAdmin(NoDeleteModelAdmin):
    list_display = ('name', 'id')


admin.site.register(Lead, LeadAdmin)

admin.site.register(LeadTrack, LeadTrackAdmin)

admin.site.register(TrackCodeFile, ReadOnlyModelAdmin)

admin.site.register(RequirementInfo, NoDeleteModelAdmin)
