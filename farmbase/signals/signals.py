from django.db.models.signals import ModelSignal

# 自定义signal
# project_playbook_check_item_task = ModelSignal(
#     providing_args=["instance", "created", 'task_name', 'expected_at', 'callback_code'],
#     use_caching=True)

# 使用
# project_playbook_check_item_task.send(sender=check_item.__class__, instance=check_item,
#                                                               created=True, task_name="会议2：原型统一评审",
#                                                               expected_at=expected_at,
#                                                               callback_code='project_playbook_prototype_prd_check_item_task')
