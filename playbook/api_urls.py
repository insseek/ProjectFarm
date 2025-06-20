from django.urls import path

from . import api

app_name = 'playbook_api'
urlpatterns = [
    path(r'templates', api.PlaybookTemplateList.as_view(), name='playbook_templates'),

    path(r'templates/proposal/online_version/', api.proposal_online_version, name='proposal_online_version'),
    path(r'templates/project/online_version/', api.project_online_version, name='project_online_version'),

    path(r'templates/<int:template_id>', api.PlaybookTemplateDetail.as_view(), name='playbook_template_detail'),
    path(r'templates/<int:template_id>/publish', api.publish_playbook_template, name='publish_playbook_template'),

    path(r'templates/stages/<int:stage_id>/check_groups', api.TemplateCheckGroupList.as_view(),
         name='playbook_template_stage_check_groups'),

    path(r'templates/stages/check_groups/<int:check_group_id>', api.TemplateCheckGroupDetail.as_view(),
         name='playbook_template_stage_check_group_detail'),

    path(r'templates/stages/check_groups/<int:check_group_id>/check_items', api.TemplateCheckItemList.as_view(),
         name='playbook_template_stage_check_group_check_items'),

    path(r'templates/stages/check_groups/check_items/<int:check_item_id>', api.TemplateCheckItemDetail.as_view(),
         name='playbook_template_stage_check_group_check_item_detail'),

    path(r'templates/stages/check_groups/check_items/<int:check_item_id>/links', api.TemplateCheckItemLinks.as_view(),
         name='playbook_template_check_item_links'),

    path(r'templates/stages/check_groups/drag', api.drag_playbook_template_stage_check_group,
         name='drag_playbook_template_stage_check_group'),

    path(r'templates/stages/check_groups/check_items/drag', api.drag_playbook_template_stage_check_group_check_item,
         name='drag_playbook_template_stage_check_group_check_item'),

    path(r'templates/stages/check_groups/check_items/drag', api.drag_playbook_template_stage_check_group_check_item,
         name='drag_playbook_template_stage_check_group_check_item'),

    path(r'templates/proposal/revision_histories', api.proposal_playbook_templates_revision_histories,
         name='proposal_playbook_templates_revision_histories'),

    path(r'templates/project/revision_histories', api.project_playbook_templates_revision_histories,
         name='project_playbook_templates_revision_histories'),

    path(r'templates/<int:template_id>/revision_history', api.playbook_template_revision_history,
         name='playbook_template_revision_history'),

    path(r'check_items/<int:id>/date', api.CheckItemDate.as_view(), name='check_item_date'),

    path(r'check_groups/<int:obj_id>/finish', api.handle_check_group, {'action_type': 'finish'},
         name='finish_check_group'),
    path(r'check_groups/<int:obj_id>/skip', api.handle_check_group, {'action_type': 'skip'}, name='skip_check_group'),
    path(r'check_items/<int:obj_id>/finish', api.handle_check_item, {'action_type': 'finish'},
         name='finish_check_item'),
    path(r'check_items/<int:obj_id>/skip', api.handle_check_item, {'action_type': 'skip'}, name='skip_check_item'),
    path(r'check_items/<int:obj_id>/reset', api.handle_check_item, {'type': 'reset'}, name='reset_check_item'),
    path(r'check_groups/<int:obj_id>/reset', api.handle_check_group, {'type': 'reset'}, name='reset_check_group'),

    path(r'stages/<int:id>/skip', api.skip_stage, name='skip_stage'),

    path(r'proposals/<int:id>', api.proposal_playbook_stages, name='proposal_playbook'),
    path(r'projects/<int:id>', api.project_playbook_stages, name='project_playbook'),
    path(r'data/migrate', api.data_migrate, name='data_migrate'),

]
