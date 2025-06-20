import random
import string
import uuid
import math
import json
import ast
from datetime import datetime, timedelta
from pprint import pprint
from copy import deepcopy

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db.models import Sum, IntegerField, When, Case, Q
from multiselectfield import MultiSelectField

from comments.models import Comment
from finance.models import JobPayment
from logs.models import Log, BrowsingHistory
from playbook.models import ChecklistItem, InfoItem, Stage
from tasks.models import Task
from farmbase.utils import encrypt_string
from gearfarm.utils.datetime_utils import get_date_by_timedelta_days, is_workday, next_workday
from farmbase.utils import gen_uuid


class Project(models.Model):
    # STATUS = (
    #     (5, '原型'),
    #     (5, '原型'),
    #     (6, '设计'),
    #     (7, '开发'),
    #     (8, '测试'),
    #     (9, '验收'),
    #     (10, '完成'),
    # )
    PROJECT_STATUS = (
        ('prd', '原型'),
        ('design', '设计'),
        ('development', '开发'),
        ('test', '测试'),
        ('acceptance', '验收'),
        ('completion', '完成'),
    )

    PROJECT_STATUS_DICT = {
        'prd': {'index': 0, 'code': 'prd', 'name': '原型'},
        'design': {'index': 1, 'code': 'design', 'name': '设计'},
        'development': {'index': 2, 'code': 'development', 'name': '开发'},
        'test': {'index': 3, 'code': 'test', 'name': '测试'},
        'acceptance': {'index': 4, 'code': 'acceptance', 'name': '验收'},
        'completion': {'index': 5, 'code': 'completion', 'name': '完成'},
    }

    # 交付审核时间点 + 42天为验收阶段
    PROJECT_STAGE_FIELDS = {
        'prd': {
            'start_date': {"field_name": "start_time", "verbose_name": "项目启动"},
            'end_date': {"field_name": "prd_confirmation_time", "verbose_name": "原型确认"}
        },
        'design': {
            'start_date': {"field_name": "ui_start_time", "verbose_name": "设计开始"},
            'end_date': {"field_name": "ui_confirmation_time", "verbose_name": "设计确认"}
        },
        'development': {
            'start_date': {"field_name": "dev_start_time", "verbose_name": "开发开始"},
            'end_date': {"field_name": "dev_completion_time", "verbose_name": "开发结束"}
        },
        'test': {
            'start_date': {"field_name": "test_start_time", "verbose_name": "测试开始"},
            'end_date': {"field_name": "test_completion_time", "verbose_name": "测试结束"},
        },
        'acceptance': {
            'start_date': {"field_name": "delivery_time", "verbose_name": "交付审核"},
            'end_date': {"field_name": "delivery_end_time", "verbose_name": "验收结束"},
        },
        'completion': {
            'start_date': {"field_name": "delivery_end_time", "verbose_name": "验收结束"},
            'end_date': {"field_name": "project_done_at", "verbose_name": "项目结束"},
        },
    }

    PROJECT_MEMBERS_FIELDS = [
        {"field_name": 'manager', "name": "项目经理", "short_name": 'PMO'},
        {"field_name": 'product_manager', "name": "产品", "short_name": 'PM'},
        {"field_name": 'mentor', "name": "导师", "short_name": '导师'},
        {"field_name": 'tpm', "name": "TPM", "short_name": 'TPM'},
        {"field_name": 'designer', "name": "设计", "short_name": 'UI'},
        {"field_name": 'test', "name": "测试", "short_name": 'QA'},
        {"field_name": 'bd', "name": "BD", "short_name": 'BD'},
    ]
    # 需要给工程师评分的角色
    NEED_STAR_RATING_MEMBERS_FIELDS = ('manager', 'product_manager', 'tpm', 'designer', 'tests')
    NEED_GRADE_MEMBERS_FIELDS = [
        {"field_name": 'manager', "name": "项目经理", "short_name": 'PMO'},
        {"field_name": 'product_manager', "name": "产品", "short_name": 'PM'},
        {"field_name": 'tpm', "name": "TPM", "short_name": 'TPM'},
        {"field_name": 'designer', "name": "设计", "short_name": 'UI'},
        {"field_name": 'test', "name": "测试", "short_name": 'QA'},
    ]
    name = models.CharField(verbose_name="项目名称", max_length=50)
    manager = models.ForeignKey(
        User,
        verbose_name="项目经理",
        related_name='manage_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    product_manager = models.ForeignKey(
        User,
        verbose_name="产品",
        related_name='product_manage_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    mentor = models.ForeignKey(
        User,
        verbose_name="导师",
        related_name='mentored_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    tpm = models.ForeignKey(
        User,
        verbose_name="技术项目经理",
        related_name='tpm_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    test = models.ForeignKey(
        User,
        verbose_name="测试工程师",
        related_name='test_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    tests = models.ManyToManyField(
        User,
        through='ProjectTest',
        verbose_name="测试工程师",
        related_name='tests_projects',
    )
    cs = models.ForeignKey(
        User,
        verbose_name="客户成功",
        related_name='cs_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    designer = models.ForeignKey(
        User,
        verbose_name="设计",
        related_name='design_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    clients = models.ManyToManyField('clients.Client', through='ProjectClient',
                                     verbose_name='项目客户', related_name='projects')
    bd = models.ForeignKey(
        User,
        verbose_name="BD",
        related_name='bd_projects',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    desc = models.TextField(verbose_name='描述', blank=True, null=True)
    deployment_info = models.TextField(verbose_name='部署测试信息', blank=True, null=True)
    deployment_servers = models.TextField(verbose_name='部署服务器信息', blank=True, null=True)
    track_code = models.TextField(verbose_name='追踪码', blank=True, null=True)

    logs = GenericRelation(Log, related_query_name="projects")
    tasks = GenericRelation(Task, related_query_name="projects")
    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')
    comments = GenericRelation(Comment, related_query_name="projects")

    playbook_stages = GenericRelation(Stage, related_query_name="projects")

    start_date = models.DateField(verbose_name="项目启动日期", blank=True, null=True)
    end_date = models.DateField(verbose_name="项目结束日期", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    deployed_at = models.DateTimeField(verbose_name="部署时间", blank=True, null=True)
    done_at = models.DateField(verbose_name="实际结束时间", blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.track_code:
            self.track_code = Project.gen_project_track_code()
        if self.deployment_servers and not self.deployed_at:
            self.deployed_at = timezone.now()
        super(Project, self).save(*args, **kwargs)

    @property
    def need_star_rating_members(self):
        members = set()
        for field_name in self.NEED_STAR_RATING_MEMBERS_FIELDS:
            if field_name == 'tests':
                tests = getattr(self, field_name).all()
                for test in tests:
                    if test.is_active:
                        members.add(test)
            else:
                member = getattr(self, field_name, None)
                if member and member.is_active:
                    members.add(member)
        return members

    @property
    def need_star_rating(self):
        if timezone.now().date() >= (self.end_date - timedelta(days=1)):
            if len(self.need_star_rating_job_positions):
                return True
        return False

    @property
    def need_star_rating_job_positions(self):
        need_star_rating = []
        job_positions = self.job_positions.filter(job_standard_score__isnull=True)
        for job_position in job_positions:
            if job_position.is_have_questionnaires:
                need_star_rating.append(job_position)
        return need_star_rating

    @property
    def is_done(self):
        return True if self.done_at else False

    @staticmethod
    def gen_project_track_code():
        track_code = gen_uuid(8)
        if Project.objects.filter(track_code=track_code).exists():
            Project.gen_project_track_code()
        return track_code

    @classmethod
    def developer_projects(cls, developer):
        developer_id = developer.id
        return cls.objects.filter(job_positions__developer_id=developer_id).distinct()

    @classmethod
    def top_user_projects(cls, top_user):
        if top_user.is_freelancer:
            return cls.developer_projects(top_user.developer)
        elif top_user.is_employee:
            return cls.user_projects(top_user.user)

    @classmethod
    def ongoing_projects(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(done_at__isnull=True)

    @classmethod
    def closed_projects(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(done_at__isnull=False)

    @classmethod
    def completion_projects(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(done_at__isnull=False)

    @classmethod
    def user_projects(cls, user, queryset=None, members=None, exclude_members=[]):
        queryset = cls.objects.all() if queryset is None else queryset
        project_member_fields = deepcopy(cls.PROJECT_MEMBERS_FIELDS)
        q1 = Q()
        q1.connector = 'OR'
        for member_filed in project_member_fields:
            field_name = member_filed['field_name']
            if members and field_name not in members:
                continue
            if field_name in exclude_members:
                continue
            if field_name == 'test':
                field_name = 'tests__id'
            else:
                field_name = field_name + '_id'
            q1.children.append((field_name, user.id))
        return queryset.filter(q1)

    def get_active_developers(self):
        developers = self.get_developers()
        return [developer for developer in developers if developer.is_active]

    def get_developers(self):
        job_positions = self.job_positions.all()
        developers = []
        for position in job_positions:
            if position.developer and position.developer not in developers:
                developers.append(position.developer)
        return developers

    @property
    def current_stages(self):
        today = timezone.now().date()
        stages = self.project_stages.filter(start_date__lte=today, end_date__gte=today).order_by('index')
        return stages

    @property
    def stage_code(self):
        return list(self.current_stages.values_list('stage_type', flat=True))

    @property
    def stage_display(self):
        return [self.PROJECT_STATUS_DICT[i]['name'] for i in self.status]

    @property
    def status(self):
        return self.stage_code

    def get_status_display(self):
        return ','.join(self.stage_display)

    @property
    def status_display(self):
        return ','.join(self.stage_display)

    @property
    def members(self):
        project = self
        members = []
        for member_filed in self.PROJECT_MEMBERS_FIELDS:
            if member_filed['field_name'] == 'test':
                continue
            field_name = member_filed['field_name']
            member = getattr(project, field_name, None)
            if member:
                members.append(member)
        project_tests = project.tests.all()
        for project_test in project_tests:
            members.append(project_test)
        return members

    @property
    def participants(self):
        return self.members

    def has_delivery_document(self):
        return self.delivery_documents.filter(is_deleted=False).filter(
            document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_README_NUMBER).exists()

    @property
    def demo_status(self):
        farm_projects_demo_status = cache.get('farm_projects_demo_status', {})
        if farm_projects_demo_status:
            project_id = self.id
            if project_id in farm_projects_demo_status:
                return farm_projects_demo_status[project_id]

    @property
    def job_positions_fully_paid(self):
        for job in self.job_positions.all():
            if not job.is_paid_off_valid_payments:
                return False
        return True

    def undone_tasks(self):
        tasks = self.tasks.filter(is_done=False).order_by('expected_at')
        return tasks

    def vacancies(self):
        positions = self.job_positions.filter(developer=None)
        if len(positions) > 0:
            return positions
        return None

    @property
    def developers_documents_need_sync(self):
        positions = self.job_positions.order_by('created_at')
        developer_ids = set()
        # 每个开发者对应的文档的同步情况
        for position in positions:
            developer = position.developer
            if developer.is_active:
                if developer.id not in developer_ids:
                    docs = developer.active_developers_documents()
                    for doc in docs:
                        if doc.project_developer_is_skipped(self, developer):
                            continue
                        sync_log = doc.developer_current_large_version_sync_log(developer)
                        if not sync_log:
                            return True
                    developer_ids.add(developer.id)
        return False

    def rebuild_dev_docs_checkpoint_status(self):
        checkpoint = self.technology_checkpoints.filter(name=TechnologyCheckpoint.DEV_DOCS_CHECKPOINT).first()
        if checkpoint:
            # 跳过的 就跳过了
            if checkpoint.status == 'skipped':
                return
            # 已经不是开发阶段了  就跳过了
            if not self.current_stages.filter(stage_type="'development'").exists() and checkpoint.status == 'done':
                return
            need_sync = self.developers_documents_need_sync
            new_status = 'pending' if need_sync else 'done'
            if checkpoint.status != new_status:
                checkpoint.status = new_status
                checkpoint.save()

    @classmethod
    def rebuild_project_dev_docs_checkpoint_status(cls, project):
        project.rebuild_dev_docs_checkpoint_status()

    @classmethod
    def rebuild_ongoing_projects_dev_docs_checkpoints_status(cls):
        for project in cls.ongoing_projects():
            project.rebuild_dev_docs_checkpoint_status()

    class Meta:
        verbose_name = '项目'


class ProjectClient(models.Model):
    PERMISSION_CHOICES = (
        ('prototype', '原型'),
        ('design', '设计'),
        ('demo_server', '测试地址'),
        ('delivery_document', '交付文档')
    )
    ADMIN_PERMISSIONS = (
        'prototype',
        'design',
        'demo_server',
        'delivery_document',
        'members'
    )
    project = models.ForeignKey(Project, verbose_name='项目', related_name='project_clients',
                                on_delete=models.CASCADE)
    client = models.ForeignKey('clients.Client', verbose_name='客户',
                               related_name='project_clients',
                               on_delete=models.CASCADE)
    is_admin = models.BooleanField(verbose_name='管理员', default=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    permissions = MultiSelectField(verbose_name="权限", choices=PERMISSION_CHOICES, null=True, blank=True)

    class Meta:
        verbose_name = '项目客户'
        ordering = ['created_at']

    def __str__(self):
        return self.project.name + "：" + self.client.username


class ProjectTest(models.Model):
    project = models.ForeignKey(Project, verbose_name='项目', related_name='project_tests',
                                on_delete=models.CASCADE)
    test = models.ForeignKey(User, verbose_name='测试',
                             related_name='project_tests',
                             on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = '项目测试'
        ordering = ['created_at']

    def __str__(self):
        return self.project.name + "：" + self.test.username


class ProjectLinks(models.Model):
    QUIP_FOLDER_TYPES = (
        ('auto', '自动创建'),
        ('select', '选择'),
        ('no_need', '不需要'),
    )
    project = models.OneToOneField(Project, verbose_name='项目', related_name='links', on_delete=models.CASCADE)
    # {'type':"project", 'id':10, 'name_with_namespace':'','name':'', 'web_url':''}
    git_project = models.TextField(verbose_name='GitLab项目', blank=True, null=True)
    gitlab_project_id = models.IntegerField(verbose_name='GitLab项目ID', blank=True, null=True)
    gitlab_group_id = models.IntegerField(verbose_name='GitLab组ID', blank=True, null=True)
    api_document = models.TextField(verbose_name='接口文档', blank=True, null=True)
    ui_link = models.TextField(verbose_name='UI设计稿', blank=True, null=True)

    # 'UI设计稿（蓝湖的）'
    ui_links = models.TextField(verbose_name='UI设计稿集', blank=True, null=True)
    # [{"name": "", "link": ""}]
    quip_folder_type = models.CharField(verbose_name="Quip文件夹类别", max_length=10, choices=QUIP_FOLDER_TYPES,
                                        default="no_need")
    quip_folder_id = models.CharField(verbose_name="Quip文件夹ID", max_length=30, blank=True, null=True)
    quip_engineer_folder_id = models.CharField(verbose_name="工程师沟通Quip文件夹ID", max_length=30, blank=True,
                                               null=True)

    def __str__(self):
        return '【{project_name}】项目链接'.format(project_name=self.project.name)

    class Meta:
        verbose_name = '项目链接'

    @property
    def quip_folder(self):
        if self.quip_folder_id:
            return "https://quip.com/" + self.quip_folder_id
        else:
            return None

    def quip_folder_data(self):
        if self.quip_folder_id:
            title = self.project.name
            return {"title": title, 'id': self.quip_folder_id, 'link': "https://quip.com/" + self.quip_folder_id}
        else:
            return None

    @property
    def quip_engineer_folder(self):
        if self.quip_engineer_folder_id:
            return "https://quip.com/" + self.quip_engineer_folder_id
        else:
            return None

    def quip_engineer_folder_data(self):
        if self.quip_engineer_folder_id:
            title = self.project.name
            return {"title": title, 'id': self.quip_engineer_folder_id,
                    'link': "https://quip.com/" + self.quip_engineer_folder_id}
        else:
            return None


# 项目工时
class ProjectWorkHourPlan(models.Model):
    ROLES = (
        ('manager', '项目经理'),
        ('product_manager', '产品'),
        ('developer', '开发'),
        ('tpm', '技术项目经理'),
        ('test', '测试'),
        ('designer', '设计'),
    )
    project = models.ForeignKey(
        Project, verbose_name='项目', related_name='project_work_hour_plans', on_delete=models.CASCADE)
    role = models.CharField(verbose_name='职位', max_length=20, choices=ROLES, null=True, blank=True)
    developer = models.ForeignKey(
        'developers.Developer', verbose_name='工程师', related_name='project_work_hour_plans', blank=True, null=True,
        on_delete=models.SET_NULL)
    user = models.ForeignKey(
        User,
        verbose_name="用户",
        related_name='project_work_hour_plans',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )
    plan_consume_days = models.FloatField(verbose_name='计划消耗', blank=True, null=True)
    elapsed_time = models.FloatField(verbose_name='已耗时', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '项目工时表'
        ordering = ['created_at']


class WorkHourRecord(models.Model):
    project_work_hour_plan = models.ForeignKey(
        ProjectWorkHourPlan, verbose_name='项目工时计划', related_name='work_hour_records', on_delete=models.CASCADE)
    statistic_start_date = models.DateField(verbose_name='统计开始日期')
    statistic_end_date = models.DateField(verbose_name='统计结束日期')
    week_consume_hours = models.FloatField(verbose_name='周消耗', blank=True, null=True)
    predict_residue_days = models.FloatField(verbose_name='预计剩余', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '项目工时记录表'
        ordering = ['created_at']


class ProjectWorkHourOperationLog(models.Model):
    TYPE_CHOICES = (
        ('create', '创建'),
        ('edit', '编辑')
    )
    project_work_hour = models.ForeignKey(ProjectWorkHourPlan, verbose_name='项目工时', related_name='operation_logs',
                                          on_delete=models.CASCADE)
    operator = models.ForeignKey(User, related_name='work_hour_operation_logs', verbose_name='操作人', null=True,
                                 blank=True, on_delete=models.SET_NULL)
    remarks = models.TextField(verbose_name='备注', null=True, blank=True)
    log_type = models.CharField(verbose_name="操作类型", max_length=15, choices=TYPE_CHOICES, default='other')
    origin_plan_consume_days = models.FloatField(verbose_name='原计划消耗', blank=True, null=True)
    new_plan_consume_days = models.FloatField(verbose_name='新计划消耗', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = '项目工时操作记录'

    def __str__(self):
        return "{}{}了工时计划".format(self.operator.username, self.get_log_type_display())

    @classmethod
    def build_log(cls, project_work_hour, operator, log_type, remarks=None, origin_plan_consume_days=None,
                  new_plan_consume_days=None, created_at=None):
        log = cls(project_work_hour=project_work_hour, operator=operator, log_type=log_type, remarks=remarks,
                  origin_plan_consume_days=origin_plan_consume_days, new_plan_consume_days=new_plan_consume_days)
        if created_at:
            log.created_at = created_at
        log.save()
        return log


# 【code explain】【工程师评分】
# 项目开发岗
class JobPosition(models.Model):
    role = models.ForeignKey('developers.Role', verbose_name='职位', on_delete=models.SET_NULL, null=True, blank=True)
    role_remarks = models.TextField(verbose_name="职位备注", blank=True, null=True)
    project = models.ForeignKey(
        Project, verbose_name='项目', related_name='job_positions', on_delete=models.CASCADE)
    developer = models.ForeignKey(
        'developers.Developer', verbose_name='工程师', related_name='job_positions', blank=True, null=True,
        on_delete=models.SET_NULL)
    pay = models.FloatField(verbose_name='报酬', blank=True, null=True)
    period = models.FloatField(verbose_name='开发周数', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    logs = GenericRelation(Log, related_query_name="job_positions")
    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')

    def __str__(self):
        return "职位:%s 工程师:%s" % (self.role.name, self.developer.name)

    @property
    def valid_contracts(self):
        # CONTRACT_STATUS = (
        #     ("uncommitted", "未提交"),
        #     ("waiting", "待签约"),
        #     ("signed", "已签约"),
        #     ("closed", "已关闭")
        # )
        return self.job_contracts.filter(status__in=['waiting', 'signed'])

    @property
    def signed_valid_contracts(self):
        # CONTRACT_STATUS = (
        #     ("uncommitted", "未提交"),
        #     ("waiting", "待签约"),
        #     ("signed", "已签约"),
        #     ("closed", "已关闭")
        # )
        return self.job_contracts.filter(status='signed').exclude(pay_status='terminated')

    @property
    def total_contract_amount(self):
        if self.valid_contracts:
            return sum(self.valid_contracts.values_list('contract_money', flat=True))
        return 0

    @property
    def total_contract_develop_days(self):
        if self.valid_contracts:
            return sum([i for i in self.valid_contracts.values_list('develop_days', flat=True) if i])
        return 0

    @property
    def no_contract_payments(self):
        return self.payments.filter(job_contract_id__isnull=True)

    @property
    def project_bugs_statistics(self):
        project_bugs = self.project.bugs.exclude(status='closed')
        all_bug_count = project_bugs.count()
        developer_bug_count = 0
        if all_bug_count:
            top_user = getattr(self.developer, 'top_user', None)
            if top_user:
                developer_bugs = project_bugs.filter(Q(assignee_id=top_user.id) | Q(fixed_by_id=top_user.id)).distinct()
                developer_bug_count = developer_bugs.count()
        data = {"developer_bug": developer_bug_count, "all_bug": all_bug_count}
        return data

    @property
    def star_rating(self):
        return getattr(self, 'job_standard_score', None)

    # 【code review】#
    '''
        职位的是否已经全部支付： 职位总金额为0   或  职位的所有合同已支付完成 且 所有无合同打款已完成
        合同可用is_fully_paid属性判断
    '''

    @property
    def is_fully_paid(self):
        if self.total_amount:
            return int(self.paid_payment_amount) == int(self.total_amount)
        return True

    @property
    def is_paid_off_valid_payments(self):
        if self.payments.filter(status__in=[0, 1]).exists():
            return False
        for obj in self.signed_valid_contracts:
            if not obj.is_fully_paid:
                return False
        return True

    # 非异常的
    @property
    def normal_payment_amount(self):
        payments = self.payments.exclude(status=3)
        if payments.exists():
            return sum(payments.values_list('amount', flat=True))
        return 0

    # 【code review】#
    '''
        职位的总金额计算方法：职位所有合同金额总和  + 职位正常的无合同打款金额总和
    '''

    @property
    def total_amount(self):
        total_amount = self.total_contract_amount + self.no_contract_amount
        return total_amount

    # 无合同打款金额
    @property
    def no_contract_amount(self):
        paid_payments = self.payments.filter(job_contract__isnull=True).exclude(status=3)
        if paid_payments.exists():
            return sum(paid_payments.values_list('amount', flat=True))
        return 0

    # 已支付的
    @property
    def paid_payment_amount(self):
        paid_payments = self.payments.filter(status=2)
        if paid_payments.exists():
            return sum(paid_payments.values_list('amount', flat=True))
        return 0

    # 进行中的
    @property
    def ongoing_payment_amount(self):
        paid_amount = self.payments.filter(status=1)
        if paid_amount.exists():
            return sum(paid_amount.values_list('amount', flat=True))
        return 0

    # 记录的
    @property
    def recorded_payment_amount(self):
        processing_payments = self.payments.filter(status=0)
        if processing_payments.exists():
            return sum(processing_payments.values_list('amount', flat=True))
        return 0

    @property
    def remaining_payment_amount(self):
        return self.total_amount - self.normal_payment_amount

    @property
    def last_paid_payment_amount(self):
        if self.last_paid_payment:
            return self.last_paid_payment.amount

    @property
    def last_paid_payment_date(self):
        if self.last_paid_payment:
            return self.last_paid_payment.completed_at

    @property
    def last_paid_payment(self):
        paid_payment = self.payments.filter(status=2).order_by('-completed_at').first()
        return paid_payment

    @property
    def payments_statistics(self):
        data = {}
        field_list = ('total_amount', 'no_contract_amount', 'paid_payment_amount', 'ongoing_payment_amount',
                      'recorded_payment_amount', 'remaining_payment_amount')
        for i in field_list:
            data[i] = getattr(self, i, 0)
        return data

    @property
    def can_be_deleted(self):
        if not self.payments.exists() and not self.job_contracts.filter(status__in=['waiting', 'signed']).exists():
            return True
        return False

    @property
    def is_have_questionnaires(self):
        grade_questionnaire = False
        job_position_role = 'developer'
        if self.role.name in '测试工程师':
            job_position_role = 'test'
        elif self.role.name in '设计师':
            job_position_role = 'designer'
        role_list = []
        if self.project.tests:
            role_list.append('test')
        if self.project.designer:
            role_list.append('designer')
        if self.project.tpm:
            role_list.append('tpm')
        if self.project.manager or self.project.product_manager:
            role_list.append('manager')
        questionnaire = Questionnaire.objects.filter(written_by__in=role_list, engineer_type=job_position_role,
                                                     status='online')
        if questionnaire:
            grade_questionnaire = True
        return grade_questionnaire

    class Meta:
        verbose_name = '开发岗位'


class JobStandardScore(models.Model):
    communication = models.FloatField(verbose_name='交流沟通', blank=True, null=True)
    efficiency = models.FloatField(verbose_name='开发速度', blank=True, null=True)
    quality = models.FloatField(verbose_name='功能质量', blank=True, null=True)
    execute = models.FloatField(verbose_name='执行', blank=True, null=True)
    score_person = models.ForeignKey(User,
                                     verbose_name="评分人",
                                     related_name='created_job_standard_scores',
                                     blank=True, null=True,
                                     on_delete=models.SET_NULL)
    job_position = models.OneToOneField(JobPosition, related_name='job_standard_score', on_delete=models.CASCADE,
                                        primary_key=True)
    evaluate = models.TextField(verbose_name='工程师评价', null=True, blank=True, max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.job_position)

    @property
    def valid_rates(self):
        rates = [i for i in [self.communication, self.efficiency, self.quality, self.execute] if 1 <= i <= 5]
        return rates

    @property
    def total_rate(self):
        rates = self.valid_rates
        return sum(rates)

    @property
    def average_score(self):
        num = len(self.valid_rates)
        if num:
            return round(self.total_rate / num, 1)

    @property
    def total(self):
        return self.total_rate

    @property
    def average(self):
        return self.average_score

    class Meta:
        verbose_name = '工程师标准评分'


class JobReferenceScore(models.Model):
    communication = models.FloatField(verbose_name='交流沟通', blank=True, null=True)
    efficiency = models.FloatField(verbose_name='开发速度', blank=True, null=True)
    quality = models.FloatField(verbose_name='功能质量', blank=True, null=True)
    execute = models.FloatField(verbose_name='执行', blank=True, null=True)
    score_person = models.ForeignKey(User,
                                     verbose_name="评分人",
                                     related_name='job_reference_scores',
                                     blank=True, null=True,
                                     on_delete=models.SET_NULL)
    job_position = models.ForeignKey(JobPosition, related_name='job_reference_scores', on_delete=models.CASCADE)
    remarks = models.TextField(verbose_name='备注', null=True, blank=True, max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.job_position)

    @property
    def valid_rates(self):
        rates = [i for i in [self.communication, self.efficiency, self.quality, self.execute] if 1 <= i <= 5]
        return rates

    @property
    def total_rate(self):
        rates = self.valid_rates
        return sum(rates)

    @property
    def average_score(self):
        num = len(self.valid_rates)
        if num:
            return round(self.total_rate / num, 1)

    @property
    def total(self):
        return self.total_rate

    @property
    def average(self):
        return self.average_score

    class Meta:
        verbose_name = '工程师参考评分'


class Questionnaire(models.Model):
    WRITTEN_BY = (
        ('manager', '项目经理'),
        ('tpm', 'TPM'),
        ('designer', '设计'),
        ('test', '测试'),
    )
    ENGINEER = (
        ('developer', '开发'),
        ('test', '测试'),
        ('designer', '设计'),
    )
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('online', '线上版本'),
        ('history', '历史版本'),
    )
    written_by = models.CharField(verbose_name='填写人', choices=WRITTEN_BY, blank=True, null=True, max_length=20)
    engineer_type = models.CharField(verbose_name='工程师类型', choices=ENGINEER, blank=True, null=True, max_length=20)
    version = models.FloatField(verbose_name='版本', max_length=10, default=1.0, blank=True, null=True)
    status = models.CharField(verbose_name='发布状态', choices=STATUS_CHOICES, max_length=20, default='draft')
    publish_at = models.DateTimeField(verbose_name='发布时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '问卷'

    @classmethod
    def get_new_version(cls, written_by, engineer_type):
        last_obj = cls.objects.filter(written_by=written_by, engineer_type=engineer_type, status='draft').order_by(
            '-version').first()
        if last_obj:
            return last_obj.version + 1
        return 1


class GradeQuestionnaire(models.Model):
    score_person = models.ForeignKey(User,
                                     verbose_name="评分人",
                                     related_name='grade_questionnaires',
                                     on_delete=models.CASCADE)
    job_position = models.ForeignKey(JobPosition, related_name='grade_questionnaires', on_delete=models.CASCADE)
    questionnaire = models.ForeignKey(Questionnaire, verbose_name='问卷', related_name='grade_questionnaires',
                                      on_delete=models.CASCADE)
    is_skip_grade = models.BooleanField(verbose_name='是否跳过评分', default=False)
    remarks = models.TextField(verbose_name='备注', null=True, blank=True, max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '工程师评分问卷'


class Question(models.Model):
    STATUS = (
        ('communication', '沟通能力'),
        ('efficiency', '工作效率'),
        ('quality', '项目质量'),
        ('execute', '执行能力'),
        ('others', '其它')
    )
    questionnaire = models.ForeignKey(Questionnaire, related_name='questions', on_delete=models.CASCADE)
    type = models.CharField(verbose_name='题目类型', max_length=20, choices=STATUS, default='others')
    title = models.CharField(verbose_name='题目', max_length=200)
    index = models.IntegerField(verbose_name='在问卷中的顺序', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '题目'

    @classmethod
    def get_new_index(cls, questionnaire):
        last_obj = cls.objects.filter(questionnaire=questionnaire).order_by('-index').first()
        if last_obj:
            return last_obj.index + 1
        return 1


class Choice(models.Model):
    STATUS = (
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
    )
    choice = models.CharField(verbose_name='选项内容', max_length=100, blank=True, null=True)
    question = models.ForeignKey(Question, related_name="choices", on_delete=models.CASCADE)
    index = models.IntegerField(default=0)
    score = models.IntegerField(verbose_name='分值', choices=STATUS, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '题目选项'

    @classmethod
    def get_new_index(cls, question):
        last_obj = cls.objects.filter(question=question).order_by('-index').first()
        if last_obj:
            return last_obj.index + 1
        return 1


class AnswerSheet(models.Model):
    """答卷"""
    grade_questionnaire = models.ForeignKey(GradeQuestionnaire, related_name='answer_sheets', on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, related_name="answer_sheets", on_delete=models.SET_NULL, blank=True,
                               null=True)  # 单选题
    question = models.ForeignKey(Question, related_name="answer_sheets", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = '评分问卷答卷'


class TechnologyCheckpoint(models.Model):
    STATUS = (
        ('pending', '未完成'),
        ('skipped', '跳过'),
        ('done', '完成'),
    )
    DEV_DOCS_CHECKPOINT = '工程师规范同步'
    project = models.ForeignKey(Project, verbose_name='项目', related_name='technology_checkpoints',
                                on_delete=models.CASCADE)
    name = models.CharField(verbose_name="检查点名称", max_length=50)
    # sprint检查点
    flag = models.CharField(verbose_name="标志", max_length=15, blank=True, null=True)
    principal = models.ForeignKey(User, verbose_name="负责人", related_name='technology_checkpoints', blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL)
    status = models.CharField(verbose_name="状态", choices=STATUS, max_length=15, default='pending')
    expected_at = models.DateField(verbose_name="预计完成时间", blank=True, null=True)

    quip_document_id = models.CharField(verbose_name="Quip文档ID", max_length=30, blank=True, null=True)
    quip_document_title = models.CharField(verbose_name="Quip文档标题", max_length=30, blank=True, null=True)

    logs = GenericRelation(Log, related_query_name="technology_checkpoints")
    comments = GenericRelation(Comment, related_query_name="technology_checkpoints")
    done_at = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    quip_document_ids = models.TextField(verbose_name="Quip文档集", blank=True, null=True)

    project_stage = models.ForeignKey('projects.ProjectStage', verbose_name="项目阶段",
                                      related_name='technology_checkpoints',
                                      blank=True, null=True,
                                      on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.status != 'pending':
            if self.done_at is None:
                self.done_at = timezone.now()
        else:
            self.done_at = None

        super(TechnologyCheckpoint, self).save(*args, **kwargs)

    @classmethod
    def pending_checkpoints(cls):
        return cls.objects.filter(status='pending')

    def quip_document(self):
        if self.quip_document_id:
            return "https://quip.com/" + self.quip_document_id
        else:
            return None

    def quip_document_data(self):
        if self.quip_document_id:
            link = "https://quip.com/" + self.quip_document_id
            if not self.quip_document_title:
                document_title = self.get_quip_document_title()
                if document_title:
                    self.quip_document_title = document_title
                    self.save()
            title = self.quip_document_title or link
            return {"title": title, "link": link, 'id': self.quip_document_id}

    def get_quip_document_title(self):
        project_id = self.project.id
        quip_projects_tpm_docs = cache.get('quip_projects_tpm_docs', {})
        tpm_docs = quip_projects_tpm_docs.get(project_id, {})
        docs = tpm_docs.get('docs', [])
        quip_document_title = None
        for doc in docs:
            doc_id = doc['id']
            if doc_id == self.quip_document_id:
                quip_document_title = doc['title']
                break
        return quip_document_title

    @property
    def quip_documents(self):
        if self.quip_document_ids:
            documents = []
            quip_document_ids = json.loads(self.quip_document_ids, encoding='utf-8')
            project_id = self.project.id
            quip_projects_tpm_docs = cache.get('quip_projects_tpm_docs', {})
            tpm_docs = quip_projects_tpm_docs.get(project_id, {})
            docs = tpm_docs.get('docs', [])
            from farmbase.tasks import crawl_project_tpm_folder_docs
            crawl_project_tpm_folder_docs.delay(project_id, True)
            docs_dict = {}
            for doc in docs:
                doc_id = doc['id']
                docs_dict[doc_id] = doc
            for doc_id in quip_document_ids:
                if doc_id in docs_dict:
                    doc = docs_dict[doc_id]
                    doc_data = doc
                    if not doc_data.get('link', None):
                        doc_data['link'] = "https://quip.com/" + doc_id
                else:
                    doc_data = {"id": doc_id, "title": "Quip文档", "link": "https://quip.com/" + doc_id}
                documents.append(doc_data)

            if documents:
                return documents

    class Meta:
        verbose_name = '项目技术检查点'
        ordering = ['expected_at']


class CheckPoint(models.Model):
    STATUS = (
        (0, '未完成'),
        (1, '正常完成'),
        (2, '存在风险'),
        (3, '合理延期'),
        (4, '出现问题'),
        (5, '该项目或该阶段无此项'),
        (6, '项目终止'),
    )
    project = models.ForeignKey(
        Project, verbose_name='项目', related_name='checkpoints', on_delete=models.CASCADE)
    name = models.CharField(verbose_name="检查点名称", max_length=50)
    codename = models.CharField(verbose_name="检查点名称", max_length=50, blank=True, null=True)
    position = models.IntegerField(verbose_name='位置', default=-1)
    principal = models.ForeignKey(User, verbose_name="负责人", related_name='checkpoints', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    post = models.ForeignKey(Group, verbose_name="负责职位", related_name='checkpoints', blank=True, null=True,
                             on_delete=models.SET_NULL)
    expected_at = models.DateField(verbose_name="预计完成时间")
    done_at = models.DateField(verbose_name='实际完成时间', blank=True, null=True)
    logs = GenericRelation(Log, related_query_name="checkpoints")
    comments = GenericRelation(Comment, related_query_name="checkpoints")
    status = models.IntegerField(
        verbose_name="状态", choices=STATUS, default=0)
    is_active = models.BooleanField(default=True)
    is_confirmed = models.BooleanField(verbose_name='确认', default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # 如果完成日期为None，状态从已完成设置为未完成
        if self.status == 1 and self.done_at is None:
            self.status = 0
        # 如果设置完成日期，状态从未完成设置为已完成
        if self.done_at and self.status == 0:
            self.status = 1
        super(CheckPoint, self).save(*args, **kwargs)

    class Meta:
        verbose_name = '项目检查点'
        ordering = ['position']


class ProjectStage(models.Model):
    STAGE_CHOICES = (
        ('prd', '原型'),
        ('design', '设计'),
        ('development', '开发'),
        ('test', '测试'),
        ('acceptance', '验收')
    )

    project = models.ForeignKey(Project, verbose_name='项目', related_name='project_stages', on_delete=models.CASCADE)
    stage_type = models.CharField(verbose_name='阶段类型', choices=STAGE_CHOICES, max_length=20)
    name = models.CharField(verbose_name='阶段名称', max_length=50)
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(verbose_name="确认日期")
    index = models.IntegerField(verbose_name='位置', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="项目日程表修改时间", auto_now=True)
    gantt_chart_built = models.BooleanField(verbose_name="已初始化甘特图任务", default=False)

    def __str__(self):
        return "{}阶段:{}".format(self.get_stage_type_display(), self.name)

    class Meta:
        verbose_name = '项目阶段'

    @property
    def stage_type_display(self):
        return self.get_stage_type_display()

    @property
    def is_previous_stage(self):
        today = timezone.now().date()
        if self.end_date < today:
            return True
        return False

    @property
    def is_current_stage(self):
        today = timezone.now().date()
        if self.start_date <= today <= self.end_date:
            return True
        return False

    @property
    def is_next_stage(self):
        today = timezone.now().date()
        if self.start_date > today:
            return True
        return False


class DeliveryDocumentType(models.Model):
    INIT_DATA = (
        {'name': '交付文档', 'suffix': 'zip', 'number': 0},

        {'name': '交付文档说明', 'suffix': 'pdf', 'number': 1},
        {'name': '源代码', 'suffix': 'zip', 'number': 2},
        {'name': '产品需求文档', 'suffix': 'pdf', 'number': 3},
        {'name': '产品原型', 'suffix': 'zip', 'number': 4},
        {'name': '产品原型源文件', 'suffix': 'zip', 'number': 5},
        {'name': 'UI设计效果图', 'suffix': 'zip', 'number': 6},
        {'name': 'UI设计图源文件', 'suffix': 'zip', 'number': 7},
        {'name': '项目操作说明', 'suffix': 'pdf', 'number': 8},
        {'name': '部署文档', 'suffix': 'pdf', 'number': 9},
        {'name': '数据库设计文档', 'suffix': 'pdf', 'number': 10},
        {'name': '接口文档', 'suffix': 'pdf', 'number': 11},
        {'name': '相关账号信息', 'suffix': 'pdf', 'number': 12},

        {'name': '其他文档', 'suffix': '', 'number': 13},
    )

    DELIVERY_DOCUMENT_NUMBER = 0
    UNCLASSIFIED_DOCUMENT_NUMBER = 13
    DELIVERY_DOCUMENT_README_NUMBER = 1

    name = models.CharField(max_length=50, verbose_name='文件类别名', unique=True)
    suffix = models.CharField(max_length=20, verbose_name='后缀', blank=True, null=True)
    number = models.IntegerField(verbose_name='文件类别编号')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '交付文件类别'
        ordering = ['number']


class DeliveryDocument(models.Model):

    def generate_filename(self, filename):
        if self.document_type.suffix:
            filename = "《{project_name}》{document_type}.{suffix}".format(project_name=self.project.name,
                                                                         document_type=self.document_type.name,
                                                                         suffix=self.document_type.suffix)
        url = "projects/{}/{}-{}".format(self.project.id, self.uid, filename)
        return url

    project = models.ForeignKey(Project, verbose_name="项目", related_name='delivery_documents', on_delete=models.CASCADE)
    document_type = models.ForeignKey(DeliveryDocumentType, verbose_name="交付文件类别", related_name='documents',
                                      on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to=generate_filename)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    is_deleted = models.BooleanField(default=False, verbose_name="删除状态")
    filename = models.CharField(verbose_name="文件名称", max_length=100, blank=True, null=True)
    uid = models.CharField(max_length=25, verbose_name="标识码")
    cipher = models.CharField(max_length=6, blank=True, null=True, verbose_name="提取码")
    is_behind = models.BooleanField(default=False)

    def __str__(self):
        return "《{project_name}》{document_type_name}".format(project_name=self.project.name,
                                                             document_type_name=self.document_type.name)

    class Meta:
        verbose_name = '交付文件'
        ordering = ['document_type__number']


class ProjectContract(models.Model):
    def generate_filename(self, filename):
        url = "projects/{}/contract/{}/{}".format(self.project.id, str(uuid.uuid4())[:8], filename)
        return url

    project = models.ForeignKey(Project, verbose_name='项目', related_name='contracts', on_delete=models.CASCADE)
    name = models.CharField(max_length=50, verbose_name='合同名', null=True, blank=True)
    number = models.CharField(max_length=50, verbose_name='合同号', null=True, blank=True)
    filing_date = models.DateField(verbose_name='入档日期', null=True, blank=True)
    file = models.FileField(upload_to=generate_filename, null=True, blank=True)
    filename = models.CharField(max_length=50, verbose_name='文件名', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    def __str__(self):
        if self.name:
            return self.name
        else:
            return self.project.name + '合同'

    class Meta:
        verbose_name = '项目合同'
        ordering = ['-created_at']


class ProjectPrototype(models.Model):
    def generate_filename(self, filename):
        url = "projects/{}/prototypes/{}.zip".format(self.project.id, self.uid)
        return url

    PUBLIC_STATUS = (
        ("none", "非公开"),
        ("client_public", "客户可见"),
        ("developer_public", "工程师可见"),
        ("public", "公开可见"),
    )
    public_status = models.CharField(verbose_name="公开状态", max_length=50, choices=PUBLIC_STATUS, default='none')  # 新字段
    is_public = models.BooleanField(default=False, verbose_name="公开状态")  # 老字段

    project = models.ForeignKey(Project, verbose_name='项目', related_name='prototypes', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    version = models.CharField(max_length=10, default='1.0')
    uid = models.CharField(max_length=25, verbose_name="标识码")
    cipher = models.CharField(max_length=6, blank=True, null=True, verbose_name="提取码")
    file = models.FileField(upload_to=generate_filename)
    filename = models.CharField(verbose_name="文件名称", max_length=100, blank=True, null=True)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_prototypes', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    is_deleted = models.BooleanField(default=False, verbose_name="删除状态")

    index_path = models.CharField(verbose_name="index_path", max_length=200, blank=True, null=True)
    browsing_histories = GenericRelation(BrowsingHistory, related_query_name="project_prototypes")

    oss_url = models.CharField(verbose_name="oss访问地址", max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = '项目原型'
        unique_together = (('project', 'title', 'version'),)
        ordering = ['-created_at', 'title']

    @property
    def last_browsing_history(self):
        return self.browsing_histories.order_by('-created_at').first()

    @classmethod
    def active_prototypes(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(is_deleted=False)

    @classmethod
    def public_prototypes(cls, queryset=None):
        queryset = cls.active_prototypes() if queryset is None else queryset
        return queryset.filter(public_status='public')

    @classmethod
    def client_public_prototypes(cls, queryset=None):
        queryset = cls.active_prototypes() if queryset is None else queryset
        return queryset.filter(public_status__in=['public', 'client_public'])

    @classmethod
    def developer_public_prototypes(cls, queryset=None):
        queryset = cls.active_prototypes() if queryset is None else queryset
        return queryset.filter(public_status__in=['public', 'developer_public'])

    @property
    def public_status_display(self):
        return self.get_public_status_display()

    def prototype_zip_path(self):
        return settings.PROTOTYPE_ROOT + self.uid + '.zip'

    def prototype_unzip_dir(self):
        return settings.PROTOTYPE_ROOT + self.uid + '/'

    def prototype_dir(self):
        return settings.PROTOTYPE_ROOT + encrypt_string(self.uid)[:16] + '/'

    @property
    def access_token(self):
        return encrypt_string(self.cipher + self.uid)[:12]

    @property
    def prototype_url(self):
        if self.oss_url:
            return self.oss_url
        elif not self.is_deleted:
            from projects.tasks import unzip_prototype_and_upload_to_oss
            unzip_prototype_and_upload_to_oss.delay(self.id)
        return None

    def __str__(self):
        return self.title + ' 版本' + self.version


class PrototypeCommentPoint(models.Model):
    prototype = models.ForeignKey(ProjectPrototype, verbose_name='原型', related_name='comment_points',
                                  on_delete=models.CASCADE)
    url_hash = models.CharField(max_length=150, verbose_name="锚链接")
    page_name = models.CharField(max_length=150, verbose_name="页面名字", blank=True, null=True)
    panel_name = models.CharField(max_length=25, verbose_name="所属板块", blank=True, null=True)
    position_left = models.IntegerField(verbose_name="相对所属板块左上角left值")
    position_top = models.IntegerField(verbose_name="相对所属板块左上角top值")
    comments = GenericRelation(Comment, related_query_name="prototype_comment_points")

    creator = models.ForeignKey('auth_top.TopUser', verbose_name='创建人', related_name='prototype_comment_points',
                                null=True,
                                blank=True,
                                on_delete=models.SET_NULL)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    class Meta:
        verbose_name = '项目评论点'
        ordering = ['prototype', 'url_hash']


class ProjectGanttChart(models.Model):
    TEMPLATE_INIT_STATUS = (
        ('uninitialized', '未初始化'),
        ('skipped', '跳过'),
        ('initialized', '已初始化')
    )
    project = models.OneToOneField(Project, related_name='gantt_chart', on_delete=models.CASCADE)
    logs = GenericRelation(Log, related_query_name="project_gantt")
    uid = models.CharField(max_length=25, blank=True, null=True)
    template_init_status = models.CharField(verbose_name="模板导入状态", max_length=20, choices=TEMPLATE_INIT_STATUS,
                                            default='uninitialized')

    class Meta:
        verbose_name = '项目甘特图'

    def __str__(self):
        return self.project.name + '甘特图'

    def save(self, *args, **kwargs):
        if not self.uid:
            self.uid = gen_uuid()
        super(ProjectGanttChart, self).save(*args, **kwargs)

    @property
    def template_init_status_display(self):
        return self.get_template_init_status_display()

    @property
    def need_update_template(self):
        today = timezone.now().date()
        if not self.project.done_at and not self.project.end_date <= today:
            project_set = cache.get('need_update_gantt_template_projects', set())
            if self.project_id in project_set:
                return True
        return False


class GanttRole(models.Model):
    TYPES = (
        # 项目的公司内部角色
        ('manager', '项目经理'),
        ('product_manager', '产品'),
        ('mentor', '导师'),
        ('tpm', '技术项目经理'),
        ('test', '测试'),
        ('cs', '客户成功'),
        ('designer', '设计'),
        ('bd', 'BD'),
        # 项目的开发工程师
        ('developer', '开发工程师'),
        ('iOS工程师', 'iOS工程师'),
        ('Android工程师', 'Android工程师'),
        ('设计师', '设计师'),
        ('后端工程师', '后端工程师'),
        ('测试工程师', '测试工程师'),
        ('前端工程师', '前端工程师'),
        ('小程序工程师', '小程序工程师'),
        ('other', '其他'),
    )
    DEVELOPER_CHOICES = (
        'developer', 'iOS工程师', 'Android工程师', '设计师', '后端工程师', '测试工程师', '前端工程师', '小程序工程师'
    )
    USER_CHOICES = (
        'manager', 'product_manager', 'mentor', 'tpm', 'test', 'cs', 'designer'
    )
    role_type = models.CharField(verbose_name="角色类型", max_length=30, blank=True, null=True)
    gantt_chart = models.ForeignKey(ProjectGanttChart, verbose_name="项目甘特图", related_name='roles',
                                    on_delete=models.CASCADE)
    name = models.CharField(max_length=30, verbose_name="角色名称")
    user = models.ForeignKey(
        User,
        verbose_name="用户",
        related_name='gantt_roles',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )

    developer = models.ForeignKey('developers.Developer', verbose_name='工程师', related_name='gantt_roles', blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL)

    class Meta:
        verbose_name = '项目甘特图角色'
        ordering = ['id']

    def save(self, *args, **kwargs):
        if self.developer and self.role_type in self.DEVELOPER_CHOICES and self.user:
            self.user = None
        elif self.user and self.role_type in self.USER_CHOICES and self.developer:
            self.developer = None
        super(GanttRole, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def project(self):
        return self.gantt_chart.project

    def rebuild_role_type_user_developer(self):
        if self.developer and self.role_type in self.DEVELOPER_CHOICES and self.user:
            self.user = None
        elif self.user and self.role_type in self.USER_CHOICES and self.developer:
            self.developer = None
        self.save()


class GanttTaskCatalogue(models.Model):
    gantt_chart = models.ForeignKey(ProjectGanttChart, verbose_name="项目甘特图", related_name='task_catalogues',
                                    on_delete=models.CASCADE)
    name = models.CharField(max_length=30, verbose_name="模块分类名称")
    auto_created = models.BooleanField(verbose_name='是模板自动创建', default=False)
    number = models.IntegerField(verbose_name='模块编号', default=1)
    project_stage = models.ForeignKey(ProjectStage, verbose_name="项目阶段", related_name='gantt_chart_catalogues',
                                      on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = '项目甘特图模块分类'
        ordering = ['number']

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        super(GanttTaskCatalogue, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def project(self):
        return self.gantt_chart.project


class GanttTaskTopic(models.Model):
    POSITION_CHOICES = (
        ('start_time', '起始日期'),
        ('finish_time', '完成日期'),
    )
    DEV_DONE_TYPES = (
        ('self', '独立勾选'),
        ('auto', '自动勾选'),
    )
    gantt_chart = models.ForeignKey(ProjectGanttChart, verbose_name="项目甘特图", related_name='task_topics',
                                    on_delete=models.CASCADE)
    catalogue = models.ForeignKey(GanttTaskCatalogue, verbose_name='模块分类', related_name='task_topics',
                                  on_delete=models.CASCADE)
    role = models.ForeignKey(GanttRole, verbose_name="角色", related_name='task_topics',
                             on_delete=models.CASCADE)
    name = models.CharField(max_length=30, verbose_name="模块任务名称")
    auto_created = models.BooleanField(verbose_name='是模板自动创建', default=False)
    number = models.IntegerField(verbose_name='模块任务编号', default=1)
    start_time = models.DateField(verbose_name="任务开始时间")
    only_workday = models.BooleanField(verbose_name='仅计算工作日', default=True)
    expected_finish_time = models.DateField(verbose_name="任务预计完成时间", blank=True,
                                            null=True)
    timedelta_days = models.FloatField(verbose_name="任务持续天数")
    half_day_position = models.CharField(verbose_name='半天所在位置', max_length=20, choices=POSITION_CHOICES, blank=True,
                                         null=True)

    is_dev_done = models.BooleanField(verbose_name='工程师已完成', default=False)
    dev_done_at = models.DateTimeField(verbose_name='工程师完成时间', blank=True, null=True)
    dev_done_type = models.CharField(verbose_name='开发确认完成类型', max_length=20, choices=DEV_DONE_TYPES, blank=True,
                                     null=True)

    is_done = models.BooleanField(verbose_name='已完成', default=False)
    done_at = models.DateTimeField(verbose_name='完成时间', blank=True, null=True)

    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True, blank=True, null=True)
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = '项目甘特图模块任务'
        ordering = ['number']

    def __str__(self):
        return self.name

    @property
    def project(self):
        return self.gantt_chart.project

    @property
    def role_type(self):
        return self.role.role_type

    def save(self, *args, **kwargs):
        self.is_done = True if self.done_at else False
        self.is_dev_done = True if self.dev_done_at else False
        self.name = self.name.strip()
        self.start_time = self.get_real_start_time()
        self.expected_finish_time = self.get_expected_finish_time()
        self.half_day_position = self.build_half_day_position()
        super(GanttTaskTopic, self).save(*args, **kwargs)

    def build_half_day_position(self):
        # 如果包含半天
        if self.timedelta_days and math.ceil(self.timedelta_days) != math.floor(
                self.timedelta_days):
            self.timedelta_days = math.floor(self.timedelta_days) + 0.5
            # 如果大于一天且包含半天 默认为半天包含在完成日期
            if self.timedelta_days > 1 and not self.half_day_position:
                self.half_day_position = 'finish_time'
            # 如果为半天 默认当天第一个半天为上半天
            if 1 > self.timedelta_days > 0:
                if self.role.task_topics.filter(expected_finish_time=self.expected_finish_time,
                                                half_day_position='finish_time').exists():
                    self.half_day_position = 'start_time'
                else:
                    self.half_day_position = 'finish_time'
        else:
            self.half_day_position = None
        return self.half_day_position

    def get_real_start_time(self):
        # 如果是工作日
        if self.only_workday:
            self.start_time = next_workday(self.start_time, include_start_date=True)
        return self.start_time

    def get_expected_finish_time(self):
        if self.start_time and self.timedelta_days:
            only_workday = self.only_workday
            timedelta_days = math.ceil(self.timedelta_days)
            # 包含当天的话  -1天
            if (only_workday and is_workday(self.start_time)) or not only_workday:
                timedelta_days -= 1
            self.expected_finish_time = get_date_by_timedelta_days(self.start_time, timedelta_days,
                                                                   only_workday=only_workday)
            return self.expected_finish_time

    @property
    def catalogue_name(self):
        return self.catalogue.name


class JobPositionNeed(models.Model):
    STATUS = (
        (0, '未完成'),
        (1, '已确认工程师'),
        (2, '已取消'),
    )
    role = models.ForeignKey('developers.Role', verbose_name='职位', on_delete=models.CASCADE)
    role_remarks = models.TextField(verbose_name="职位备注", blank=True, null=True)
    project = models.ForeignKey(Project, verbose_name='项目', related_name='position_needs', on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_position_needs',
                                  on_delete=models.CASCADE)
    principal = models.ForeignKey(User, verbose_name='负责人', related_name='responsible_position_needs', blank=True,
                                  null=True,
                                  on_delete=models.SET_NULL)
    status = models.IntegerField(verbose_name="状态", choices=STATUS, default=0)

    remarks = models.TextField(verbose_name='岗位描述', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    expected_date = models.DateField(verbose_name="预计确认日期")
    confirmed_at = models.DateTimeField(verbose_name='确认时间', blank=True, null=True)
    canceled_at = models.DateTimeField(verbose_name='取消时间', blank=True, null=True)
    period = models.FloatField(verbose_name='开发周数', blank=True, null=True)
    done_at = models.DateField(verbose_name="完成时间", blank=True, null=True)
    logs = GenericRelation(Log, related_query_name="position_needs")
    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')

    class Meta:
        verbose_name = '开发岗位需求'
        ordering = ['-created_at']

    def __str__(self):
        return "%s %s" % (self.project.name, self.role.name)

    @classmethod
    def undone_position_needs(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(done_at__isnull=True)

    # 所有候选人是否已经反馈联系; 已确认的工程师会后续合作不需要专门反馈；进行过初步联系的人未确认的、一定要进行反馈联系
    @property
    def need_feedback(self):
        if self.candidates.exclude(status=1).filter(initial_contact_at__isnull=False, contact_at__isnull=True).exists():
            return True
        return False

    @property
    def need_new_candidate(self):
        if self.status == 0 and not self.candidates.filter(status__lte=1).exists():
            return True
        return False

    @property
    def has_unhandled_candidate(self):
        return self.candidates.filter(status=0).exists()

    def is_today(self):
        return timezone.now().date() == self.expected_date

    def is_past(self):
        return timezone.now().date() > self.expected_date

    def remaining_days(self):
        return (self.expected_date - timezone.now().date()).days

    def candidates_auto_tasks(self, is_done=None):
        auto_tasks = Task.objects.none()
        for candidate in self.candidates.all():
            candidate_auto_tasks = candidate.auto_tasks
            if is_done is not None:
                candidate_auto_tasks = candidate_auto_tasks.filter(is_done=is_done)
            auto_tasks = auto_tasks | candidate_auto_tasks
        return auto_tasks

    def save(self, *args, **kwargs):
        if self.status != 0 and not self.need_feedback:
            if not self.done_at:
                self.done_at = timezone.now()
        else:
            self.done_at = None

        super(JobPositionNeed, self).save(*args, **kwargs)


class JobPositionCandidate(models.Model):
    STATUS = (
        (0, '待确认'),
        (1, '已确认'),
        (2, '已拒绝'),
        (3, '未选择'),
    )
    position_need = models.ForeignKey(JobPositionNeed, verbose_name='开发岗位需求', related_name='candidates',
                                      on_delete=models.CASCADE)
    developer = models.ForeignKey('developers.Developer', verbose_name='工程师', related_name='position_candidates',
                                  blank=True, null=True, on_delete=models.SET_NULL)
    status = models.IntegerField(verbose_name="状态", choices=STATUS, default=0)
    remarks = models.TextField(verbose_name='备注', blank=True, null=True)

    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_position_candidates',
                                  on_delete=models.CASCADE)

    handler = models.ForeignKey(User, verbose_name='处理人', related_name='handled_position_candidates',
                                on_delete=models.SET_NULL, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='分配时间')
    initial_contact_at = models.DateTimeField(verbose_name='初次联系时间', blank=True, null=True)
    contact_at = models.DateTimeField(verbose_name='反馈时间', blank=True, null=True)
    confirmed_at = models.DateTimeField(verbose_name='确认时间', blank=True, null=True)

    refuse_reason = models.TextField(verbose_name='拒绝理由', blank=True, null=True)
    refuse_remarks = models.TextField(verbose_name='拒绝备注', blank=True, null=True)
    is_first_collaboration = models.NullBooleanField(
        verbose_name='第一次合作', blank=True, null=True)
    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')

    class Meta:
        verbose_name = '开发岗位候选人'
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        if self.is_first_collaboration == None:
            is_first_collaboration = True
            if self.developer.job_positions.exists():
                is_first_collaboration = False
            self.is_first_collaboration = is_first_collaboration
        super(JobPositionCandidate, self).save(*args, **kwargs)

    def __str__(self):
        return "【{project}】{role}:{developer} ".format(project=self.position_need.project.name,
                                                       role=self.position_need.role.name, developer=self.developer.name)


class ClientCalendar(models.Model):
    STAGES = ('start', 'requirement_confirmation', 'ui_design', 'development', 'test', 'acceptance', 'holiday')
    project = models.ForeignKey(Project, verbose_name='项目', related_name='calendars', on_delete=models.CASCADE)
    title = models.CharField(max_length=100, blank=True, null=True)
    uid = models.CharField(max_length=25, unique=True)
    period_days = models.IntegerField(verbose_name="周期天数", default=0)
    start_time = models.DateField(verbose_name="启动时间")
    delivery_time = models.DateField(verbose_name="交付时间")
    start = models.TextField(verbose_name="项目启动", blank=True, null=True)
    requirement_confirmation = models.TextField(verbose_name="需求确认", blank=True, null=True)
    ui_design = models.TextField(verbose_name="UI设计", blank=True, null=True)
    development = models.TextField(verbose_name="项目开发", blank=True, null=True)
    test = models.TextField(verbose_name="项目测试", blank=True, null=True)
    acceptance = models.TextField(verbose_name="交付审核", blank=True, null=True)
    holiday = models.TextField(verbose_name="节假日", blank=True, null=True)

    creator = models.ForeignKey(User, verbose_name='创建人', related_name='created_project_calendars',
                                on_delete=models.SET_NULL, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    is_public = models.BooleanField(default=False, verbose_name="公开状态")

    class Meta:
        verbose_name = '项目客户日程表'

    def __str__(self):
        return "《{}项目》客户日程表".format(self.project)

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.project.name + '日程表'
        self.period_days = self.build_period_days()
        super(ClientCalendar, self).save(*args, **kwargs)

    def build_period_days(self):
        dates = set()
        stages = self.STAGES
        for stage_name in stages:
            if stage_name == 'holiday':
                continue
            stage = getattr(self, stage_name)
            if stage:
                stage_dates = set(ast.literal_eval(stage))
                dates = dates | stage_dates
        return len(dates)

    @property
    def remaining_days(self):
        num = 0
        stages = self.STAGES
        today_str = timezone.now().date().strftime(settings.DATE_FORMAT)
        for stage_name in stages:
            if stage_name == 'holiday':
                continue
            stage = getattr(self, stage_name)
            if stage:
                stage_dates = set(ast.literal_eval(stage))
                for date_str in stage_dates:
                    if date_str > today_str:
                        num += 1

        return num

    def get_title(self):
        if not self.title:
            self.title = self.project.name + '日程表'
            self.save()
        return self.title
