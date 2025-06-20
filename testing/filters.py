import re

import django_filters
from django.db.models import Q

from testing.models import TestCase, ProjectTestCase, ProjectTestPlan, TestPlanCase, Bug
from projects.models import Project


class ProjectFilter(django_filters.FilterSet):
    managers = django_filters.CharFilter(method='get_managers_filter')
    tests = django_filters.CharFilter(method='get_tests_filter')

    class Meta:
        model = Project
        fields = ('managers', 'tests')

    def get_managers_filter(self, queryset, name, value):
        if value:
            user_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(manager__top_user__id__in=user_list)

        return queryset

    def get_tests_filter(self, queryset, name, value):
        if value:
            user_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(
                Q(tests__top_user__id__in=user_list) | Q(job_positions__developer__top_user__id__in=user_list))

        return queryset


class ProjectTestPlanFilter(django_filters.FilterSet):
    platforms = django_filters.CharFilter(method='get_platforms_filter')

    class Meta:
        model = ProjectTestPlan
        fields = ('platforms',)

    def get_platforms_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(platform_id__in=value_list).order_by('-index')

        return queryset


class TestCaseFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method='get_status_filter')

    class Meta:
        model = TestCase
        fields = ('status',)

    def get_status_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(status__in=value_list)
        return queryset


class ProjectTestCaseFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method='get_status_filter')

    creators = django_filters.CharFilter(method='get_creators_filter')
    tags = django_filters.CharFilter(method='get_tags_filter')

    cases = django_filters.CharFilter(method='get_cases_filter')
    case_type = django_filters.CharFilter(method='get_case_type_filter')
    flow_type = django_filters.CharFilter(method='get_flow_type_filter')

    class Meta:
        model = ProjectTestCase
        fields = ('status', 'creators', 'tags', 'case_type', 'flow_type')

    def get_status_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(status__in=value_list)
        return queryset

    def get_creators_filter(self, queryset, name, value):
        if value:
            user_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(creator_id__in=user_list)
        return queryset

    def get_tags_filter(self, queryset, name, value):
        if value:
            user_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(tags__id__in=user_list).distinct()
        return queryset

    def get_cases_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(id__in=value_list).distinct()
        return queryset

    def get_case_type_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(case_type__in=value_list).distinct()
        return queryset

    def get_flow_type_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(flow__in=value_list).distinct()
        return queryset


class TestPlanCaseFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method='get_status_filter')
    tags = django_filters.CharFilter(method='get_tags_filter')

    class Meta:
        model = TestPlanCase
        fields = ('status', 'tags')

    def get_status_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(status__in=value_list)
        return queryset

    def get_tags_filter(self, queryset, name, value):
        if value:
            user_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(tags__id__in=user_list).distinct()

        return queryset


class BugFilter(django_filters.FilterSet):
    modules = django_filters.CharFilter(method='get_modules_filter')
    bug_types = django_filters.CharFilter(method='get_bug_types_filter')
    platforms = django_filters.CharFilter(method='get_platforms_filter')
    priorities = django_filters.CharFilter(method='get_priorities_filter')
    assignees = django_filters.CharFilter(method='get_assignees_filter')
    creators = django_filters.CharFilter(method='get_creators_filter')
    fixed_by = django_filters.CharFilter(method='get_fixed_by_filter')
    status = django_filters.CharFilter(method='get_status_filter')
    tags = django_filters.CharFilter(method='get_tags_filter')

    class Meta:
        model = Bug
        fields = (
            'modules', 'bug_types', 'platforms', 'priorities', 'assignees', 'status', 'creators', 'fixed_by', 'tags')

    def get_modules_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(module_id__in=filter_list).distinct()
        return queryset

    def get_bug_types_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(bug_type__in=filter_list).distinct()
        return queryset

    def get_platforms_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(platform_id__in=filter_list).distinct()
        return queryset

    def get_priorities_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(priority__in=filter_list).distinct()
        return queryset

    def get_assignees_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(assignee_id__in=filter_list).distinct()
        return queryset

    def get_fixed_by_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(fixed_by_id__in=filter_list).distinct()
        return queryset

    def get_creators_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(creator_id__in=filter_list).distinct()
        return queryset

    def get_status_filter(self, queryset, name, value):
        if value:
            value_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(status__in=value_list)
        return queryset

    def get_tags_filter(self, queryset, name, value):
        if value:
            filter_list = re.sub(r'[;；,，]', ' ', value).split()
            queryset = queryset.filter(tags__id__in=filter_list).distinct()
        return queryset
