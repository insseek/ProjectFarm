from django.conf import settings

from django.contrib import admin
from proposals.models import Proposal

from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, AddOnlyModelAdmin, NoDeleteModelAdmin


# Register your models here.
class ProposalAdmin(NoDeleteModelAdmin):
    list_display = ('name', 'id', 'bd', 'pm', 'created_at', 'report_at', 'closed_at')


class ProposalFullAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'bd', 'pm', 'created_at', 'report_at', 'closed_at')


if settings.PRODUCTION:
    admin.site.register(Proposal, ProposalAdmin)
else:
    admin.site.register(Proposal, ProposalFullAdmin)
