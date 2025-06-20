import json
from datetime import datetime, timedelta
from copy import deepcopy

from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from tasks.models import Task
from farmbase.utils import this_week_day, next_week_day, in_the_same_week


class LinkItem(models.Model):
    name = models.CharField(verbose_name="名称", max_length=68)
    url = models.CharField(verbose_name="链接地址", max_length=81)
    index = models.IntegerField(verbose_name='位置')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '链接'
        ordering = ['index']


class Stage(models.Model):
    MEMBER_CHOICES = (
        ('manager', '项目经理'),  # 2021/5/6  项目playbook中 只保留有 项目经理playbook
        ('product_manager', '产品经理'),
    )

    STAGE_CODES = (
        # 需求
        ('pending', '等待认领'),
        ('contact', '等待沟通'),
        ('ongoing', '进行中'),
        ('biz_opp', '商机'),
        ('contract', '成单交接'),
        ('deal', '成单'),
        ('no_deal', '未成单'),

        # 项目
        ('prd', '原型'),
        ('design', '设计'),
        ('development', '开发'),
        ('test', '测试'),
        ('acceptance', '验收'),
        # ('completion', '完成'),
    )

    member_type = models.CharField(verbose_name="角色类型", max_length=20, choices=MEMBER_CHOICES,
                                   default='product_manager')
    name = models.CharField(verbose_name="阶段名称", max_length=50)

    # 和项目阶段  需求阶段的代号对应
    stage_code = models.CharField(verbose_name="阶段代号", choices=STAGE_CODES, max_length=20, blank=True, null=True)

    index = models.IntegerField(verbose_name='位置')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # 时间点
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    project_stage = models.ForeignKey('projects.ProjectStage', verbose_name="项目阶段", related_name='playbook_stages',
                                      blank=True, null=True,
                                      on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Playbook阶段'
        ordering = ['index']

    @property
    def status_index(self):
        if self.content_type.model == 'proposal':
            return self.content_object.get_status_index_by_code(self.stage_code)

    @property
    def stage_index(self):
        return self.status_index

    @property
    def is_previous_stage(self):
        if self.content_type.model == 'project':
            if self.project_stage:
                return self.project_stage.is_previous_stage
        else:
            return self.stage_index < self.content_object.stage_index

    @property
    def is_current_stage(self):
        if self.content_type.model == 'project':
            if self.project_stage:
                return self.project_stage.is_current_stage
        else:
            return self.stage_index == self.content_object.stage_index

    @property
    def is_next_stage(self):
        if self.content_type.model == 'project':
            if self.project_stage:
                return self.project_stage.is_next_stage
        else:
            return self.stage_index > self.content_object.stage_index

    @property
    def stage_start_date(self):
        if self.content_type.model == 'project':
            if self.project_stage:
                return self.project_stage.start_date

    @property
    def stage_end_date(self):
        if self.content_type.model == 'project':
            if self.project_stage:
                return self.project_stage.end_date


# 组、任务的注意事项
class InfoItem(models.Model):
    description = models.TextField(verbose_name='描述')
    index = models.IntegerField(verbose_name='位置')

    # 注意事项里的链接
    links = GenericRelation(LinkItem, related_query_name="info_items")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Playbook注意项'
        ordering = ['index']


# 组
class ChecklistItem(models.Model):
    stage = models.ForeignKey(Stage, blank=True, null=True, related_name='check_groups',
                              on_delete=models.CASCADE)
    description = models.TextField(verbose_name='描述')
    index = models.IntegerField(verbose_name='位置')
    checked = models.BooleanField(verbose_name='完成', default=False)
    skipped = models.BooleanField(verbose_name='跳过', default=False)
    completed_at = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)

    # 时间点
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Playbook检查项组'
        ordering = ['index']

    def save(self, *args, **kwargs):
        if self.skipped or self.checked:
            if not self.completed_at:
                self.completed_at = timezone.now()
        super(ChecklistItem, self).save(*args, **kwargs)

    def reset_init_data(self):
        if self.completed_at:
            self.completed_at = None
            self.skipped = False
            self.checked = False
            self.save()
        return self

    def rebuild_completed_at(self):
        # 存在子项
        if self.check_items.exists():
            if self.completed_at:
                # 存在未完成的子项
                if self.check_items.filter(completed_at__isnull=True).exists():
                    self.completed_at = None
                    self.skipped = False
                    self.checked = False
                    self.save()
            else:
                if not self.check_items.filter(completed_at__isnull=True).exists():
                    if self.check_items.filter(checked=True).exists():
                        self.checked = True
                    else:
                        self.skipped = True
                    self.completed_at = timezone.now()
                    self.save()


