import time
import random
import uuid
import binascii
import os
from datetime import timedelta
import math
from django.contrib.contenttypes.fields import GenericRelation
from django.core.cache import cache
from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from pypinyin import lazy_pinyin

from comments.models import Comment
from projects.models import JobPosition, Project, GanttTaskTopic, JobStandardScore
from finance.models import JobPayment
from logs.models import BrowsingHistory


class TaggedDevelopmentLanguage(TaggedItemBase):
    content_object = models.ForeignKey('Developer', on_delete=models.CASCADE)


class TaggedFrameworks(TaggedItemBase):
    content_object = models.ForeignKey('Developer', on_delete=models.CASCADE)


class Role(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '职位'


# Create your models here.
class Developer(models.Model):
    AVATAR_COLORS = (
        ('#212736', 'Black'),
        ('#2161FD', 'Blue'),
        ('#36B37E', 'Green'),
        ('#F5121D', 'Red'),
        ('#FE802F', 'Orange'),
        ('#9254DE', 'Purple'),
        ('#EB2F96', 'Magenta'),
    )

    def generate_filename(self, filename):
        url = "developers-{}-{}-{}".format(self.name, str(uuid.uuid4())[:6], filename)
        return url

    GENDER_CHOICES = (
        ('0', '女'),
        ('1', '男'),
        ('2', '未填写'),
    )
    STATUS_DICT = {
        "abandoned": '0',
        "can_take_new_job": '1',
        "cannot_take_new_job": '2',
    }
    STATUS_CHOICES = (
        ('0', '弃用'),
        ('1', '可以接单'),
        ('2', '不可接单'),
    )
    FULLTIME_CHOICES = (
        ('A', '未填写'),
        ('B', '全职'),
        ('C', '半全职'),
        ('D', '兼职')
    )
    # 个人信息
    name = models.CharField(max_length=50, verbose_name='名称')
    name_pinyin = models.CharField(max_length=100, verbose_name='名称拼音', null=True, blank=True)

    phone = models.CharField(max_length=20, verbose_name='手机号', blank=True, null=True)
    avatar = models.ImageField(upload_to=generate_filename, verbose_name='头像', null=True, blank=True)
    avatar_color = models.CharField(verbose_name='头像颜色', choices=AVATAR_COLORS, max_length=10, blank=True, null=True)
    gender = models.CharField(verbose_name='性别', max_length=2, choices=GENDER_CHOICES, default='2')
    location = models.CharField(max_length=100, verbose_name='所在地区', null=True, blank=True)
    address = models.CharField(max_length=100, verbose_name='地址', null=True, blank=True)
    description = models.TextField(verbose_name='简介', blank=True, null=True)
    id_card_number = models.CharField(max_length=30, verbose_name='身份证号码', blank=True, null=True)
    front_side_of_id_card = models.ImageField(upload_to=generate_filename, verbose_name='身份证正面照', null=True,
                                              blank=True)
    back_side_of_id_card = models.ImageField(upload_to=generate_filename, verbose_name='身份证反面照', null=True,
                                             blank=True)
    esign_account_id = models.CharField(verbose_name='工程师签署账户id', max_length=100, null=True, blank=True)

    # 老字段：打款信息
    payment_info = models.TextField(verbose_name='打款信息', blank=True, null=True)
    # 收款人信息
    payee_name = models.CharField(max_length=50, verbose_name='收款人户名', blank=True, null=True)
    payee_id_card_number = models.CharField(max_length=30, verbose_name='收款人身份证号码', blank=True, null=True)
    payee_phone = models.CharField(max_length=20, verbose_name='收款人手机号', blank=True, null=True)
    payee_opening_bank = models.TextField(verbose_name='收款人开户行', blank=True, null=True)
    payee_account = models.CharField(verbose_name='收款人收款账号', null=True, blank=True, max_length=50)

    # 职位信息
    status = models.CharField(verbose_name='状态', max_length=2, choices=STATUS_CHOICES, default='1')
    is_active = models.BooleanField(verbose_name='有效', default=True)
    roles = models.ManyToManyField(Role, verbose_name='职位', related_name='developers')
    fulltime_status = models.CharField(verbose_name='工作时间', max_length=2, choices=FULLTIME_CHOICES, default='A')
    development_languages = TaggableManager(verbose_name="开发语言", related_name="development_language_developer",
                                            through=TaggedDevelopmentLanguage)
    frameworks = TaggableManager(verbose_name="开发框架工具", related_name="framework_developer", through=TaggedFrameworks)
    # 联系方式
    email = models.EmailField(blank=True, null=True)
    qq = models.CharField(max_length=15, verbose_name='QQ', blank=True, null=True)
    wechat = models.CharField(max_length=20, verbose_name='微信', blank=True, null=True)
    git = models.CharField(max_length=30, verbose_name='Git', blank=True, null=True)
    quip = models.CharField(max_length=30, verbose_name='Quip', blank=True, null=True)
    fadada = models.CharField(max_length=30, verbose_name='法大大', blank=True, null=True)

    gitlab_user_id = models.IntegerField(verbose_name='GitLab账户', blank=True, null=True)
    feishu_user_id = models.CharField(verbose_name="飞书ID", max_length=30, blank=True, null=True, unique=True)

    # 评论
    comments = GenericRelation(Comment, related_query_name="developers")

    abandoned_reason = models.TextField(verbose_name='弃用理由', blank=True, null=True)
    refuse_new_job_reason = models.TextField(verbose_name='不可接单理由', blank=True, null=True)

    abandoned_at = models.DateTimeField(verbose_name='弃用时间', blank=True, null=True)

    expected_work_at = models.DateField(verbose_name='预计可接单时间', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(verbose_name='最近登录时间', blank=True, null=True)
    is_real_name_auth = models.BooleanField(verbose_name='是否已经实名认证', default=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.status != '0':
            self.abandoned_reason = None
            self.abandoned_at = None
            self.is_active = True
        if self.status == '0':
            self.abandoned_at = self.abandoned_at or timezone.now()
            self.is_active = False
        if self.status != '2':
            self.expected_work_at = None
            self.refuse_new_job_reason = None
        if not self.avatar_color:
            self.avatar_color = self.get_random_avatar_color()
        if not self.name_pinyin:
            self.name_pinyin = lazy_pinyin(self.name)
        super(Developer, self).save(*args, **kwargs)

    def get_random_avatar_color(self):
        randint = random.randint(0, len(self.AVATAR_COLORS) - 1)
        return self.AVATAR_COLORS[randint][0]

    def get_top_user(self):
        from auth_top.models import TopUser
        top_user, created = TopUser.get_or_create(developer=self)
        return top_user

    @property
    def status_display(self):
        return self.get_status_display()

    @classmethod
    def active_developers(cls):
        return cls.objects.exclude(status='0').all()

    @property
    def employability(self):
        '''
        工程师可分配性
        默认可分配性3
        没有进行中项目 + 5
        只有交付项目 + 4
        没有进行中分配记录 + 2
        :return:
        '''
        if self.status == '0':
            employability_level = -1
        elif self.status == '2':
            employability_level = 0
        else:
            employability_level = 3
            active_projects = self.active_projects()
            acceptance_projects = [project for project in active_projects if
                                   project.current_stages.filter(stage_type="acceptance").exists()]
            projects_len = len(active_projects)
            if not self.position_candidates.filter(status=0).exists():
                employability_level += 2
            if not projects_len:
                employability_level += 5
            elif projects_len == len(acceptance_projects):
                employability_level += 4
        return employability_level

    def build_star_rating(self, project=None):
        avg_rate = None
        jobs = self.job_positions.all()
        if project:
            jobs = jobs.filter(project_id=project.id)
        job_ids = jobs.values_list('id', flat=True)
        reviews = JobStandardScore.objects.filter(job_position_id__in=job_ids)
        if reviews.exists():
            communication = list(reviews.aggregate(Avg('communication')).values())[0]
            efficiency = list(reviews.aggregate(Avg('efficiency')).values())[0]
            quality = list(reviews.aggregate(Avg('quality')).values())[0]
            execute = list(reviews.aggregate(Avg('execute')).values())[0]
            avg_rate = {
                'communication': round(communication, 2) if communication else 0,
                'efficiency': round(efficiency, 2) if efficiency else 0,
                'quality': round(quality, 2) if quality else 0,
                'execute': round(execute, 2) if execute else 0
            }
            rate_values = [value for value in avg_rate.values()]
            avg_rate['average'] = round(sum(rate_values) / len(rate_values), 2)

        return avg_rate

    # 【code explain】【工程师评分】  计算平均分
    def rebuild_star_rating(self):
        return self.build_star_rating()

    # 【code explain】【工程师评分】  计算平均分
    def get_star_rating(self):
        from developers.tasks import update_developer_cache_data, DEVELOPERS_EXTRA_CACHE_KEY

        developers_data = cache.get(DEVELOPERS_EXTRA_CACHE_KEY, {})
        developer_cache_data = developers_data.get(self.id, {})
        if not developer_cache_data:
            developer_cache_data = update_developer_cache_data(self.id)
        star_rating = developer_cache_data['star_rating']
        return star_rating

    @property
    def star_rating(self):
        return self.get_star_rating()

    @property
    def average_star_rating(self):
        return self.star_rating['average'] if self.star_rating else 0

    # 最近完成的项目
    @property
    def last_project(self):
        project = Project.completion_projects().filter(job_positions__developer_id=self.id).order_by('-done_at').first()
        return project

    # 总项目数
    @property
    def project_total(self):
        project_id_list = self.job_positions.all().values_list('project', flat=True)
        return len(set(project_id_list))

    def my_projects(self):
        projects = Project.objects.filter(job_positions__developer_id=self.id).distinct()
        return projects

    def all_projects(self):
        projects = Project.objects.filter(job_positions__developer_id=self.id).distinct()
        return projects

    def active_projects(self):
        ongoing_projects = Project.ongoing_projects().filter(job_positions__developer_id=self.id).distinct()
        return ongoing_projects

    def get_active_projects(self):
        ongoing_projects = Project.ongoing_projects().filter(job_positions__developer_id=self.id).distinct()
        return ongoing_projects

    def active_project_jobs(self):
        jobs = self.job_positions.exclude(project__done_at__isnull=False).select_related('project')
        return jobs

    def finished_project_jobs(self):
        jobs = self.job_positions.filter(project__done_at__isnull=False)
        return jobs

    # 所有职位的报酬总和、没有判断是否打款
    def payment_total(self):
        jobs = self.job_positions.all()
        return sum([job.total_amount for job in jobs if job.total_amount])

    def latest_payment(self):
        payments = JobPayment.objects.filter(position__developer_id=self.id, status=2).order_by('-completed_at')
        if payments.exists():
            return payments.first()

    def recent_average_payment(self):
        start_date = timezone.now() + timedelta(days=-120)
        end_date = timezone.now()
        pay_list = JobPayment.objects.filter(position__developer_id=self.id, status=2).filter(
            completed_at__gte=start_date, completed_at__lte=end_date).values_list('amount', flat=True)
        return sum([pay for pay in pay_list if pay]) / 4

    def all_projects_jobs(self):
        jobs = self.job_positions.all()
        return jobs

    def last_daily_work(self, project):
        daily_work = project.daily_works.filter(developer_id=self.id).exclude(status='pending').order_by('-day').first()
        if daily_work:
            return daily_work

    def get_partners(self):
        jobs = self.job_positions.all().select_related('project')
        all_projects = {job.project for job in jobs}
        pm_set = set()
        job_set = set()
        pm_cooperation_number = {}
        developer_cooperation_number = {}
        for project in all_projects:
            pm_key = (project.manager.id, project.manager.username)
            if pm_key not in pm_cooperation_number:
                pm_cooperation_number[pm_key] = 0
                pm_set.add(pm_key)
            pm_cooperation_number[pm_key] += 1

            for job in project.job_positions.exclude(developer_id=self.id):
                job_key = (job.developer.id, job.developer.name, job.developer.status, job.role.name)
                if job_key not in developer_cooperation_number:
                    developer_cooperation_number[job_key] = 0
                if job_key not in job_set:
                    job_set.add(job_key)
                developer_cooperation_number[job_key] += 1

        pm_list = [{"id": pm[0], "username": pm[1]} for pm in pm_set]
        developer_list = [
            {"id": developer[0], "name": developer[1], 'status': developer[2], 'role': {'name': developer[3]}} for
            developer in
            job_set]
        for pm in pm_list:
            pm_key = (pm['id'], pm['username'])
            pm['cooperation_number'] = pm_cooperation_number[pm_key]
        for developer in developer_list:
            key = (developer['id'], developer['name'], developer['status'], developer['role']['name'])
            developer['cooperation_number'] = developer_cooperation_number[key]

        pm_order_list = sorted(pm_list, key=lambda pm: pm['cooperation_number'], reverse=True)
        developer_order_list = sorted(developer_list, key=lambda developer: developer['cooperation_number'],
                                      reverse=True)
        partners = {"pm": pm_order_list, "developers": developer_order_list}
        return partners

    def active_developers_documents(self):
        public_documents = Document.active_documents().filter(is_public=True)
        documents = public_documents
        for role in self.roles.all():
            role_documents = role.documents.filter(deleted=False)
            documents = documents | role_documents
        return documents.distinct().order_by('index')

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the developer has been
        authenticated in templates.
        """
        return True

    @property
    def username(self):
        return self.name

    class Meta:
        verbose_name = '工程师'


class DailyWork(models.Model):
    STATUS_CHOICES = (
        ('pending', '等待'),
        ('postpone', '任务延期'),
        ('normal', '正常'),
        ('absence', '缺卡'),
    )
    status = models.CharField(verbose_name="日报状态", max_length=15, choices=STATUS_CHOICES, default='pending')

    project = models.ForeignKey(Project, verbose_name='项目', related_name='daily_works', on_delete=models.CASCADE)
    developer = models.ForeignKey(Developer, verbose_name='工程师', related_name='developer_daily_works',
                                  on_delete=models.CASCADE)

    gantt_tasks = models.TextField(verbose_name='甘特图任务', blank=True, null=True)
    other_task = models.TextField(verbose_name='其他任务', blank=True, null=True)

    day = models.DateField(verbose_name="日期")
    leave_at = models.TimeField(verbose_name="请假开始时间", blank=True, null=True)
    return_at = models.TimeField(verbose_name="请假结束时间", blank=True, null=True)

    need_support = models.BooleanField(verbose_name='是否需要项目组成员支持', default=False)
    remarks = models.TextField(verbose_name='备注', blank=True, null=True)

    # 存储的是前一天对今日的计划
    gantt_tasks_plan = models.TextField(verbose_name='甘特图任务计划', blank=True, null=True)
    other_task_plan = models.TextField(verbose_name='其他任务计划', blank=True, null=True)

    next_day_work = models.ForeignKey(to='self', blank=True, null=True, on_delete=models.SET_NULL)
    browsing_histories = GenericRelation(BrowsingHistory, related_query_name="daily_works")

    need_submit_daily_work = models.BooleanField(default=True)
    punched_at = models.DateTimeField(verbose_name="打卡时间", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    gitlab_commits = models.TextField(verbose_name='代码提交', blank=True, null=True)

    class Meta:
        verbose_name = '工作日报'

    def __str__(self):
        return "【{}】【{}】【{}】工作日报".format(self.project.name, self.developer.name,
                                         self.day.strftime(settings.DATE_FORMAT))

    def roles(self):
        job_positions = self.project.job_positions.filter(developer_id=self.developer_id)
        role_list = []
        for job in job_positions:
            if job.role and job.role not in role_list:
                role_list.append(job.role)
        return role_list

    @property
    def status_display(self):
        return self.get_status_display()

    @classmethod
    def valid_daily_works(cls, queryset=None):
        queryset = queryset or cls.objects.all()
        return queryset.filter(status__in=['normal', 'postpone'])


class DailyWorkTask:
    TASK_STATUS = (
        ('pending', '未开始'),
        ('ongoing', '正在做'),
        ('done', '已完成'),
    )
    TASK_TYPES = (
        ('gantt', '甘特图任务'),
        ('other', '其他任务'),
    )

    def __init__(self):
        self.task_type = 'other'
        self.task_status = 'pending'

        self.gantt_task_id = None

        self.catalogue_name = None
        self.name = None

        self.start_time = None
        self.only_workday = False
        self.expected_finish_time = None
        self.timedelta_days = None

        self.remarks = None
        self.result_remarks = None

    def __str__(self):
        return self.name


class Document(models.Model):
    IMPORTANCE_CHOICES = (
        ('general', '普通'),
        ('major', '重点'),
    )
    title = models.CharField(max_length=100, verbose_name='文档标题', unique=True)
    importance = models.CharField(verbose_name="重要性", max_length=15, choices=IMPORTANCE_CHOICES, default='general')
    is_public = models.BooleanField(verbose_name="是否公开阅读", default=False)
    roles = models.ManyToManyField(Role, verbose_name='职位', related_name='documents')
    deleted = models.BooleanField(verbose_name="是否删除", default=False)
    index = models.IntegerField(verbose_name="排序", default=0)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = '工程师文档'

    @classmethod
    def rebuild_index(cls):
        documents = cls.objects.filter(deleted=False).order_by('index', 'created_at')
        for index, document in enumerate(documents):
            document.index = index
            document.save()

    @classmethod
    def get_new_version(cls, document, version_mode):
        if version_mode == 'mini':
            return cls.get_new_mini_version(document)
        return cls.get_new_large_version(document)

    @classmethod
    def get_new_index(cls):
        document = cls.objects.filter(deleted=False).order_by('-index').first()
        if document:
            return document.index + 1
        return 0

    @classmethod
    def active_documents(cls):
        return cls.objects.filter(deleted=False).order_by('index')

    @classmethod
    def get_new_mini_version(cls, document):
        version = float(document.online_version.version) + 0.1
        version = str(round(version, 1))
        return version

    @classmethod
    def get_new_large_version(cls, document):
        version = float(document.online_version.version) + 1.0
        version = math.floor(version)
        version = '{:.1f}'.format(version)
        return version

    @property
    def online_version(self):
        return self.versions.filter(status='online').first()

    @property
    def history_versions(self):
        return self.versions.filter(status='history').order_by('-version')

    # TPM与工程师对当前大版本的同步记录   小版本继承最近一个大版本及之后的所有读记录 （小版本更新 之前的记录也算在该小版本上）
    def developer_current_large_version_sync_log(self, developer):
        online_version = self.online_version
        read_log = developer.document_sync_logs.filter(document_id=online_version.id).order_by('-created_at').first()
        if online_version.version_mode == 'large':
            return read_log
        elif online_version.version_mode == 'mini':
            if not read_log:
                history_versions = self.history_versions
                for version in history_versions:
                    read_log = developer.document_sync_logs.filter(document_id=version.id).order_by(
                        '-created_at').first()
                    # 查到最近阅读记录 或遇到大版本 停止
                    if read_log:
                        break
                    if version.version_mode == 'large':
                        break
        return read_log

    # 工程师对当前大版本的阅读记录   小版本继承最近一个大版本及之后的所有的阅读记录 （小版本更新 之前的阅读记录也算在该小版本上）
    def developer_current_large_version_read_log(self, developer):
        online_version = self.online_version
        read_log = developer.document_read_logs.filter(document_id=online_version.id).order_by('-created_at').first()
        if online_version.version_mode == 'large':
            return read_log
        elif online_version.version_mode == 'mini':
            if not read_log:
                history_versions = self.history_versions
                for version in history_versions:
                    read_log = developer.document_read_logs.filter(document_id=version.id).order_by(
                        '-created_at').first()
                    # 查到最近阅读记录 或遇到大版本 停止
                    if read_log:
                        break
                    if version.version_mode == 'large':
                        break
        return read_log

    # Farm用户对当前大版本的阅读记录    小版本继承最近一个大版本及之后的所有的阅读记录 （小版本更新 之前的阅读记录也算在该小版本上）
    def user_current_large_version_read_log(self, user):
        online_version = self.online_version
        read_log = user.document_read_logs.filter(document_id=online_version.id).order_by(
            '-created_at').first()
        if online_version.version_mode == 'large':
            return read_log
        elif online_version.version_mode == 'mini':
            if not read_log:
                history_versions = self.history_versions
                for version in history_versions:
                    read_log = user.document_read_logs.filter(document_id=version.id).order_by('-created_at').first()
                    if read_log:
                        break
                    if version.version_mode == 'large':
                        break
        return read_log

    # 工程师最近的阅读记录
    def developer_last_large_version_read_log(self, developer):
        read_log = None
        versions = self.versions.order_by('-version')
        for version in versions:
            read_log = developer.document_read_logs.filter(document_id=version.id).order_by('-created_at').first()
            if read_log:
                break
        return read_log

    # 工程师最近有阅读记录的大版本 的最新版本  （小版本继承它对应的一个大版本及之后的所有的阅读记录）
    def developer_last_read_version(self, developer):
        versions = self.versions.order_by('-version')
        read_version = None
        read_log = None
        for version in versions:
            # 默认当前版本为已读版本
            if read_version is None:
                read_version = version
            read_log = developer.document_read_logs.filter(document_id=version.id).order_by('-created_at').first()
            if read_log:
                break
            # 遇到大版本 未读 已读版本置空
            if version.version_mode == 'large':
                read_version = None
        if not read_log:
            read_version = None

        return read_version

    # 跳过同步
    def skip_sync_project_developer_document(self, project, developer):
        cache_key = 'skipped_sync_project_developer_documents'
        skip_sync_cache = cache.get(cache_key, set())
        key = 'project-{}-developer-{}-document-{}'.format(project.id, developer.id, self.id)
        skip_sync_cache.add(key)
        cache.set(cache_key, skip_sync_cache, None)

    # 是否跳过同步
    def project_developer_is_skipped(self, project, developer):
        cache_key = 'skipped_sync_project_developer_documents'
        skip_sync_cache = cache.get(cache_key, set())
        key = 'project-{}-developer-{}-document-{}'.format(project.id, developer.id, self.id)
        return key in skip_sync_cache


class DocumentVersion(models.Model):
    VERSION_MODE_CHOICES = (
        ('mini', '小版本'),
        ('large', '大版本'),
    )
    STATUS_CHOICES = (
        ('online', '线上版本'),
        ('history', '历史版本'),
    )
    document = models.ForeignKey(Document, verbose_name='文档', related_name='versions', on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='document_versions', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    version = models.CharField(verbose_name='版本号', max_length=10, default='1.0', blank=True, null=True)
    version_mode = models.CharField(verbose_name='版本类型', choices=VERSION_MODE_CHOICES, max_length=10, default='large')
    status = models.CharField(verbose_name='状态', max_length=10, choices=STATUS_CHOICES, default='online')
    html = models.TextField(verbose_name="来源html", blank=True, null=True)
    clean_html = models.TextField(verbose_name="来源html", blank=True, null=True)
    remarks = models.TextField(verbose_name="备注", blank=True, null=True)

    source = models.CharField(verbose_name='创建来源', max_length=20, default='quip_link')
    quip_doc_id = models.CharField(verbose_name="Quip文档ID", max_length=30)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)

    class Meta:
        verbose_name = '文档版本'

    def get_developer_read_log(self, developer):
        read_log = developer.document_read_logs.filter(document_id=self.id, developer_id=developer.id).first()
        return read_log

    def get_user_read_log(self, user):
        read_log = user.document_read_logs.filter(document_id=self.id, user_id=user.id).first()
        return read_log

    # 当前版本 所属的大版本的阅读记录  该大版本 该大版本对应的小版本中任何一个版本阅读 都算已读
    def get_developer_large_version_read_log(self, developer):
        versions = self.document.versions.all()
        large_versions = versions.filter(version_mode='large')

        start_version = large_versions.filter(version__lte=self.version).order_by('-version').first()
        end_version = large_versions.filter(version__gt=self.version).order_by('version').first()

        versions = versions.filter(version__gte=start_version.version).order_by('-version')
        if end_version:
            versions = versions.filter(version__lt=end_version.version).order_by('-version')
        read_log = None
        for version in versions:
            read_log = developer.document_read_logs.filter(document_id=version.id,
                                                           developer_id=developer.id).first()
            if read_log:
                break
        return read_log

    # 当前版本 所属的大版本的阅读记录  该大版本 该大版本对应的小版本中任何一个版本阅读 都算已读
    def get_user_large_version_read_log(self, user):
        versions = self.document.versions.all()
        large_versions = versions.filter(version_mode='large')
        start_version = large_versions.filter(version__lte=self.version).order_by('-version').first()
        end_version = large_versions.filter(version__gt=self.version).order_by('version').first()
        versions = versions.filter(version__gte=start_version.version).order_by('-version')
        if end_version:
            versions = versions.filter(version__lt=end_version.version).order_by('-version')
        read_log = None
        for version in versions:
            read_log = user.document_read_logs.filter(document_id=version.id,
                                                      user_id=user.id).first()
            if read_log:
                break
        return read_log


class DocumentReadLog(models.Model):
    document = models.ForeignKey(DocumentVersion, verbose_name='文档版本', related_name='read_logs',
                                 on_delete=models.CASCADE)

    user = models.ForeignKey(User, verbose_name='读者-Farm用户', related_name='document_read_logs',
                             blank=True,
                             null=True,
                             on_delete=models.CASCADE)
    developer = models.ForeignKey(Developer, verbose_name='读者-工程师', related_name='document_read_logs',
                                  blank=True,
                                  null=True,
                                  on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")

    class Meta:
        verbose_name = '工程师文档阅读记录'


class DocumentSyncLog(models.Model):
    document = models.ForeignKey(DocumentVersion, verbose_name='文档版本', related_name='sync_logs',
                                 on_delete=models.CASCADE)
    user = models.ForeignKey(User, verbose_name='同步-Farm用户', related_name='document_sync_logs',
                             on_delete=models.CASCADE)
    developer = models.ForeignKey(Developer, verbose_name='同步-工程师', related_name='document_sync_logs',
                                  on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")

    class Meta:
        verbose_name = '工程师文档同步沟通'

    def __str__(self):
        return "【{}】【{}】【{}】同步记录".format(self.document.document.title, self.user.username,
                                         self.developer.name)
