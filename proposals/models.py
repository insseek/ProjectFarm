from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Sum, IntegerField, When, Case, Q
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import reverse
from django.utils import timezone
from multiselectfield import MultiSelectField

from comments.models import Comment
from files.models import File
from logs.models import Log
from playbook.models import ChecklistItem, InfoItem, Stage
from projects.models import Project
from tasks.models import Task
from gearfarm.utils.const import LEAD_STATUS
from clients.models import Lead, LeadIndividual, LeadOrganization, LeadSource
from gearfarm.utils.page_path_utils import build_page_path


class Proposal(models.Model):
    RELIABILITY_CHOICES = (
        ('low', '低'),
        ('general', '普通'),
        ('major', '重点'),
    )
    STATUS = (
        (1, '等待认领'),
        (2, '等待沟通'),
        # (3, '等待报告'),
        (4, '进行中'),
        (5, '商机'),
        (6, '成单交接'),
        (10, '成单'),
        (11, '未成单'),
    )

    PROPOSAL_STATUS_DICT = {
        'pending': {'index': 0, 'code': 'pending', 'name': '等待认领', "status": 1},
        'contact': {'index': 1, 'code': 'contact', 'name': '等待沟通', "status": 2},
        'ongoing': {'index': 2, 'code': 'ongoing', 'name': '进行中', "status": 4},
        'biz_opp': {'index': 3, 'code': 'biz_opp', 'name': '商机', "status": 5},
        'contract': {'index': 4, 'code': 'contract', 'name': '成单交接', "status": 6},
        'deal': {'index': 5, 'code': 'deal', 'name': '成单', "status": 10},
        'no_deal': {'index': 6, 'code': 'no_deal', 'name': '未成单', "status": 11},
    }

    PROPOSAL_STATUS = (
        ('pending', '等待认领'),
        ('contact', '等待沟通'),
        ('ongoing', '进行中'),
        ('biz_opp', '商机'),
        ('contract', '成单交接'),
        ('deal', '成单'),
        ('no_deal', '未成单'),
    )

    CLOSED_REASON = (
        (1, '其它'),
        (2, '无响应'),
        (3, '暂时不做'),
        (4, '选择其它家'),
        (5, '无效需求（不靠谱）'),
    )
    QUIP_FOLDER_TYPES = (
        ('auto', '自动创建'),
        ('select', '选择'),
        ('no_need', '不需要'),
    )
    BUDGET_UNITS = (
        ('元', '元'),
        ('万', '万'),
    )
    project = models.OneToOneField(Project, verbose_name='项目', related_name='proposal', blank=True, null=True,
                                   on_delete=models.SET_NULL)
    lead = models.OneToOneField(Lead, verbose_name='线索', related_name='proposal', blank=True, null=True,
                                on_delete=models.SET_NULL)

    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_proposals', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    pm = models.ForeignKey(User, verbose_name='产品经理', related_name='pm_proposals', blank=True, null=True,
                           on_delete=models.SET_NULL)
    bd = models.ForeignKey(User, verbose_name='BD', related_name='bd_proposals', blank=True, null=True,
                           on_delete=models.SET_NULL)
    lead_source = models.OneToOneField(LeadSource, verbose_name='线索来源数据', related_name='proposal',
                                       on_delete=models.SET_NULL,
                                       null=True, blank=True)
    status = models.IntegerField(verbose_name="需求状态", choices=STATUS, default=1)
    name = models.CharField(verbose_name="需求名称", max_length=50, blank=True, null=True)
    description = models.TextField(verbose_name='需求描述')
    industries = models.ManyToManyField('proposals.Industry', verbose_name='所属行业', related_name='proposals')
    application_platforms = models.ManyToManyField('proposals.ApplicationPlatform', verbose_name='应用平台',
                                                   related_name='proposals')
    business_objective = models.TextField(verbose_name="业务目标", blank=True, null=True)
    REBATE_CHOICES = (
        ('0', '渠道介绍，需要分成'),
        ('1', '内部成员，但需要返点'),
        ('2', '不需要返点'),
    )
    rebate = models.CharField(verbose_name="返点", max_length=2, choices=REBATE_CHOICES, default='2')
    rebate_info = models.CharField(verbose_name="返点信息", max_length=64, blank=True, null=True)
    period = models.TextField(verbose_name="时间规划", blank=True, null=True)

    MATERIALS = (
        ('1', 'BP/PPT版介绍'),
        ('2', '功能列表/思维导图'),
        ('3', '原型'),
        ('4', '设计稿'),
        ('5', '已有产品'),
        ('9', '其他'),
    )
    available_material = MultiSelectField(verbose_name="需求资料", choices=MATERIALS, blank=True, null=True)
    material_remarks = models.TextField(verbose_name="需求资料备注", blank=True, null=True)

    REFERENCES = (
        ('0', '参考全部'),
        ('1', '参考部分页面/流程'),
        ('2', '其他'),
        ('3', '无'),
    )
    reference = models.CharField(verbose_name="竞品参考", max_length=2, choices=REFERENCES, blank=True, null=True)
    reference_remarks = models.TextField(verbose_name="竞品参考备注", blank=True, null=True)

    RIGID_REQUIREMENTS = (
        ('1', '代码规范和代码语言要求'),
        ('2', '价格上限'),
        ('3', '明确的上线时间'),
        ('9', '其他'),
    )

    rigid_requirement = MultiSelectField(verbose_name="硬性要求", choices=RIGID_REQUIREMENTS, blank=True, null=True)
    rigid_requirement_remarks = models.CharField(verbose_name="硬性要求备注", max_length=96, blank=True, null=True)

    remarks = models.TextField(verbose_name='提交人备注', blank=True, null=True)
    reliability = models.CharField(verbose_name="靠谱度", max_length=15, choices=RELIABILITY_CHOICES, default='general')

    budget = models.CharField(verbose_name="预算", max_length=15, blank=True, null=True)
    budget_unit = models.CharField(verbose_name="预算 单位", max_length=2, choices=BUDGET_UNITS,
                                   default="元", blank=True, null=True)
    decision_time = models.DateField(verbose_name='决策时间', blank=True, null=True)
    decision_makers = models.CharField(verbose_name="决策层", max_length=100, blank=True, null=True)
    decision_email = models.CharField(verbose_name="决策层邮箱", max_length=100, blank=True, null=True)
    biz_opp_created_at = models.DateTimeField(verbose_name="商机创建时间", blank=True, null=True)

    closed_reason = models.IntegerField(verbose_name="未成单原因", choices=CLOSED_REASON, blank=True, null=True)
    closed_reason_comment = models.TextField(verbose_name="未成单理由文本", blank=True, null=True)

    closed_reason_text = models.TextField(verbose_name="未成单原因", blank=True, null=True)
    closed_reason_remarks = models.TextField(verbose_name="未成单原因备注", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')
    assigned_at = models.DateTimeField(verbose_name='认领时间', blank=True, null=True)
    contact_at = models.DateTimeField(verbose_name='联系时间', blank=True, null=True)
    report_at = models.DateTimeField(verbose_name='报告时间', blank=True, null=True)
    closed_at = models.DateTimeField(verbose_name='关闭时间', blank=True, null=True)

    quip_folder_type = models.CharField(verbose_name="Quip文件夹类别", max_length=30, choices=QUIP_FOLDER_TYPES,
                                        default="no_need")
    quip_folder_id = models.CharField(verbose_name="Quip文件夹ID", max_length=30, blank=True, null=True)
    quip_doc_id = models.CharField(verbose_name="Quip沟通文档ID", max_length=30, blank=True, null=True)

    file_list = GenericRelation(File, related_query_name="proposals")
    comments = GenericRelation(Comment, related_query_name="proposals")
    tasks = GenericRelation(Task, related_query_name="proposals")
    logs = GenericRelation(Log, related_query_name="proposals")
    playbook_stages = GenericRelation(Stage, related_query_name="proposals")
    auto_tasks = GenericRelation(Task, object_id_field='source_id', content_type_field='source_type')

    def save(self, *args, **kwargs):
        if self.project_id and not self.status != self.PROPOSAL_STATUS_DICT['deal']['status']:
            self.closed_at = timezone.now()
            self.status = self.PROPOSAL_STATUS_DICT['deal']['status']
            if self.lead:
                self.lead.status = LEAD_STATUS['deal'][0]
                self.lead.proposal_closed_at = timezone.now()
                self.lead.save()
        if self.status >= self.PROPOSAL_STATUS_DICT['deal']['status'] and not self.closed_at:
            self.closed_at = timezone.now()
        super(Proposal, self).save(*args, **kwargs)

    def close_and_create_project(self, project, to_save=True):
        if project:
            self.closed_at = timezone.now()
            self.status = self.PROPOSAL_STATUS_DICT['deal']['status']
            self.project = project
            self.save()
            if self.lead:
                self.lead.status = LEAD_STATUS['deal'][0]
                self.lead.proposal_closed_at = timezone.now()
                self.lead.save()

    @property
    def participants(self):
        return [self.pm, self.bd]

    @classmethod
    def get_status_index_by_code(cls, stage_code):
        if stage_code and stage_code in cls.PROPOSAL_STATUS_DICT:
            return cls.PROPOSAL_STATUS_DICT[stage_code]['index']

    @property
    def product_manager(self):
        return self.pm

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def stage_code(self):
        return self.get_status_display()

    @property
    def files(self):
        return self.file_list.filter(is_deleted=False).order_by('created_at')

    @property
    def status_index(self):
        return self.status

    @property
    def stage_index(self):
        return self.status

    @property
    def source_display(self):
        if self.lead_source:
            return self.lead_source.source_type_display

    def undone_tasks(self):
        tasks = self.tasks.filter(is_done=False).order_by('expected_at')
        return tasks

    @property
    def quip_folder(self):
        if self.quip_folder_id:
            return "https://quip.com/" + self.quip_folder_id
        else:
            return None

    def quip_folder_data(self):
        if self.quip_folder_id:
            title = "【{id}】{name}".format(id=self.id, name=self.name)
            return {"title": title, 'id': self.quip_folder_id, 'link': "https://quip.com/" + self.quip_folder_id}
        else:
            return None

    def quip_doc(self):
        if self.quip_doc_id:
            return "https://quip.com/" + self.quip_doc_id
        else:
            return None

    @property
    def title(self):
        if not self.name:
            if self.description:
                name = ' '.join(self.description[:10].splitlines())
            else:
                name = "需求【{}】".format(self.id)
            self.name = name
            self.save()
        return self.name

    def latest_report_data(self):
        reports = self.reports.filter(is_public=True).order_by('-published_at')
        if reports.exists():
            latest_report = reports.first()
            title = latest_report.title
            version = latest_report.version
            author = latest_report.author
            created_at = latest_report.created_at.strftime(settings.DATETIME_FORMAT)

            report_url = settings.REPORTS_HOST + reverse('reports:view', args=(latest_report.uid,))
            report_preview_url = reverse('reports:preview', args=(latest_report.uid,))
            return {"title": title, 'version': version, "report_url": report_url, "author": author,
                    "created_at": created_at, 'report_preview_url': report_preview_url,
                    "published_at": latest_report.published_at,
                    'is_expired': latest_report.is_expired()}

    @classmethod
    def waiting_assigned_proposals(cls):
        return cls.objects.filter(status=cls.PROPOSAL_STATUS_DICT['pending']['status'])

    @classmethod
    def waiting_contact_proposals(cls):
        return cls.objects.filter(status=cls.PROPOSAL_STATUS_DICT['contact']['status'])

    @classmethod
    def ongoing_proposals(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(status__lt=cls.PROPOSAL_STATUS_DICT['deal']['status'])

    @classmethod
    def closed_proposals(cls, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(status__gte=cls.PROPOSAL_STATUS_DICT['deal']['status'])

    @classmethod
    def user_proposals(cls, user, queryset=None):
        queryset = cls.objects.all() if queryset is None else queryset
        return queryset.filter(Q(pm_id=user.id) | Q(bd_id=user.id))

    @classmethod
    def no_deal_proposals(cls):
        return cls.objects.filter(status=cls.PROPOSAL_STATUS_DICT['no_deal']['status'])

    @classmethod
    def deal_proposals(cls):
        return cls.objects.filter(status=cls.PROPOSAL_STATUS_DICT['deal']['status'])

    @classmethod
    def waiting_deal_proposals(cls):
        # 状态在等待沟通与成单之间的进行中需求
        proposal_ongoing_status = cls.PROPOSAL_STATUS_DICT['ongoing']['status']
        proposal_deal_status = cls.PROPOSAL_STATUS_DICT['deal']['status']
        return cls.objects.filter(status__gte=proposal_ongoing_status,
                                  status__lt=proposal_deal_status).all()

    def __str__(self):
        return self.name or ' '.join(self.description[:10].splitlines())

    class Meta:
        verbose_name = '需求'
        permissions = (
            ("gear_view_all_proposals", "查看全部需求"),
            ("gear_view_ongoing_proposals", "查看进行中的需求"),
            ("gear_view_proposals_finished_in_90_days", "查看最近90天内结束的需求"),
            ("gear_view_calculator", "查看计算器"),
            ("gear_view_playbook", "查看需求playbook"),
        )


class HandoverReceipt(models.Model):
    INVOICE_TYPES = (
        ('plain', '增值税普票'),
        ('special', '增值税专票'),
    )
    INVOICE_MODES = (
        ('invoice_first', '先票后款'),
        ('payment_first', '先款后票'),
    )
    OP_INVOICE_MODES = (
        ('invoice_first', '先票后款'),
        ('payment_first', '先款后票'),
    )
    OP_PAYMENT_MODES = (
        ('monthly', '按月'),
        ('quarterly', '按季度'),
        ('yearly', '按年'),
    )
    OP_INVOICE_TYPES = (
        ('plain', '增值税普票'),
        ('special', '增值税专票'),
    )
    INVOICE_PERIODS = (
        ('one-off', '所有款项金额统一开票'),
        ('periodic', '一期一开'),
    )
    proposal = models.OneToOneField(Proposal, verbose_name='需求', related_name='handover_receipt',
                                    on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='submitted_handover_receipts', blank=True,
                                  null=True, on_delete=models.SET_NULL)

    invoice_type = models.CharField(verbose_name="开票类型", max_length=20, choices=INVOICE_TYPES)
    invoice_mode = models.CharField(verbose_name="开票方式", max_length=20, choices=INVOICE_MODES)
    invoice_period = models.CharField(verbose_name="开票周期", max_length=20, choices=INVOICE_PERIODS)
    invoice_info = models.TextField(verbose_name="开票信息")

    addressee_name = models.CharField(verbose_name="邮寄收件人姓名", max_length=20)
    addressee_phone_number = models.CharField(verbose_name="邮寄收件人联系方式", max_length=30)
    addressee_address = models.CharField(verbose_name="邮寄收件人地址", max_length=150)

    has_referral_fee = models.BooleanField(verbose_name="介绍费", default=False)
    referral_fee_rebate = models.IntegerField(verbose_name="介绍费返点总额(元）", blank=True, null=True)

    has_marketing_plan = models.BooleanField(verbose_name="项目市场安排", default=False)
    marketing_plan_info = models.TextField(verbose_name="市场安排信息", blank=True, null=True)

    maintenance_period = models.IntegerField(verbose_name="项目维护期/月")

    need_op_service = models.BooleanField(verbose_name="运维服务", default=False)
    op_period = models.IntegerField(verbose_name="运维周期/月", blank=True, null=True)
    op_service_charge = models.IntegerField(verbose_name="运维服务费总金额(元）", blank=True, null=True)
    # op_invoice_type = models.CharField(verbose_name="运维开票类型", max_length=1, choices=OP_INVOICE_TYPES, blank=True,
    #                                    null=True)
    op_invoice_mode = models.CharField(verbose_name="运维开票方式", max_length=20, choices=OP_INVOICE_MODES, blank=True,
                                       null=True)
    op_payment_mode = models.CharField(verbose_name="运维支付类型", max_length=20, choices=OP_PAYMENT_MODES, blank=True,
                                       null=True)

    project_background = models.TextField(verbose_name="项目背景")

    created_at = models.DateTimeField(verbose_name='提交时间', auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    class Meta:
        verbose_name = '交接清单'

    def __str__(self):
        title = '交接清单'
        if self.proposal:
            title = '需求【{}】{}的交接清单'.format(self.proposal.id, self.proposal.name if self.proposal.name else '')
        return title


class Industry(models.Model):
    INIT_DATA = [
        {'name': '金融'},
        {'name': '教育'},
        {'name': '文化'},
        {'name': '休闲娱乐'},
        {'name': '媒体'},
        {'name': '法律'},
        {'name': '零售'},
        {'name': '工业/制造业'},
        {'name': '生活服务'},
        {'name': '餐饮'},
        {'name': '酒店'},
        {'name': '旅游'},
        {'name': '服装/服饰'},
        {'name': '体育'},
        {'name': '医疗/健康'},
        {'name': '美容/美发'},
        {'name': '房产/家居'},
        {'name': '家政/维修'},
        {'name': '婚庆/摄影'},
        {'name': '婚恋'},
        {'name': '宠物'},
        {'name': '共享服务'},
        {'name': '汽车'},
        {'name': '出行'},
        {'name': '物流运输'},
        {'name': '建筑/工程'},
        {'name': '通讯电子'},
        {'name': '光伏'},
        {'name': '农林牧渔'},
        {'name': '企业服务'},
        {'name': '咨询'},
        {'name': '广告营销'},
        {'name': '软件开发'},
        {'name': '设计'},
        {'name': '信息安全'},
        {'name': '物联网'},
        {'name': '人工智能'},
        {'name': '区块链'},
        {'name': 'AR/VR'},
        {'name': '电商'},
        {'name': '社交'},
        {'name': '游戏'},
        {'name': '其他'}
    ]
    name = models.CharField(verbose_name='名称', max_length=50, unique=True)
    index = models.IntegerField(verbose_name='排序位置', default=0)

    class Meta:
        verbose_name = '行业类型'

    def __str__(self):
        return self.name


class ApplicationPlatform(models.Model):
    INIT_DATA = [
        {'name': 'iOS'},
        {'name': 'iPad'},
        {'name': 'Android'},
        {'name': 'Android Pad'},
        {'name': 'Web'},
        {'name': 'H5'},
        {'name': '小程序'},
        {'name': '公众号'},
        {'name': '管理后台'},
        {'name': 'SDK'}
    ]
    name = models.CharField(max_length=50, unique=True)
    index = models.IntegerField(verbose_name='排序位置', default=0)

    class Meta:
        verbose_name = '应用平台'

    def __str__(self):
        return self.name


class ProductType(models.Model):
    INIT_DATA = [
        {
            "name": "电商",
            "children": [
                {"name": "B2B"},
                {"name": "B2C"},
                {"name": "B2B2C"},
                {"name": "C2C"},
                {"name": "O2O"},
                {"name": "标准电商"},
                {"name": "团购"},
                {"name": "一元购"},
                {"name": "优惠券"},

            ]
        },
        {
            "name": "社交",
            "children": [
                {"name": "社交"},
                {"name": "社区"},
                {"name": "社群"}
            ]
        },
        {
            "name": "CMS",
            "children": [
                {"name": "官网"},
                {"name": "PGC"},
                {"name": "图文"},
                {"name": "音视频"},
                {"name": "点播"},
                {"name": "直播"},

            ]
        },
        {
            "name": "软硬件",
            "children": [
                {"name": "设备监控"},
                {"name": "硬件控制"},
            ]
        },
        {
            "name": "企业营销",
            "children": [
                {"name": "会员服务"},
                {"name": "营销工具"},
                {"name": "分销系统"},
            ]
        },
        {
            "name": "企业信息化",
            "children": [
                {"name": "CRM"},
                {"name": "ERP"},
                {"name": "OA"},
                {"name": "工单"},
                {"name": "经销商管理"},
                {"name": "供应链管理"},

            ]
        },
        {
            "name": "数据处理",
            "children": [
                {"name": "数据统计"},
                {"name": "爬虫"},
                {"name": "数据清洗"},
                {"name": "数据标注"}
            ]
        },
        {
            "name": "工具",
            "children": [
                {"name": "互动直播"},
                {"name": "视频会议"},

            ]
        },
        {
            "name": "SaaS",
            "children": [

            ]
        },
        {
            "name": "游戏",
            "children": [

            ]
        },
        {
            "name": "其他",
            "children": [

            ]
        }
    ]
    parent = models.ForeignKey(to='self', verbose_name='父级类型', related_name='children', null=True, blank=True,
                               on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    index = models.IntegerField(verbose_name='排序位置', default=0)

    class Meta:
        verbose_name = '产品类型'
        unique_together = ('parent', 'name')

    def __str__(self):
        return self.name