class CheckItem(models.Model):
    PERIOD_CHOICES = (
        ('once', '一次性任务'),
        ('weekly', '每周任务'),
        # ('daily', '每日任务')
    )
    # TYPE_CHOICES = (
    #     ('会议', '会议'),
    #     ('Farm', 'Farm'),
    #     ('Quip', 'Quip'),
    #     ('GitLab', 'GitLab'),
    #     ('微信', '微信'),
    #     ('YApi', 'YApi'),
    #     ('Axure', 'Axure'),
    #     ('其他', '其他'),
    # )
    WEEKDAY_CHOICES = (
        (1, '周一'),
        (2, '周二'),
        (3, '周三'),
        (4, '周四'),
        (5, '周五'),
        (6, '周六'),
        (7, '周日'),
    )
    EXPECTED_DATE_BASE_CHOICES = (
        ('stage_start_date', '阶段开始日期'),
        ('stage_end_date', '阶段结束日期'),
        # ('sprint_start_date', 'Sprint开始日期'),  # 取消
        # ('sprint_end_date', 'Sprint结束日期')  # 取消
    )
    check_group = models.ForeignKey(ChecklistItem, blank=True, null=True, related_name='check_items',
                                    on_delete=models.CASCADE)
    description = models.TextField(verbose_name='描述')
    index = models.IntegerField(verbose_name='位置')
    type = models.CharField(verbose_name="类型", max_length=20, blank=True, null=True)
    period = models.CharField(verbose_name="周期", max_length=15, choices=PERIOD_CHOICES, default='once')
    notice = models.TextField(verbose_name='注意事项', blank=True, null=True)
    checked = models.BooleanField(verbose_name='完成', default=False)
    skipped = models.BooleanField(verbose_name='跳过', default=False)
    completed_at = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    # 任务级别的注意事项 链接
    links = GenericRelation(LinkItem, related_query_name="check_item")
    info_items = GenericRelation(InfoItem, related_query_name="check_item")
    # 项目playbook可以设置期望完成时间
    expected_date_base = models.CharField(verbose_name="期望日期基准", max_length=20, choices=EXPECTED_DATE_BASE_CHOICES,
                                          blank=True,
                                          null=True)
    expected_date_base_timedelta_days = models.IntegerField(verbose_name="期望日期基准间隔天数", blank=True,
                                                            null=True)
    # 周一到周日为  [1,2,3,4,5,6,7]   前端周日为0、python中weekday周日是6  统一用1-7  使用时再处理
    expected_weekday = models.IntegerField(verbose_name="每周任务期望周几", choices=WEEKDAY_CHOICES, blank=True,
                                           null=True)
    expected_date = models.DateField(verbose_name="预计结束日期", blank=True, null=True)
    # 时间点
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Playbook检查项'
        ordering = ['index']

    @classmethod
    def pending_check_items(cls):
        return cls.objects.filter(completed_at__isnull=True)

    @classmethod
    def todo_check_items(cls, day=timezone.now().date()):
        return cls.objects.filter(completed_at__isnull=True, expected_date__lte=day)

    def save(self, *args, **kwargs):
        if self.skipped or self.checked:
            if not self.completed_at:
                self.completed_at = timezone.now()
        if not self.completed_at and not self.expected_date:
            self.expected_date = self.build_expected_date()
        super(CheckItem, self).save(*args, **kwargs)

    def reset_init_data(self):
        if self.completed_at:
            self.completed_at = None
            self.skipped = False
            self.checked = False
            self.save()
        return self

    @property
    def stage_start_date(self):
        return self.check_group.stage.stage_start_date

    @property
    def stage_end_date(self):
        return self.check_group.stage.stage_end_date

    @property
    def current_sprint(self):
        return self.check_group.stage.current_sprint

    def build_expected_date(self, to_save=False):
        expected_date = deepcopy(self.expected_date)
        if self.check_group.stage.content_type.model == 'project':
            if self.period == 'weekly':
                today = timezone.now().date()
                if self.expected_weekday is not None:
                    if self.stage_start_date:
                        if self.stage_end_date:
                            # 本阶段
                            if self.stage_end_date >= today >= self.stage_start_date:
                                expected_date = this_week_day(self.expected_weekday - 1, today)
                            # 阶段前
                            elif today < self.stage_start_date:
                                expected_date = this_week_day(self.expected_weekday - 1, self.stage_start_date)
                            # 今天超过本阶段  但是同一周
                            elif today > self.stage_end_date and in_the_same_week([self.stage_end_date, today]):
                                expected_date = this_week_day(self.expected_weekday - 1, today)
                        else:
                            if today < self.stage_start_date:
                                expected_date = this_week_day(self.expected_weekday - 1, self.stage_start_date)
                            # 同阶段
                            elif self.check_group.stage.stage_code == self.check_group.stage.content_object.stage_code:
                                expected_date = this_week_day(self.expected_weekday - 1, self.stage_start_date)
            else:
                timedelta_days = self.expected_date_base_timedelta_days or 0
                base_date = None
                if self.expected_date_base == 'stage_start_date':
                    base_date = self.stage_start_date
                elif self.expected_date_base == 'stage_end_date':
                    base_date = self.stage_end_date
                if base_date:
                    expected_date = base_date + timedelta(days=timedelta_days)

            # elif self.period == 'sprint':
            #     today = timezone.now().date()
            #     timedelta_days = self.expected_date_base_timedelta_days or 0
            #     base_sprint = None
            #     if self.current_sprint:
            #         base_sprint = self.current_sprint
            #     elif self.first_sprint and today < self.first_sprint.start_time:
            #         base_sprint = self.first_sprint
            #
            #     if base_sprint:
            #         base_date = None
            #         if self.expected_date_base == 'sprint_start_date':
            #             base_date = base_sprint.start_time
            #         elif self.expected_date_base == 'sprint_end_date':
            #             base_date = base_sprint.end_time
            #         if base_date:
            #             expected_date = base_date + timedelta(days=timedelta_days)
            if to_save:
                if self.expected_date != expected_date:
                    self.expected_date = expected_date
                    self.save()
        return expected_date


