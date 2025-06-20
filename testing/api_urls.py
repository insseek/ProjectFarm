from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import api

default_router = DefaultRouter()
default_router.register(r'case_libraries', api.TestCaseLibraryViewSet, base_name='case_libraries')
default_router.register(r'case_modules', api.TestCaseModuleViewSet, base_name='case_modules')
default_router.register(r'cases', api.TestCaseViewSet, base_name='cases')
default_router.register(r'projects', api.ProjectViewSet, base_name='projects')
default_router.register(r'project_platforms', api.ProjectPlatformViewSet, base_name='project_platforms')
default_router.register(r'project_tags', api.ProjectTagViewSet, base_name='project_tags')
default_router.register(r'project_case_modules', api.ProjectTestCaseModuleViewSet, base_name='project_case_modules')
default_router.register(r'project_cases', api.ProjectTestCaseViewSet, base_name='project_cases')
default_router.register(r'project_test_plans', api.ProjectTestPlanViewSet, base_name='project_test_plans')
default_router.register(r'plan_cases', api.TestPlanCaseViewSet, base_name='plan_cases')
default_router.register(r'project_bugs', api.BugViewSet, base_name='project_bugs')

app_name = 'testing_api'
urlpatterns = [
    path(r'', include(default_router.urls)),
    path(r'projects/<int:project_id>/members/', api.project_members, name='project_members'),
    path(r'projects/<int:project_id>/favorite/toggle/', api.project_favorite_toggle, name='project_favorite_toggle'),
    path(r'test_plan_modules/', api.test_plan_modules, name='test_plan_modules'),

    path(r'cases/excel_template/download/', api.download_case_template, {'template_type': 'test_case_template'},
         name='download_case_template'),
    path(r'cases/excel/check/', api.cases_file_check, name='cases_file_check'),
    path(r'cases/error_excel/download/', api.download_error_template, {'template_type': 'test_case_template'},
         name='download_error_template'),
    path(r'cases/excel/import/', api.import_cases, name='import_cases'),

    path(r'project_cases/excel_template/download/', api.download_case_template,
         {'template_type': 'project_test_case_template'},
         name='download_project_case_template'),
    path(r'project_cases/excel/check/', api.project_cases_file_check, name='project_cases_file_check'),
    path(r'project_cases/error_excel/download/', api.download_error_template,
         {'template_type': 'project_test_case_template'},
         name='download_error_template'),
    path(r'project_cases/excel/import/', api.import_project_cases, name='import_project_cases'),

    path(r'data/migrate/', api.data_migrate, name='data_migrate'),
    path(r'projects/<int:project_id>/bugs_trend_chart/', api.get_project_bugs_trend_chart_data, name='data_migrate'),

]


# default_router.register(r'projects/<int:project_id>/contracts', api.ProjectContractsViewSet,
#                         base_name='project_contracts')
