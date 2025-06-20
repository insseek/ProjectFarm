import time
import random

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import reverse
from django.utils import timezone
from multiselectfield import MultiSelectField

from files.models import File
from tasks.models import Task


class Client(models.Model):
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
        url = "clients/avatar-{}-{}".format(self.id, filename)
        return url

    phone = models.CharField(max_length=20, verbose_name='手机号')
    username = models.CharField(max_length=50, verbose_name='名称')
    email = models.EmailField(blank=True, null=True)

    avatar = models.ImageField(upload_to=generate_filename, verbose_name='头像', null=True, blank=True)
    avatar_color = models.CharField(verbose_name='头像颜色', choices=AVATAR_COLORS, max_length=10, blank=True, null=True)

    is_active = models.BooleanField(verbose_name='有效', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(verbose_name='最近登录时间', blank=True, null=True)

    creator = models.ForeignKey('auth_top.TopUser', verbose_name='创建人', related_name='clients', null=True, blank=True,
                                on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if not self.avatar_color:
            self.avatar_color = self.get_random_avatar_color()
        super(Client, self).save(*args, **kwargs)

    def get_random_avatar_color(self):
        randint = random.randint(0, len(self.AVATAR_COLORS) - 1)
        return self.AVATAR_COLORS[randint][0]

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = '项目客户'


class LeadIndividual(models.Model):
    name = models.CharField(verbose_name="名称", max_length=64)
    phone_number = models.CharField(verbose_name="联系人联系方式", max_length=30, blank=True, null=True)
    creator = models.ForeignKey(User, verbose_name='创建人', related_name='lead_individuals', on_delete=models.SET_NULL,
                                null=True, blank=True)

    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '个人客户'

    def __str__(self):
        return self.name


class LeadOrganization(models.Model):
    organization_type = models.CharField(verbose_name="组织类型", max_length=30, blank=True, null=True)
    name = models.CharField(verbose_name="名称", max_length=64)
    creator = models.ForeignKey(User, verbose_name='创建人', related_name='lead_organizations', on_delete=models.SET_NULL,
                                null=True, blank=True)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '组织客户'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.organization_type in ['other', '其他']:
            self.organization_type = None
        super(LeadOrganization, self).save(*args, **kwargs)


class LeadSource(models.Model):
    # 来源类型的附属字段查询
    SOURCE_EDITABLE_FIELDS = ['source_type', 'sem_type', 'sem_track_code', 'leave_info_type',
                              'leave_info_at', 'sem_project_category', 'sem_search_term', 'source_address',
                              'referer_url', 'content_marketing_type',
                              'track_code', 'source_remark',
                              'organization', 'organization_name',
                              'organization_type',
                              'contact_name', 'contact_info', 'activity_type',
                              'activity_name']

    SOURCE_FIELDS_DICT = {
        'sem': [
            {'field_name': 'sem_type', 'verbose_name': '类型'},
            {'field_name': 'sem_track_code', 'verbose_name': '追踪码'},
            {'field_name': 'leave_info_type', 'verbose_name': '留资方式'},
            {'field_name': 'leave_info_at', 'verbose_name': '留资时间'},
            {'field_name': 'sem_project_category', 'verbose_name': 'SEM产品分类'},
            {'field_name': 'sem_search_term', 'verbose_name': 'SEM搜索词'},
            {'field_name': 'source_address', 'verbose_name': '来源地区'},
        ],
        'website': [
            {'field_name': 'referer_url', 'verbose_name': '页面链接'},
            {'field_name': 'track_code', 'verbose_name': '追踪码'},
            {'field_name': 'leave_info_type', 'verbose_name': '留资方式'},
            {'field_name': 'leave_info_at', 'verbose_name': '留资时间'}
        ],
        'content_marketing': [
            {'field_name': 'content_marketing_type', 'verbose_name': '类型'},
            {'field_name': 'track_code', 'verbose_name': '追踪码'},
            {'field_name': 'leave_info_type', 'verbose_name': '留资方式'},
            {'field_name': 'leave_info_at', 'verbose_name': '留资时间'},
            {'field_name': 'source_remark', 'verbose_name': '备注'},
        ],
        'social_network': [
            {'field_name': 'organization_name', 'verbose_name': '推荐人工作单位'},
            {'field_name': 'contact_name', 'verbose_name': '推荐人姓名'},
            {'field_name': 'contact_info', 'verbose_name': '推荐人联系方式'},
        ],
        'client_new_project': [
            {'field_name': 'organization_name', 'verbose_name': '客户企业名称'},
        ],
        'client_project_iteration': [
            {'field_name': 'organization_name', 'verbose_name': '客户企业名称'},
        ],
        'client_referral': [
            {'field_name': 'organization_name', 'verbose_name': '客户企业名称'},
            {'field_name': 'contact_name', 'verbose_name': '推荐人'},
            {'field_name': 'contact_info', 'verbose_name': '推荐人联系方式'},
        ],
        'activity': [
            {'field_name': 'activity_type', 'verbose_name': '活动类型'},
            {'field_name': 'activity_name', 'verbose_name': '活动名称'}
        ],
        'startup_camp': [
            {'field_name': 'organization_name', 'verbose_name': '公司名称'},
            {'field_name': 'contact_name', 'verbose_name': '对接人'},
            {'field_name': 'contact_info', 'verbose_name': '对接人联系方式'},
        ],
        'org_referral': [
            {'field_name': 'organization_type', 'verbose_name': '类型'},
            {'field_name': 'organization_name', 'verbose_name': '名称'},
            {'field_name': 'contact_name', 'verbose_name': '对接人'},
            {'field_name': 'contact_info', 'verbose_name': '对接人联系方式'},
        ],
    }
    #  线索的
    LEAD_SOURCES = (
        ('sem', 'SEM'),
        ('website', '官网（非SEM）'),
        ('content_marketing', '内容营销'),
        ('social_network', '社群/朋友圈/微信好友'),
        # ('client_project_iteration', '客户项目迭代'),
        ('client_new_project', '客户新项目'),
        ('client_referral', '客户推荐'),
        ('activity', '活动'),
        ('startup_camp', '创业营/商学院/训练营'),
        ('org_referral', '企业/机构/协会推荐'),
        # ('other', '其他'),
    )
    # 需求的
    SOURCES = (
        ('sem', 'SEM'),
        ('website', '官网（非SEM）'),
        ('content_marketing', '内容营销'),
        ('social_network', '社群/朋友圈/微信好友'),
        ('client_project_iteration', '客户项目迭代'),
        ('client_new_project', '客户新项目'),
        ('client_referral', '客户推荐'),
        ('activity', '活动'),
        ('startup_camp', '创业营/商学院/训练营'),
        ('org_referral', '企业/机构/协会推荐'),
        ('other', '其他'),
    )
    SEM_CHOICES = (
        ('sougou', '搜狗'),
        ('shenma', '神马'),
        ('360', '360'),
        ('baidu', '百度'),
        ('google', '谷歌'),
        ('phone', '400电话'),
        ('toutiao', '今日头条'),
        ('other', '其他')
    )
    LEAVE_INFO_TYPES = (
        ('53kf', '53客服'),
        ('form_submit', '表单提交'),
    )
    CONTENT_MARKETING_CHOICES = (
        ('wx_mp', '微信小程序'),
        ('wx_service', '微信服务号'),
        ('wx_sub', '微信订阅号'),
        ('other', '其他'),
    )
    ACTIVITY_TYPES = (
        ('sponsor', '自办活动'),
        ('cosponsor', '协办活动'),
        ('participator', '参加活动'),
    )
    ORGANIZATION_TYPES = (
        ('云服务商', '云服务商'),
        ('SaaS服务商', 'SaaS服务商'),
        ('众包平台', '众包平台'),
        ('选型平台', '选型平台'),
        ('培训机构', '培训机构'),
        ('投资机构', '投资机构'),
        ('FA', 'FA'),
        ('行业协会', '行业协会'),
        ('众创空间', '众创空间'),
        ('孵化器', '孵化器'),
        ('公关营销公司', '公关营销公司'),
        ('咨询公司', '咨询公司'),
        ('设计公司', '设计公司'),
        ('友商竞品', '友商竞品'),
        ('代理商', '代理商'),
        ('集成商', '集成商'),
        ('行业媒体', '行业媒体'),
        ('其它', '其它'),
    )

    source_type = models.CharField(verbose_name="来源类型", max_length=35, choices=SOURCES, default='other')
    # SEM来源字段
    sem_type = models.CharField(verbose_name="SEM来源类型", max_length=25, choices=SEM_CHOICES, blank=True, null=True)
    sem_track_code = models.CharField(verbose_name="SEM追踪码", max_length=20, blank=True, null=True)
    sem_project_category = models.TextField(verbose_name="SEM产品分类", blank=True, null=True)
    sem_search_term = models.TextField(verbose_name="SEM搜索词", blank=True, null=True)
    source_address = models.TextField(verbose_name="来源地区", blank=True, null=True)

    # SEM 、官网（非SEM）、内容营销
    leave_info_type = models.CharField(verbose_name="客户留资方式", max_length=15, choices=LEAVE_INFO_TYPES, blank=True,
                                       null=True)
    leave_info_at = models.DateTimeField(verbose_name='客户留资时间', blank=True, null=True)

    # 官网（非SEM）来源字段
    referer_url = models.TextField(verbose_name="页面url", blank=True, null=True)
    # 官网（非SEM）、内容营销
    track_code = models.TextField(verbose_name="追踪码（非SEM）", max_length=20, blank=True, null=True)

    # 内容营销来源字段
    content_marketing_type = models.CharField(verbose_name="内容营销来源类型", max_length=25, choices=CONTENT_MARKETING_CHOICES,
                                              blank=True, null=True)
    # 内容营销为其他的备注
    source_remark = models.CharField(verbose_name="来源备注", max_length=64, blank=True, null=True)

    # 活动
    activity_type = models.CharField(verbose_name="来源活动类型", max_length=15, choices=ACTIVITY_TYPES, blank=True,
                                     null=True)
    activity_name = models.CharField(verbose_name="来源活动名称", max_length=64, blank=True, null=True)

    organization_type = models.CharField(verbose_name="机构/企业类型", max_length=20, choices=ORGANIZATION_TYPES, blank=True,
                                         null=True)
    # 客户企业、机构、创业营
    organization = models.ForeignKey(LeadOrganization, verbose_name='企业/组织/机构', related_name='lead_sources',
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True)
    # 客户推荐、创业营、企业推荐
    contact_name = models.CharField(verbose_name="机构对接人姓名", max_length=20, blank=True, null=True)
    contact_info = models.TextField(verbose_name="机构对接人联系方式", blank=True, null=True)

    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '线索来源'

    def __str__(self):
        return self.get_source_type_display()

    @property
    def source_type_display(self):
        return self.get_source_type_display()

    @property
    def sem_type_display(self):
        return self.get_sem_type_display()

    @property
    def leave_info_type_display(self):
        return self.get_leave_info_type_display()

    @property
    def content_marketing_type_display(self):
        return self.get_content_marketing_type_display()

    @property
    def activity_type_display(self):
        return self.get_activity_type_display()

    @property
    def organization_type_display(self):
        return self.get_organization_type_display()

    @property
    def source_info(self):
        texts = []
        source_type = self.source_type
        # source_type_text = '来源类型：' + lead_source_data['source_type_display']
        # texts.append(source_type_text)
        source_fields_dict = LeadSource.SOURCE_FIELDS_DICT
        if source_type in source_fields_dict:
            source_fields = source_fields_dict[source_type]
            for source_field in source_fields:
                field_name = source_field['field_name']
                verbose_name = source_field['verbose_name']
                field_value = getattr(self, field_name, '')
                text = '{}：{}'.format(verbose_name, field_value if field_value else '')
                texts.append(text)
        return '；\n'.join(texts)


class Lead(models.Model):
    RELIABILITY_DEGREES = (
        ('general', '普通'),
        ('major', '重点'),
    )
    STATUS = (
        ('contact', '前期沟通'),
        ('proposal', '进入需求'),
        ('no_deal', '未成单'),
        ('deal', '成单'),
        ('apply_close', '关闭审核'),
        ('invalid', '无效关闭'),
    )
    NOT_EDITABLE_FIELDS = ('status', 'creator', 'created_at', 'modified_at')
    lead_source = models.OneToOneField(LeadSource, verbose_name='线索来源数据', related_name='lead',
                                       on_delete=models.SET_NULL,
                                       null=True, blank=True)

    name = models.CharField(verbose_name="名称", max_length=64)
    description = models.TextField(verbose_name="线索简介")
    remarks = models.TextField(verbose_name="线索备注", blank=True, null=True)

    status = models.CharField(verbose_name="线索状态", max_length=15, choices=STATUS, default='contact')
    reliability = models.CharField(verbose_name="靠谱度", max_length=10, choices=RELIABILITY_DEGREES, default='general')

    has_rebate = models.BooleanField(verbose_name="返点", default=False)
    rebate_info = models.CharField(verbose_name="返点信息", max_length=64, blank=True, null=True)
    rebate_proportion = models.IntegerField(verbose_name="返点百分比例", blank=True, null=True)

    # 线索联系人信息
    company = models.ForeignKey(LeadOrganization, verbose_name='企业客户', related_name='client_leads',
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    company_name = models.CharField(verbose_name="公司名称", max_length=64, blank=True, null=True)
    contact_name = models.CharField(verbose_name="联系人姓名", max_length=20, blank=True, null=True)
    contact_job = models.CharField(verbose_name="联系人职位", max_length=20, blank=True, null=True)
    phone_number = models.CharField(verbose_name="联系方式", max_length=30, blank=True, null=True)
    address = models.CharField(verbose_name="地址", max_length=150, blank=True, null=True)
    # 线索联系人结束

    creator = models.ForeignKey(User, verbose_name='创建人', related_name='created_leads', on_delete=models.SET_NULL,
                                null=True, blank=True)
    salesman = models.ForeignKey(User, verbose_name='销售', related_name='sales_leads', on_delete=models.SET_NULL,
                                 null=True, blank=True)
    closed_by = models.ForeignKey(User, verbose_name='关闭者', related_name='closed_leads', on_delete=models.SET_NULL,
                                  null=True, blank=True)
    apply_closed_by = models.ForeignKey(User, verbose_name='申请关闭者', related_name='apply_closed_leads',
                                        on_delete=models.SET_NULL,
                                        null=True, blank=True)

    file_list = GenericRelation(File, related_query_name="leads")
    tasks = GenericRelation(Task, related_query_name="leads")

    invalid_reason = models.CharField(verbose_name="关闭理由", max_length=100, blank=True, null=True)
    invalid_remarks = models.TextField(verbose_name="关闭备注", blank=True, null=True)
    apply_closed_at = models.DateTimeField(verbose_name='申请关闭时间', blank=True, null=True)

    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    closed_at = models.DateTimeField(verbose_name='关闭时间', blank=True, null=True)
    proposal_created_at = models.DateTimeField(verbose_name='进入需求时间', blank=True, null=True)
    proposal_closed_at = models.DateTimeField(verbose_name='需求关闭时间', blank=True, null=True)
    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')

    class Meta:
        verbose_name = '线索'

    def __str__(self):
        return self.name

    @property
    def participants(self):
        return [self.salesman]

    @classmethod
    def pending_leads(cls):
        return cls.objects.filter(status='contact')

    @classmethod
    def ongoing_leads(cls):
        return cls.objects.filter(status__in=['contact', 'proposal'])

    @property
    def files(self):
        return self.file_list.filter(is_deleted=False).order_by('created_at')

    @property
    def closed_reason(self):
        if self.invalid_reason and self.invalid_remarks:
            return '{}()'.format(self.invalid_reason, self.invalid_remarks)
        return self.invalid_reason or self.invalid_remarks

    def undone_tasks(self):
        tasks = self.tasks.filter(is_done=False).order_by('expected_at')
        return tasks

    def close_auto_tasks(self):
        tasks = self.undone_tasks()
        for task in tasks:
            if task.auto_close_required:
                task.done_at = timezone.now()
                task.is_done = True
                task.save()

    @property
    def quotation_status(self):
        quotations = self.quotations.order_by('-edited_at')
        if quotations.exists():
            return quotations.first().status

    @property
    def can_be_converted_to_proposal(self):
        if self.reports.filter(is_public=True).exists():
            return True
        elif self.report_files.filter(is_active=True).exists():
            return True
        elif self.punch_records.filter(contact_type="meet").exists():
            return True
        elif self.punch_records.count() > 1:
            return True

    @property
    def last_published_report(self):
        report = self.reports.filter(is_public=True).order_by('-published_at').first()

    def latest_report_data(self):
        reports = self.reports.filter(is_public=True).order_by('-published_at')
        if reports.exists():
            latest_report = reports.first()
            title = latest_report.title
            author = latest_report.author
            created_at = latest_report.created_at.strftime(settings.DATETIME_FORMAT)
            report_url = settings.REPORTS_HOST + reverse('reports:view', args=(latest_report.uid,))
            report_preview_url = reverse('reports:preview', args=(latest_report.uid,))
            return {"title": title, "report_url": report_url, "author": author,
                    "created_at": created_at, "published_at": latest_report.published_at,
                    'report_preview_url': report_preview_url,
                    'is_expired': latest_report.is_expired()}

    def latest_punch_record(self):
        return self.punch_records.order_by('-created_at').first()

    def project(self):
        from proposals.models import Proposal
        proposal = Proposal.objects.filter(lead_id=self.id)
        if proposal.exists() and proposal.first().project_id:
            return proposal.first().project


class ClientInfo(models.Model):
    from proposals.models import Proposal
    lead = models.OneToOneField(Lead, verbose_name='线索', related_name='client_info', blank=True, null=True,
                                on_delete=models.SET_NULL)
    proposal = models.OneToOneField(Proposal, verbose_name='需求', related_name='client_info', blank=True, null=True,
                                    on_delete=models.SET_NULL)
    company = models.ForeignKey(LeadOrganization, verbose_name='企业客户', related_name='client_infos',
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    company_name = models.CharField(verbose_name="公司名称", max_length=64, blank=True, null=True)
    address = models.CharField(verbose_name="客户地址", max_length=150, blank=True, null=True)
    company_link = models.TextField(verbose_name="公司相关链接", blank=True, null=True)
    company_description = models.TextField(verbose_name="公司简介", blank=True, null=True)
    contact_name = models.CharField(verbose_name="联系人姓名", max_length=20, blank=True, null=True)
    contact_job = models.CharField(verbose_name="联系人职位", max_length=20, blank=True, null=True)
    phone_number = models.CharField(verbose_name="联系方式", max_length=30, blank=True, null=True)
    CLIENT_BACKGROUNDS = (
        ('0', '个人'),
        ('1', '初创团队'),
        ('2', '传统企业'),
        ('3', '大型/上市公司'),
        ('4', '互联网公司事业部'),
        ('5', '其他'),
    )
    client_background = models.CharField(verbose_name="客户背景", max_length=2, choices=CLIENT_BACKGROUNDS)
    client_background_remarks = models.CharField(verbose_name="客户背景备注", max_length=64, blank=True, null=True)

    ROLES = (
        ('0', '对接人'),
        ('1', '决策人'),
        ('2', '中间人'),
    )
    contact_role = models.CharField(verbose_name="联系人角色", max_length=2, choices=ROLES)
    DECISION_MAKING_CHOICES = (
        ('0', '只收集信息向上级汇报'),
        ('1', '拥有一定决策能力'),
    )
    decision_making_capacity = models.CharField(verbose_name="决策能力", max_length=2, choices=DECISION_MAKING_CHOICES)
    TECHNICAL_CHOICES = (
        ('0', '懂产品技术，能力还行'),
        ('1', '不太懂，觉得自己懂'),
        ('2', '不懂，且知道自己不懂'),
    )
    technical_capacity = models.CharField(verbose_name="技术能力", max_length=2, choices=TECHNICAL_CHOICES)

    COMMUNICATIONS = (
        ('0', '易于沟通和说服'),
        ('1', '较强势'),
        ('2', '逻辑性强，条理清楚'),
        ('3', '逻辑混乱'),
        ('4', '抠细节，有些事儿'),
    )
    communication_cost = MultiSelectField(verbose_name="沟通成本", choices=COMMUNICATIONS)

    REBATE_CHOICES = (
        ('0', '渠道介绍，需要分成'),
        ('1', '内部成员，但需要返点'),
        ('2', '不需要返点'),
    )

    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_client_infos',
                                  on_delete=models.SET_NULL,
                                  null=True, blank=True)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '客户信息'


class RequirementInfo(models.Model):
    SERVICES = (
        ('0', '产品咨询'),
        ('1', '原型设计'),
        ('2', 'UI设计'),
        ('3', '前端开发'),
        ('4', '后端开发'),
        ('5', '运维服务'),
    )
    lead = models.OneToOneField(Lead, verbose_name='线索', related_name='requirement', blank=True, null=True,
                                on_delete=models.SET_NULL)
    name = models.CharField(verbose_name="需求名称", max_length=64)
    CLIENT_BACKGROUNDS = (
        ('0', '个人'),
        ('1', '初创团队'),
        ('2', '传统企业'),
        ('3', '大型/上市公司'),
        ('4', '互联网公司事业部'),
    )
    client_background = models.CharField(verbose_name="客户背景", max_length=2, choices=CLIENT_BACKGROUNDS)
    client_background_remarks = models.CharField(verbose_name="客户背景备注", max_length=64, blank=True, null=True)

    service = MultiSelectField(verbose_name="服务内容", choices=SERVICES)
    service_remarks = models.CharField(verbose_name="服务内容备注", max_length=64, blank=True, null=True)

    RELIABILITY_FACTORS = (
        ('0', '询价比价为主'),
        ('1', '朋友/客户推荐'),
        ('2', '原有产品二次开发'),
        ('3', '无其他因素'),
    )
    reliability_factor = MultiSelectField(verbose_name="靠谱度影响因素", choices=RELIABILITY_FACTORS)
    reliability_remarks = models.CharField(verbose_name="靠谱度影响因素备注", max_length=64, blank=True, null=True)

    business_objective = models.TextField(verbose_name="业务目标")

    PLATFORMS = (
        ('0', 'iOS'),
        ('1', 'Android'),
        ('2', '小程序'),
        ('3', '管理后台'),
        ('4', 'PC端网页web'),
        ('5', '移动端/公共号H5'),
        ('6', '软硬件结合'),
        ('7', '其他'),
    )
    application_platform = MultiSelectField(verbose_name="应用平台", choices=PLATFORMS)
    platform_remarks = models.CharField(verbose_name="应用平台备注", max_length=64, blank=True, null=True)

    MATERIALS = (
        ('0', '只有需求描述'),
        ('1', 'BP/PPT版介绍'),
        ('2', '功能列表/思维导图'),
        ('3', '原型'),
        ('4', '设计稿'),
        ('5', '已有产品名称/链接'),
        ('6', '已有产品截图'),
        ('7', '其他'),
    )
    available_material = MultiSelectField(verbose_name="已有材料", choices=MATERIALS)
    material_remarks = models.CharField(verbose_name="已有材料备注", max_length=64, blank=True, null=True)

    REFERENCES = (
        ('0', '参考全部'),
        ('1', '参考部分页面/流程'),
        ('2', '其他'),
        ('3', '无'),
    )
    reference = models.CharField(verbose_name="竞品参考", max_length=2, choices=REFERENCES)
    reference_remarks = models.CharField(verbose_name="竞品参考备注", max_length=64, blank=True, null=True)

    case = models.CharField(verbose_name="案例", max_length=96, blank=True, null=True)

    DECISION_FACTORS = (
        ('0', '价格敏感'),
        ('1', '质量敏感'),
        ('2', '业务最终目标敏感'),
    )
    decision_factor = MultiSelectField(verbose_name="决策因素", choices=DECISION_FACTORS)

    RIGID_REQUIREMENTS = (
        ('0', 'UI视觉要求'),
        ('1', '代码语言要求'),
        ('2', '其他'),
    )

    rigid_requirement = MultiSelectField(verbose_name="硬性要求", choices=RIGID_REQUIREMENTS)
    rigid_requirement_remarks = models.CharField(verbose_name="硬性要求备注", max_length=96, blank=True, null=True)

    budget = models.CharField(verbose_name="预算范围", max_length=64, blank=True, null=True)
    period = models.CharField(verbose_name="时间范围", max_length=64, blank=True, null=True)
    decision_period = models.CharField(verbose_name="决策周期", max_length=64, blank=True, null=True)
    special_time_point = models.CharField(verbose_name="特殊时间节点", max_length=64, blank=True, null=True)
    contact_name = models.CharField(verbose_name="联系人姓名", max_length=30)
    ROLES = (
        ('0', '对接人'),
        ('1', '决策人'),
        ('2', '中间人'),
    )
    contact_role = models.CharField(verbose_name="联系人角色", max_length=2, choices=ROLES)
    APPEAL_ONE_CHOICES = (
        ('0', '只收集信息向上级汇报'),
        ('1', '拥有一定决策能力'),
    )
    APPEAL_TWO_CHOICES = (
        ('0', '懂产品技术，能力还行'),
        ('1', '不太懂，觉得自己懂'),
        ('2', '不懂，且知道自己不懂'),
    )
    APPEAL_THREE_CHOICES = (
        ('0', '渠道介绍，需要分成'),
        ('1', '内部成员，但需要返点'),
        ('2', '不需要返点'),
    )
    appeal_background_one = models.CharField(verbose_name="诉求背景一", max_length=2, choices=APPEAL_ONE_CHOICES)
    appeal_background_two = models.CharField(verbose_name="诉求背景二", max_length=2, choices=APPEAL_TWO_CHOICES)
    appeal_background_three = models.CharField(verbose_name="诉求背景三", max_length=2, choices=APPEAL_THREE_CHOICES)
    rebate_proportion = models.IntegerField(verbose_name="返点比例", blank=True, null=True)

    other_remarks = models.TextField(verbose_name="其他说明", blank=True, null=True)
    other_decision_maker = models.CharField(verbose_name="其他决策人", max_length=64, blank=True, null=True)

    COMMUNICATIONS = (
        ('0', '易于沟通和说服'),
        ('1', '较强势'),
        ('2', '逻辑性强，条理清楚'),
        ('3', '逻辑混乱'),
        ('4', '抠细节，有些事儿'),
    )
    communication_cost = MultiSelectField(verbose_name="沟通成本", choices=COMMUNICATIONS)

    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_requirements',
                                  on_delete=models.SET_NULL,
                                  null=True, blank=True)

    file_list = GenericRelation(File, related_query_name="requirement")
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    created_date = models.DateField(verbose_name='创建日期', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '客户需求信息'

    def __str__(self):
        return self.name

    @property
    def files(self):
        return self.file_list.filter(is_deleted=False).order_by('created_at')


class LeadPunchRecord(models.Model):
    TYPES = (
        ('phone', '电话'),
        ('meet', '会面')
    )
    lead = models.ForeignKey(Lead, verbose_name='线索', related_name='punch_records', on_delete=models.CASCADE)
    contact_type = models.CharField(verbose_name="联系方式", max_length=5, choices=TYPES)
    contact_time = models.DateTimeField(verbose_name='联系时间')
    contact_result = models.TextField(verbose_name="沟通结果", blank=True, null=True)
    remarks = models.TextField(verbose_name="备注")
    creator = models.ForeignKey(User, verbose_name='创建人', related_name='created_punch_records',
                                on_delete=models.CASCADE)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '联系打卡记录'

    def __str__(self):
        return "{} {}".format(self.get_contact_type_display(), self.contact_time.strftime(settings.DATETIME_FORMAT))


class TrackCodeFile(models.Model):
    entry_path = models.TextField(verbose_name="上传文件", blank=True, null=True)
    output_path = models.TextField(verbose_name="导出文件", blank=True, null=True)
    filename = models.CharField(verbose_name="文件名称", max_length=128, blank=True, null=True)
    is_template = models.BooleanField(default=False)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '跟踪码文件'

    def __str__(self):
        return self.filename


class LeadTrack(models.Model):
    channel = models.CharField(verbose_name="渠道", max_length=30, blank=True, null=True)
    media = models.CharField(verbose_name="媒体", max_length=30, blank=True, null=True)
    account = models.CharField(verbose_name="账户", max_length=30, blank=True, null=True)
    plan = models.CharField(verbose_name="计划", max_length=64, blank=True, null=True)
    unit = models.TextField(verbose_name="单元", blank=True, null=True)
    keywords = models.TextField(verbose_name="关键词", blank=True, null=True)
    device = models.CharField(verbose_name="设备", max_length=30, blank=True, null=True)

    url = models.TextField(verbose_name="URL", blank=True, null=True)
    track_code = models.CharField(verbose_name="跟踪码", max_length=20, blank=True, null=True, unique=True)
    md5_hash = models.TextField(verbose_name="URL", blank=True, null=True)
    track_url = models.TextField(verbose_name="跟踪URL", blank=True, null=True)

    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '跟踪码'


class LeadQuotation(models.Model):
    STATUS_CHOICES = (
        ('waiting', '等待报价'),
        ('rejected', '已驳回'),
        ('quoted', '已经报价')
    )
    REQUIRE_STATUS = (
        ('mvp', 'MVP'),
        ('ripe_product', '成熟产品')
    )
    lead = models.ForeignKey(Lead, verbose_name='线索', related_name='quotations', on_delete=models.CASCADE)
    status = models.CharField(verbose_name="状态", max_length=15, choices=STATUS_CHOICES, default='waiting')
    company_name = models.TextField(verbose_name="客户公司", blank=True, null=True)

    company_business = models.TextField(verbose_name="公司业务", blank=True, null=True)
    product_description = models.TextField(verbose_name="产品描述", blank=True, null=True)
    development_goal = models.TextField(verbose_name='开发目标', blank=True, null=True)
    integrity_require = models.CharField(verbose_name='完整度要求', max_length=20, choices=REQUIRE_STATUS, blank=True,
                                         null=True)

    # APP，小程序，网站，H5，管理后台
    product_applications = models.TextField(verbose_name="产品形态", blank=True, null=True)

    remarks = models.TextField(verbose_name="备注信息", blank=True, null=True)

    creator = models.ForeignKey(User, verbose_name='创建人', related_name='created_quotations', on_delete=models.SET_NULL,
                                null=True, blank=True)
    quoter = models.ForeignKey(User, verbose_name='报价人', related_name='quoted_quotations', on_delete=models.SET_NULL,
                               null=True, blank=True)
    rejecter = models.ForeignKey(User, verbose_name='驳回人', related_name='rejected_quotations',
                                 on_delete=models.SET_NULL,
                                 null=True, blank=True)
    rejected_reason = models.TextField(verbose_name="驳回理由", blank=True, null=True)
    editor = models.ForeignKey(User, verbose_name='最近编辑人', related_name='editor_quotations', on_delete=models.SET_NULL,
                               null=True, blank=True)

    quotation_content = models.TextField(verbose_name="报价内容", blank=True, null=True)
    calculator_link = models.TextField(verbose_name="计算器链接", blank=True, null=True)

    quotation_list = models.TextField(verbose_name="报价信息", blank=True, null=True)

    edited_at = models.DateTimeField(verbose_name="产品信息编辑时间", blank=True, null=True)
    edited_date = models.DateField(verbose_name="产品信息编辑日期", blank=True, null=True)
    rejected_at = models.DateTimeField(verbose_name="驳回时间", blank=True, null=True)
    quoted_at = models.DateTimeField(verbose_name="报价时间", blank=True, null=True)

    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    created_date = models.DateField(verbose_name='创建日期', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    file_list = GenericRelation(File, related_query_name="lead_quotations")

    class Meta:
        verbose_name = '线索报价'
        ordering = ['-created_at']

    def __str__(self):
        return "线索【】报价需求".format(self.lead.name)

    @property
    def files(self):
        return self.file_list.filter(is_deleted=False).order_by('created_at')


class LeadReportFile(models.Model):
    def generate_filename(self, filename):
        url = "leads/reports/{}-".format(str(time.time()), filename)
        return url

    file = models.FileField(upload_to=generate_filename)
    lead = models.ForeignKey(Lead, verbose_name="线索", on_delete=models.SET_NULL, related_name="report_files",
                             blank=True, null=True)
    title = models.CharField(verbose_name='标题', max_length=50, blank=True, null=True)
    is_active = models.BooleanField(verbose_name='可见状态', default=True)
    author = models.CharField(verbose_name='制作人', max_length=15, blank=True, null=True)
    creator = models.ForeignKey(User, verbose_name='创建人', related_name='create_lead_report_files', blank=True,
                                null=True,
                                on_delete=models.SET_NULL)
    is_public = models.BooleanField(verbose_name='发布状态', default=True)
    published_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = '线索报告文件'
        ordering = ['-published_at']