class Template(models.Model):
    TYPE_CHOICES = (
        ('proposal', '需求'),
        ('project', '项目'),
    )
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('online', '线上版本'),
        ('history', '历史版本'),
    )
    MEMBER_CHOICES = (
        ('manager', '项目经理'),
        ('product_manager', '产品'),
    )
    origin = models.ForeignKey(to='self', verbose_name="创建来源", blank=True, null=True,
                               related_name='clone_playbook_templates',
                               on_delete=models.SET_NULL)
    template_type = models.CharField(verbose_name="模板类型", max_length=15, choices=TYPE_CHOICES)
    member_type = models.CharField(verbose_name="角色类型", max_length=20, choices=MEMBER_CHOICES,
                                   default='product_manager')
    version = models.CharField(verbose_name='当前版本', max_length=10, default='1.0', blank=True, null=True)
    status = models.CharField(verbose_name='状态', max_length=15, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(verbose_name='删除状态', default=True)
    remarks = models.CharField(verbose_name="备注", max_length=64, blank=True, null=True)
    creator = models.ForeignKey(User, verbose_name='创建人', related_name='create_playbook_templates', blank=True,
                                null=True,
                                on_delete=models.SET_NULL)
    last_operator = models.ForeignKey(User, verbose_name='最近编辑人', related_name='last_edit_playbook_templates',
                                      blank=True,
                                      null=True, on_delete=models.SET_NULL)
    publisher = models.ForeignKey(User, verbose_name='发布人', related_name='publish_playbook_templates', blank=True,
                                  null=True, on_delete=models.SET_NULL)
    # 时间点
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    published_at = models.DateTimeField(verbose_name="发布时间", blank=True, null=True)

    def __str__(self):
        return "{} v{}".format(self.get_template_type_display(), self.version)

    class Meta:
        verbose_name = 'Playbook模板'

    @classmethod
    def get_new_version(cls, template_type, member_type, status):
        template_type_choices = [template_type for template_type, template_type_display in cls.TYPE_CHOICES]
        member_type_choices = [member_type for member_type, member_type_display in cls.MEMBER_CHOICES]
        status_choices = [status for status, status_display in cls.STATUS_CHOICES]
        if template_type in template_type_choices and status in status_choices and member_type in member_type_choices:
            exists_templates = cls.objects.filter(template_type=template_type, member_type=member_type, status=status,
                                                  is_active=True)
            if exists_templates.exists():
                last_template = exists_templates.order_by('-version').first()
                version = float(last_template.version) + 0.1
                version = str(round(version, 1))
                return version
        return '1.0'

    @classmethod
    def get_online_template(cls, template_type, member_type):
        exists_templates = cls.objects.filter(template_type=template_type, member_type=member_type, status='online',
                                              is_active=True)
        if exists_templates.exists():
            last_template = exists_templates.order_by('-version').first()
            exists_templates.exclude(pk=last_template.id).update(status='history')
            return last_template


class TemplateStage(models.Model):
    STAGE_CODES = (
        # 需求
        ('pending', '等待认领'),
        ('contact', '等待沟通'),
        ('ongoing', '进行中'),
        ('biz_opp', '商机'),
        ('contract', '成单交接'),
        ('deal', '成单'),
        ('no_deal', '未成单'),

        # 项目
        ('prd', '原型'),
        ('design', '设计'),
        ('development', '开发'),
        ('test', '测试'),
        ('acceptance', '验收'),
        # ('completion', '完成'),
    )
    PROJECT_STAGES = (
        ('prd', '原型'),
        ('design', '设计'),
        ('development', '开发'),
        ('test', '测试'),
        ('acceptance', '验收'),
    )
    playbook_template = models.ForeignKey(Template, verbose_name="Playbook模板", related_name='stages',
                                          on_delete=models.CASCADE)
    name = models.CharField(verbose_name="阶段名称", max_length=50)
    # 和项目阶段  需求阶段的代号对应
    stage_code = models.CharField(verbose_name="阶段代号", choices=STAGE_CODES, max_length=20, blank=True, null=True)
    index = models.IntegerField(verbose_name='位置')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Playbook模板阶段'
        ordering = ['index']


class TemplateCheckGroup(models.Model):
    playbook_template = models.ForeignKey(Template, verbose_name="Playbook模板", related_name='check_groups',
                                          blank=True, null=True, on_delete=models.CASCADE)
    template_stage = models.ForeignKey(TemplateStage, verbose_name="Playbook模板阶段", related_name='check_groups',
                                       blank=True, null=True, on_delete=models.CASCADE)
    description = models.TextField(verbose_name='描述')
    index = models.IntegerField(verbose_name='位置')
    origin = models.ForeignKey(to='self', verbose_name="创建来源", blank=True, null=True, related_name='clone_check_groups',
                               on_delete=models.SET_NULL)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Playbook模板检查项组'
        ordering = ['index']


class TemplateCheckItem(models.Model):
    PERIOD_CHOICES = (
        ('once', '一次性任务'),
        ('weekly', '每周任务'),
        # ('daily', '每日任务')
    )
    CHECK_ITEM_TYPE_CHOICES = (
        ('会议', '会议'),
        ('Farm', 'Farm'),
        ('Quip', 'Quip'),
        ('GitLab', 'GitLab'),
        ('微信', '微信'),
        ('YApi', 'YApi'),
        ('飞书', '飞书'),
        ('Axure', 'Axure'),
        ('其他', '其他'),
    )
    EXPECTED_DATE_BASE_CHOICES = (
        ('stage_start_date', '阶段开始日期'),
        ('stage_end_date', '阶段结束日期'),
        # ('sprint_start_date', 'Sprint开始日期'),
        # ('sprint_end_date', 'Sprint结束日期')
    )
    WEEKDAY_CHOICES = (
        (1, '周一'),
        (2, '周二'),
        (3, '周三'),
        (4, '周四'),
        (5, '周五'),
        (6, '周六'),
        (7, '周日'),
    )
    playbook_template = models.ForeignKey(Template, verbose_name="Playbook模板", related_name='check_items',
                                          blank=True, null=True, on_delete=models.CASCADE)
    template_check_group = models.ForeignKey(TemplateCheckGroup, blank=True, null=True, related_name='check_items',
                                             on_delete=models.CASCADE)
    type = models.CharField(verbose_name="类型", max_length=20, choices=CHECK_ITEM_TYPE_CHOICES, blank=True, null=True)
    period = models.CharField(verbose_name="周期", max_length=15, choices=PERIOD_CHOICES, default='once')
    description = models.TextField(verbose_name='描述')
    index = models.IntegerField(verbose_name='位置')
    origin = models.ForeignKey(to='self', verbose_name="创建来源", blank=True, null=True, related_name='clone_check_items',
                               on_delete=models.SET_NULL)
    notice = models.TextField(verbose_name='注意事项', blank=True, null=True)

    # 项目playbook可以设置期望完成时间
    expected_date_base = models.CharField(verbose_name="期望日期基准", max_length=20, choices=EXPECTED_DATE_BASE_CHOICES,
                                          blank=True,
                                          null=True)

    expected_date_base_timedelta_days = models.IntegerField(verbose_name="期望日期基准间隔天数", blank=True,
                                                            null=True)
    # 周一到周日为  [1,2,3,4,5,6,7]   前端周日为0、python中weekday周日是6  统一用1-7  使用时再处理
    expected_weekday = models.IntegerField(verbose_name="每周任务期望周几", blank=True, choices=WEEKDAY_CHOICES,
                                           null=True)

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = 'Playbook模板检查项'
        ordering = ['index']


class TemplateLinkItem(models.Model):
    template_check_item = models.ForeignKey(TemplateCheckItem, blank=True, null=True, related_name='links',
                                            on_delete=models.CASCADE)
    name = models.CharField(verbose_name="名称", max_length=68)
    url = models.CharField(verbose_name="链接地址", max_length=81)
    index = models.IntegerField(verbose_name='位置')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Playbook模板任务链接'
        ordering = ['index']


class TemplateRevisionHistory(models.Model):
    playbook_template = models.OneToOneField(Template, verbose_name="Playbook模板", related_name='revision_history',
                                             on_delete=models.CASCADE)
    content_data = models.TextField(verbose_name='内容数据', blank=True, null=True)

    # 时间点
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    def __str__(self):
        return str(self.playbook_template) + ' 修改记录'

    @classmethod
    def build_playbook_template_revision_history(cls, playbook_template):
        from playbook.serializers import TemplateCheckGroupEditableFieldSerializer, \
            TemplateCheckItemEditableFieldSerializer
        origin_template = playbook_template.origin
        if not origin_template:
            return
        origin_template_check_groups = origin_template.check_groups.all()
        origin_template_check_items = origin_template.check_items.all()

        playbook_template_check_groups = playbook_template.check_groups.all()
        playbook_template_check_items = playbook_template.check_items.all()

        cloned_check_groups = playbook_template_check_groups.filter(origin_id__isnull=False).order_by(
            'template_stage__index', 'index')
        cloned_check_items = playbook_template_check_items.filter(origin_id__isnull=False).order_by(
            'template_check_group__template_stage__index', 'template_check_group__index', 'index')

        cloned_check_groups_origin_ids = set(cloned_check_groups.values_list('origin_id', flat=True))
        cloned_check_items_ids = set(cloned_check_items.values_list('origin_id', flat=True))
        origin_template_check_groups_ids = set(origin_template_check_groups.values_list('id', flat=True))
        origin_template_check_items_ids = set(origin_template_check_items.values_list('id', flat=True))

        deleted_check_groups_ids = origin_template_check_groups_ids - cloned_check_groups_origin_ids
        deleted_check_items_ids = origin_template_check_items_ids - cloned_check_items_ids

        deleted_check_groups = TemplateCheckGroup.objects.filter(id__in=deleted_check_groups_ids).order_by(
            'template_stage__index', 'index')
        deleted_check_items = TemplateCheckItem.objects.filter(id__in=deleted_check_items_ids).order_by(
            'template_check_group__template_stage__index', 'template_check_group__index', 'index')

        deleted_check_groups_data = TemplateCheckGroupEditableFieldSerializer(deleted_check_groups, many=True).data
        deleted_check_items_data = TemplateCheckItemEditableFieldSerializer(deleted_check_items, many=True).data

        insert_check_groups = playbook_template_check_groups.filter(origin_id__isnull=True).order_by(
            'template_stage__index', 'index')
        insert_check_items = playbook_template_check_items.filter(origin_id__isnull=True).order_by(
            'template_check_group__template_stage__index', 'template_check_group__index', 'index')

        insert_check_groups_data = TemplateCheckGroupEditableFieldSerializer(insert_check_groups, many=True).data
        insert_check_items_data = TemplateCheckItemEditableFieldSerializer(insert_check_items, many=True).data

        updated_check_groups_data = []
        updated_check_items_data = []

        for check_group in cloned_check_groups:
            origin_check_group = check_group.origin

            check_group_data = TemplateCheckGroupEditableFieldSerializer(check_group).data
            origin_check_group_data = TemplateCheckGroupEditableFieldSerializer(origin_check_group).data
            if check_group_data != origin_check_group_data:
                updated_check_group = {
                    "old_data": origin_check_group_data,
                    "new_data": check_group_data
                }
                updated_check_groups_data.append(updated_check_group)

        for check_group in cloned_check_items:
            origin_check_group = check_group.origin
            check_group_data = TemplateCheckItemEditableFieldSerializer(check_group).data
            origin_check_group_data = TemplateCheckItemEditableFieldSerializer(origin_check_group).data
            if check_group_data != origin_check_group_data:
                updated_check_group = {
                    "old_data": origin_check_group_data,
                    "new_data": check_group_data
                }
                updated_check_items_data.append(updated_check_group)

        result_data = {
            "insert": {"check_groups": insert_check_groups_data, "check_items": insert_check_items_data},
            "update": {"check_groups": updated_check_groups_data, "check_items": updated_check_items_data},
            "delete": {"check_groups": deleted_check_groups_data, "check_items": deleted_check_items_data},
        }

        content_data = json.dumps(result_data, ensure_ascii=False)
        log = cls(playbook_template=playbook_template, content_data=content_data)
        log.save()
        return log

    class Meta:
        verbose_name = 'Playbook模板修改记录'
