from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.db import models
from django.utils import timezone
from taggit.managers import TaggableManager


class Task(models.Model):
    # 除了common 其他为自动创建的待办事项
    TASK_TYPES = (
        ('common', '普通'),
        ('lead_new_task', '线索新任务'),

        ('proposal_new_task', '需求新任务'),
        ('proposal_contact', '需求初次联系'),
        ('proposal_need_report', '需求需要报告'),

        ('project_payment', '项目收款'),  # 项目的合同已经到了预计收款日期，但仍未收到款
        ('project_position_need', '项目职位需求'),
        ('project_position_candidate', '项目职位需求候选人'),
        ('project_position_star_rating', '项目职位评分'),

        ('project_position_star_rating', '项目职位评分'),

        ('regular_contract_payment', '固定工程师合同'),

    )
    '''
        content_object 任务关联的主体、source_object 任务的直接来源对象
        比如项目中 项目合同、工程师需求等自动生成的任务
    '''
    task_type = models.CharField(verbose_name='任务类型', choices=TASK_TYPES, max_length=50, default='common')
    name = models.TextField(verbose_name='名称')
    creator = models.ForeignKey(User, verbose_name='创建者', related_name='created_tasks', on_delete=models.SET_NULL,
                                null=True, blank=True)
    principal = models.ForeignKey(User, verbose_name='负责人', related_name='tasks', on_delete=models.SET_NULL, null=True,
                                  blank=True)
    expected_at = models.DateField(verbose_name="预计结束时间")
    is_done = models.BooleanField(verbose_name='已完成', default=False)
    done_at = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)

    # content_object 任务关联的主体
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # source_object 任务的直接来源对象
    source_type = models.ForeignKey(ContentType, related_name="source_tasks", verbose_name='任务来源model',
                                    on_delete=models.CASCADE, blank=True, null=True)
    source_id = models.PositiveIntegerField(verbose_name='任务来源对象id', blank=True, null=True)
    source_object = GenericForeignKey('source_type', 'source_id')
    callback_code = models.CharField(verbose_name="回调代号", max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    tags = TaggableManager()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.done_at:
            self.is_done = True
        else:
            self.is_done = False
        super(Task, self).save(*args, **kwargs)

    class Meta:
        verbose_name = '任务'

    def is_today(self):
        return timezone.now().date() == self.expected_at

    def is_past(self):
        return timezone.now().date() > self.expected_at

    @property
    def task_type_display(self):
        return self.get_task_type_display()

    @classmethod
    def undone_tasks(cls):
        return cls.objects.filter(is_done=False)

    # 自动完成的任务不能手动重置状态
    @property
    def auto_close_required(self):
        if self.task_type in ['lead_new_task', 'proposal_contact', 'proposal_new_task', 'project_payment',
                              'project_position_candidate', 'project_position_star_rating', 'regular_contract_payment']:
            return True
        return False
