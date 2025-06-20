from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from auth_top.models import TopUser
from comments.models import Comment
from files.models import File
from logs.models import Log
from projects.models import Project
from proposals.models import Proposal


class CommonWorkOrder(models.Model):
    # # 每个状态可以进行的的操作
    STATUS_ACTIONS_CHOICES = {
        1: ['assign', 'begin', 'close'],
        2: ['assign', 'done', 'close'],
        3: ['close', 'reopen'],
        4: ['reopen'],
    }
    # 每个操作后对应的状态
    ACTIONS_TO_STATUS = {
        'begin': 2,
        'done': 3,
        'assign': 1,
        'close': 4,
        'reopen': 1
    }
    # 可以进行该操作的对应的状态
    ACTIONS_FROM_STATUS = {
        'assign': [1, 2],
        'done': [2],
        'begin': [1],
        'close': [1, 2, 3],
        'reopen': [3, 4],
    }
    PRIORITY_CHOICES = (
        (1, '低'),
        (2, '一般'),
        (3, '紧急'),
    )

    STATUS_CHOICES = (
        (1, '待处理'),  # pending
        (2, '处理中'),  # ongoing
        (3, '已完成'),  # done
        (4, '已关闭'),  # closed
        # (5, '无效关闭'),
    )

    WORK_ORDER_CHOICES = (
        ('ui_style', '设计-设计风格'),
        ('ui_global', '设计-整体设计'),
        ('ui_changes', '设计-设计调整'),
        ('ui_walkthrough', '设计-设计走查'),
        ('tpm_deployment', 'TPM-项目部署'),
        ('tpm_bug', 'TPM-BUG处理'),
        ('tpm_evaluation', 'TPM-技术评估'),
        ('tpm_other', 'TPM-其他'),
        ('other', '其他'),
    )
    work_order_type = models.CharField(verbose_name='工单类型', choices=WORK_ORDER_CHOICES, default='other', max_length=50)

    description = models.TextField(verbose_name='描述', blank=True, null=True)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_common_work_orders', blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL)
    principal = models.ForeignKey(User, verbose_name='负责人', related_name='common_work_orders', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    priority = models.IntegerField(verbose_name="优先级", choices=PRIORITY_CHOICES, default=1)
    title = models.CharField(verbose_name='标题', blank=True, null=True, max_length=256)
    status = models.IntegerField(verbose_name="状态", choices=STATUS_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    expiration_date = models.DateField(verbose_name='截止日期', blank=True, null=True)
    start_at = models.DateTimeField(verbose_name='开始时间', blank=True, null=True)
    start_by = models.ForeignKey(User, verbose_name='开始人', related_name='start_work_orders', blank=True, null=True,
                                 on_delete=models.SET_NULL)
    expected_at = models.DateField(verbose_name="预计完成时间", blank=True, null=True)
    done_at = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    closed_at = models.DateTimeField(verbose_name='关闭时间', blank=True, null=True)

    done_by = models.ForeignKey(User, verbose_name='完成人', related_name='done_work_orders', blank=True, null=True,
                                on_delete=models.SET_NULL)
    closed_by = models.ForeignKey(User, verbose_name='关闭人', related_name='closed_work_orders', blank=True, null=True,
                                  on_delete=models.SET_NULL)

    file_list = GenericRelation(File, related_query_name="work_orders")

    # 关联
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # 操作记录
    logs = GenericRelation(Log, related_query_name="common_work_orders")

    # 设计调整
    modify_page_number = models.IntegerField(verbose_name='修改页面数量', blank=True, null=True)
    add_page_number = models.IntegerField(verbose_name='新增页面数量', blank=True, null=True)

    # 设计风格
    page_number = models.IntegerField(verbose_name='页面数量', blank=True, null=True)
    style_type = models.IntegerField(verbose_name='风格种类', blank=True, null=True)

    # 整体设计
    page_number_range = models.CharField(verbose_name='页面数量范围', max_length=20, blank=True, null=True)
    practical_page_number = models.IntegerField(verbose_name='实际页面数量', blank=True, null=True)

    # BUG处理
    bug_link = models.CharField(verbose_name='bug链接', blank=True, null=True, max_length=256)

    # 项目部署
    data_link = models.CharField(verbose_name='部署资料链接', blank=True, null=True, max_length=256)

    def __str__(self):
        return self.description or self.get_work_order_type_display()

    class Meta:
        verbose_name = '工单'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.status == 4:
            if not self.closed_at:
                self.closed_at = timezone.now()
        else:
            if self.closed_at:
                self.closed_at = None
        if self.status == 3:
            if not self.done_at:
                self.done_at = timezone.now()
        elif self.status == 2:
            if not self.start_at:
                self.start_at = timezone.now()
        elif self.status == 1:
            self.closed_by = None
            self.closed_at = None
            self.done_at = None
            self.done_by = None
            self.start_at = None
            self.start_by = None
        super(CommonWorkOrder, self).save(*args, **kwargs)

    def get_status_value(self, status):
        status_dict = {'pending': 1, 'ongoing': 2, 'done': 3, 'closed': 4}
        return status_dict.get(status, None)

    @property
    def participants(self):
        return [self.submitter, self.principal, self.start_by, self.done_by, self.closed_by]

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def stair_work_order(self):
        if self.work_order_type in ['ui_style', 'ui_global', 'ui_changes', 'ui_walkthrough']:
            return 'design'
        else:
            return 'tpm'

    @property
    def content_object_name(self):
        if self.content_object:
            return str(self.content_object)
        else:
            return "其他"

    @classmethod
    def user_submit_work_orders(cls, user, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(submitter_id=user.id)

    @classmethod
    def user_principal_work_orders(cls, user, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(principal_id=user.id)

    @classmethod
    def closed_work_orders(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(closed_at__isnull=False)

    @classmethod
    def ongoing_work_orders(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(closed_at__isnull=True)

    @classmethod
    def design_work_orders(cls):
        return cls.objects.filter(work_order_type__in=['ui_style', 'ui_global', 'ui_changes', 'ui_walkthrough'])

    @classmethod
    def tpm_work_orders(cls):
        return cls.objects.filter(work_order_type__in=['tpm_deployment', 'tpm_bug', 'tpm_evaluation', 'tpm_other'])

    @property
    def files(self):
        return self.file_list.filter(is_deleted=False).order_by('created_at')

    @property
    def comments_count(self):
        count = 0
        for log in self.operation_logs.all():
            count = count + len(log.comments.all())
        return count


class WorkOrderOperationLog(models.Model):
    TYPE_CHOICES = (
        ('create', '创建'),
        ('edit', '编辑'),
        ('assign', '指派'),
        ('begin', '确认'),
        ('close', '关闭'),
        ('reopen', '重启'),
        ('done', '完成'),
        ('comment', '评论'),
        ('modify', '修改预计完成时间'),
        ('other', '操作'),
    )
    work_order = models.ForeignKey(CommonWorkOrder, verbose_name='工单', related_name='operation_logs',
                                   on_delete=models.CASCADE)
    operator = models.ForeignKey(User, related_name='work_order_operation_logs', verbose_name='操作人', null=True,
                                 blank=True,
                                 on_delete=models.SET_NULL)
    remarks = models.TextField(verbose_name='备注', null=True, blank=True)
    log_type = models.CharField(verbose_name="操作类型", max_length=15, choices=TYPE_CHOICES, default='other')
    origin_assignee = models.ForeignKey(User, verbose_name='原分配人',
                                        null=True, blank=True,
                                        related_name='origin_assignee_work_order_operation_logs',
                                        on_delete=models.SET_NULL)
    new_assignee = models.ForeignKey(User, verbose_name='新分配人',
                                     null=True, blank=True,
                                     related_name='new_assignee_work_order_operation_logs',
                                     on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    created_date = models.DateField(auto_now_add=True)
    expected_at = models.DateField(verbose_name='预计完成日期', null=True, blank=True)
    comments = GenericRelation(Comment, related_query_name="work_order_operation_logs")

    class Meta:
        verbose_name = '工单操作记录'

    def __str__(self):
        return "{}{}了工单".format(self.operator.username, self.get_log_type_display())

    @classmethod
    def build_log(cls, work_order, operator, log_type='other', remarks=None, origin_assignee=None, new_assignee=None,
                  comment=None, expected_at=None):
        log = cls(work_order=work_order, operator=operator, log_type=log_type, remarks=remarks,
                  origin_assignee=origin_assignee, expected_at=expected_at,
                  new_assignee=new_assignee)
        log.save()
        if comment:
            Comment.objects.create(author=operator, content=comment, content_object=log)
        return log

    @classmethod
    def build_comment_log(cls, work_order, operator, content, content_text=None, parent=None):
        if not parent:
            work_order_ob = cls.objects.create(work_order=work_order, operator=operator, log_type="comment")
            comment = Comment.objects.create(author=operator, content=content, content_text=content_text,
                                             content_object=work_order_ob)
            return comment
        else:
            if getattr(parent.content_object, 'work_order') == work_order and not parent.parent:
                comment = Comment.objects.create(author=operator, content=content, content_text=content_text,
                                                 content_object=parent.content_object, parent=parent)
                return comment
