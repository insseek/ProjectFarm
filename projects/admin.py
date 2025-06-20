from django.conf import settings
from django.contrib import admin
from projects.models import Project, JobPosition, JobPositionNeed, JobPositionCandidate, ProjectLinks,  GanttTaskCatalogue, GanttTaskTopic, ProjectPrototype
from gearfarm.utils.custom_admin import ReadOnlyModelAdmin, AddOnlyModelAdmin, NoDeleteModelAdmin


# Register your models here.
class ProjectAdmin(NoDeleteModelAdmin):
    list_display = ('name', 'id', 'manager')


class ProjectFullAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'manager')


class JobAdmin(NoDeleteModelAdmin):
    list_display = ('role', 'project', 'developer', 'pay')


class JobPositionCandidateAdmin(NoDeleteModelAdmin):
    list_display = ('position_need', 'developer', 'status', 'submitter', 'created_at')


if settings.PRODUCTION:
    admin.site.register(Project, ProjectAdmin)
else:
    admin.site.register(Project, ProjectFullAdmin)

admin.site.register(JobPosition, JobAdmin)

admin.site.register(JobPositionNeed, NoDeleteModelAdmin)

admin.site.register(JobPositionCandidate, JobPositionCandidateAdmin)

admin.site.register(ProjectLinks, NoDeleteModelAdmin)

admin.site.register(GanttTaskCatalogue)
# admin.site.register(GanttTaskTopic)

admin.site.register(ProjectPrototype, NoDeleteModelAdmin)
