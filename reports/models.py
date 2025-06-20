from datetime import timedelta
from bs4 import BeautifulSoup
from copy import deepcopy
import markdown
import re
import json

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import NOT_PROVIDED, DateTimeField, Model
from django.utils import timezone
from taggit.managers import TaggableManager

from gearfarm.utils.common_utils import async_build_obj_ip_address
from comments.models import Comment
from clients.models import Lead
from farmbase.utils import gen_uuid
from proposals.models import Proposal
from logs.models import BrowsingHistory
from reports.diff_report_html import DiffReportHTML
from notifications.tasks import send_report_update_reminder, send_report_new_log
from proposals.models import Industry, ApplicationPlatform, ProductType


class Report(models.Model):
    SOURCE_CHOICES = (
        ('quip_link', 'Quip链接'),
        ('markdown', 'markdown文本'),
        ('farm', 'Farm'),
    )
    TYPE_CHOICES = (
        ('proposal', '需求报告'),
        ('lead', '线索报告'),
    )
    report_type = models.CharField(verbose_name='报告分类', max_length=20, choices=TYPE_CHOICES, default='proposal')
    creation_source = models.CharField(verbose_name='创建来源', max_length=20, choices=SOURCE_CHOICES, default='quip_link')
    proposal = models.ForeignKey(Proposal, verbose_name="需求", on_delete=models.SET_NULL, related_name="reports",
                                 blank=True, null=True)
    lead = models.ForeignKey(Lead, verbose_name="线索", on_delete=models.SET_NULL, related_name="reports",
                             blank=True, null=True)
    is_public = models.BooleanField(verbose_name='发布状态', default=True)
    is_active = models.BooleanField(verbose_name='可见状态', default=True)

    uid = models.CharField(verbose_name='uuid', max_length=30, unique=True)
    title = models.CharField(verbose_name='标题', max_length=50, blank=True, null=True)

    # 需求报告版本信息
    version = models.CharField(verbose_name='当前版本', max_length=10, default='v1.0', blank=True, null=True)
    author = models.CharField(verbose_name='制作人', max_length=15, blank=True, null=True)
    date = models.CharField(verbose_name='制作日期', max_length=25, blank=True, null=True)
    version_content = models.TextField(verbose_name='版本历史', blank=True, null=True)
    # [{"version": '', "date": '', "author": ''}]

    # 线索报告会议沟通信息
    meeting_time = models.DateField(verbose_name="会议时间", blank=True, null=True)
    meeting_place = models.CharField(verbose_name='会议地点', max_length=50, blank=True, null=True)
    meeting_participants = models.TextField(verbose_name='参会人员', blank=True, null=True)
    # [{"company": '公司', "name": '姓名', "position": '职位'， "contact":'联系方式'}]

    # Farm编辑的
    main_content = models.TextField(verbose_name='主要内容', blank=True, null=True)
    main_content_html = models.TextField(verbose_name='主要内容html', blank=True, null=True)
    main_content_text = models.TextField(verbose_name='主要内容文本', blank=True, null=True)

    # markdown文本
    markdown = models.TextField(verbose_name="markdown内容", blank=True, null=True)
    # Quip链接
    html = models.TextField(verbose_name="html内容", blank=True, null=True)

    # 内容简介
    description = models.TextField(verbose_name='描述', blank=True, null=True)

    # 展示项
    show_next = models.BooleanField(verbose_name="下一步", default=True)
    show_services = models.BooleanField(verbose_name="服务范围", default=True)
    show_plan = models.BooleanField(verbose_name="报价方案", default=True)
    # 线索报告展示项
    show_company_about = models.BooleanField(verbose_name="关于我们", default=True)
    show_company_clients = models.BooleanField(verbose_name="我们的客户", default=True)

    industries = models.ManyToManyField(Industry, verbose_name='所属行业', related_name='reports')
    application_platforms = models.ManyToManyField(ApplicationPlatform, verbose_name='应用平台', related_name='reports')
    product_types = models.ManyToManyField(ProductType, verbose_name='产品分类', related_name='reports')

    # 浏览记录
    browsing_histories = GenericRelation(BrowsingHistory, related_query_name="reports")

    creator = models.ForeignKey(User, verbose_name='创建人', related_name='create_reports', blank=True, null=True,
                                on_delete=models.SET_NULL)
    last_operator = models.ForeignKey(User, verbose_name='最近编辑人', related_name='last_edit_reports', blank=True,
                                      null=True, on_delete=models.SET_NULL)

    # 时间点
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    expired_at = models.DateTimeField(verbose_name="过期时间", blank=True, null=True)
    publish_applicant_at = models.DateTimeField(verbose_name="申请审核时间", blank=True, null=True)
    published_at = models.DateTimeField(verbose_name="发布时间", blank=True, null=True)

    publisher = models.ForeignKey(User, verbose_name='发布人', related_name='publish_reports', blank=True,
                                  null=True, on_delete=models.SET_NULL)
    publish_applicant = models.ForeignKey(User, verbose_name='发布申请人', related_name='applicant_publish_reports',
                                          blank=True,
                                          null=True, on_delete=models.SET_NULL)
    publish_applicant_comment = models.TextField(verbose_name='发布申请备注', blank=True, null=True)
    reviewer = models.ForeignKey(User, verbose_name='审核人', related_name='review_reports', blank=True,
                                 null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.title

    @property
    def content_object(self):
        '''
        报告关联的对象   需求或线索
        :return:
        '''
        return self.proposal or self.lead

    def extend_expiration(self, delta=timedelta(days=14)):
        expired_at = timezone.now() + delta
        if self.expired_at != expired_at:
            self.expired_at = expired_at
            self.save()

    @property
    def previous_obj_public_report(self):
        report = None
        if self.proposal:
            report = self.proposal.reports.filter(is_public=True).order_by('-published_at').first()
        elif self.lead:
            report = self.lead.reports.filter(is_public=True).order_by('-published_at').first()
        return report

    def is_expired(self):
        if not self.is_public or not self.expired_at:
            return False
        return self.expired_at < timezone.now()

    def expire_now(self):
        if self.is_public and not self.is_expired():
            self.expired_at = timezone.now()
            self.save()

    # 报告的描述  老数据中
    def update_description(self):
        description = deepcopy(self.description)
        if self.content_object:
            description = self.content_object.description
        elif self.markdown or self.html:
            html = markdown.markdown(self.markdown) if self.markdown else self.html
            p_section = re.compile(r'<h2[\S\s]*?>(?P<title>[\S\s]*?)</h2>(?P<content>[\S\s]*?)(?=<h2)')
            result = p_section.search(html)
            if result:
                content = result.group('content')
                soup = BeautifulSoup(content, "html.parser")
                description = ' '.join(re.sub(r'\s', ' ', soup.get_text()).split())
        if self.description != description:
            self.description = description
            self.save()

    def report_url(self):
        return settings.REPORTS_HOST + reverse('reports:view', args=(self.uid,))

    class Meta:
        verbose_name = '报告'
        ordering = ['-created_at', 'title']
        permissions = (
            ("gear_view_all_reports", "查看全部报告"),
        )


class Grade(models.Model):
    rate = models.IntegerField(verbose_name="分数")
    report = models.ForeignKey('Report', related_name="grades", verbose_name="报告", on_delete=models.CASCADE)
    uid = models.CharField(max_length=100, default='uuid')
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)

    class Meta:
        verbose_name = '报告评分'


class ReportEvaluation(models.Model):
    LEVEL_CHOICES = (
        ('helpful', '很有帮助'),
        ('not_helpful', '没有帮助'),
    )
    report = models.ForeignKey(Report, related_name="evaluations", verbose_name="报告", on_delete=models.CASCADE)
    uid = models.CharField(max_length=100, blank=True, null=True)

    level = models.CharField(verbose_name='评级', max_length=20, choices=LEVEL_CHOICES)
    remarks = models.TextField(verbose_name='备注', blank=True, null=True)

    ip = models.CharField(max_length=100, verbose_name='IP', blank=True, null=True)
    address = models.CharField(max_length=100, verbose_name='地理位置', blank=True, null=True)
    user_agent = models.TextField(verbose_name='浏览器的身份', blank=True, null=True)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    class Meta:
        verbose_name = '报告评价'

    @property
    def remark_list(self):
        if self.remarks:
            return re.sub(r'[;；,，]', ' ', self.remarks).split()

    def build_ip_address(self):
        if self.ip and not self.address:
            async_build_obj_ip_address(self)


class Section:
    def __init__(self):
        self.title = None
        self.content = None
        self.uid = gen_uuid()


class DocRecord:
    def __init__(self):
        self.version = None
        self.date = None
        self.author = None


class Plan:
    def __init__(self):
        self.title = None
        self.items = []
        self.services = None
        self.development = None
        self.duration = None
        self.price = None
        self.price_unit = None


class CommentPoint(models.Model):
    report = models.ForeignKey(Report, related_name="comment_points", verbose_name="局部评论点", on_delete=models.CASCADE)
    uid = models.CharField(max_length=25, unique=True)
    comments = GenericRelation(Comment, related_query_name="report_comment_points")
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = '报告评论点'


class QuotationPlan(models.Model):
    report = models.ForeignKey(Report, related_name="quotation_plans", verbose_name="报告", on_delete=models.CASCADE)
    uid = models.CharField(max_length=25, unique=True)
    title = models.CharField(verbose_name='标题', max_length=50, blank=True, null=True)
    price = models.CharField(verbose_name='报价估算', max_length=50, blank=True, null=True)
    period = models.CharField(verbose_name='预计工期', max_length=50, blank=True, null=True)
    projects = models.CharField(verbose_name='项目包含', max_length=150, blank=True, null=True)
    services = models.CharField(verbose_name='服务范围', max_length=150, blank=True, null=True)
    price_detail = models.TextField(verbose_name="报价详情", blank=True, null=True)
    comment_points = GenericRelation(CommentPoint, related_query_name="report_plan")
    position = models.IntegerField(verbose_name='报价方案编号', default=0)

    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = '项目报价方案'
        ordering = ['created_at']

    def __str__(self):
        return self.title


class FrameDiagramTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = '框架图标签'

    def __str__(self):
        return self.name


class FrameDiagram(models.Model):
    def generate_filename(self, filename):
        url = "reports/frame_diagrams/%s-%s" % (self.uid, filename)
        return url

    uid = models.CharField(max_length=25, unique=True)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='frame_diagrams', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    file = models.ImageField(upload_to=generate_filename)
    filename = models.CharField(verbose_name="文件名称", max_length=128)
    suffix = models.CharField(max_length=20, verbose_name='后缀', blank=True, null=True)
    file_url = models.TextField(verbose_name="文件地址", blank=True, null=True)
    tags = models.ManyToManyField(FrameDiagramTag, related_name='frame_diagrams', verbose_name='类型')
    is_standard = models.BooleanField(verbose_name="标准框架图", default=False)
    is_deleted = models.BooleanField(default=False, verbose_name="是否被删除")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '框架图'

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if not self.suffix:
            self.suffix = self.get_suffix()
        super(FrameDiagram, self).save(*args, **kwargs)

    def get_suffix(self):
        if self.filename and '.' in self.filename:
            return self.filename.rsplit(".", 1)[1]


class MindMap(models.Model):
    def generate_filename(self, filename):
        url = "reports/mind_maps/%s-%s" % (self.uid, filename)
        return url

    uid = models.CharField(max_length=25, unique=True)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='mind_maps', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    file = models.FileField(upload_to=generate_filename)
    filename = models.CharField(verbose_name="文件名称", max_length=128)
    file_url = models.TextField(verbose_name="文件地址", blank=True, null=True)
    json_url = models.TextField(verbose_name="json文件地址", blank=True, null=True)
    image_url = models.TextField(verbose_name="image文件地址", blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '脑图'

    def __str__(self):
        return self.filename


class ReportFile(models.Model):
    def generate_filename(self, filename):
        url = "reports/files/%s-%s" % (self.uid, filename)
        return url

    uid = models.CharField(max_length=25, unique=True)
    submitter = models.ForeignKey(User, verbose_name='提交人', related_name='report_files', blank=True, null=True,
                                  on_delete=models.SET_NULL)
    file = models.FileField(upload_to=generate_filename)
    filename = models.CharField(verbose_name="文件名称", max_length=128)
    suffix = models.CharField(max_length=20, verbose_name='后缀', blank=True, null=True)
    file_url = models.TextField(verbose_name="文件地址", blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '报告文件'

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if not self.suffix:
            self.suffix = self.get_suffix()
        super(ReportFile, self).save(*args, **kwargs)

    def get_suffix(self):
        if self.filename and '.' in self.filename:
            return self.filename.rsplit(".", 1)[1]


class OperatingRecord(models.Model):
    report = models.ForeignKey(Report, related_name="operating_logs", verbose_name="报告", on_delete=models.CASCADE)
    content_data = models.TextField(verbose_name='内容数据', blank=True, null=True)
    operator = models.ForeignKey(
        User,
        verbose_name='操作者',
        related_name='report_logs',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    class Meta:
        verbose_name = '报告操作记录'
        ordering = ['-created_at']

    def __str__(self):
        if self.content_data:
            content_data = json.loads(self.content_data)
            if content_data['subtitle']:
                return content_data['title'] + ':' + content_data['subtitle']
            return content_data['title']

    @classmethod
    def build_create_report_log(cls, operator, report, comment=None, read_only=False, source_report=None):
        if not operator.is_authenticated:
            return None
        subtitle = str(report)
        content_data = {"type": "create", "model_name": 'report', "title": "新建报告", "subtitle": subtitle, "fields": [],
                        "comment": comment}
        if not source_report:
            old_value = ''
            new_value = report.main_content_text
            new_html = new_value if new_value else ''
            if re.sub(r'\s+', '', new_html):
                diff_html_parser = DiffReportHTML(old_value, new_value)
                diff_html = diff_html_parser.build_diff_html()
                if diff_html:
                    html_op_data = {"type": "insert", "name": "main_content_html", "verbose_name": "报告内容",
                                    "old_value": old_value,
                                    "new_value": new_value,
                                    "diff_result": diff_html}
                    content_data["fields"].append(html_op_data)
        return cls.build_log(operator, content_data, report, read_only=read_only, is_created=True)

    @classmethod
    def build_update_report_log(cls, operator, origin_data, updated_data, report, comment=None, read_only=False,
                                request=None):
        if not operator.is_authenticated:
            return None
        subtitle = str(report)
        content_data = {"type": "update", "model_name": 'report', "title": '编辑报告', "subtitle": subtitle, "fields": [],
                        "comment": comment}

        if report.report_type == 'proposal':
            editable_fields = (
                "title", "version_content", "main_content_html", "quotation_plans", "show_next", "show_services",
                "show_plan", "main_content_text")
        else:
            editable_fields = (
                "title", "meeting_time", "meeting_place", "meeting_participants", "main_content_html",
                "main_content_text", "show_plan", "quotation_plans", "show_company_about",
                "show_company_clients",)

        fields = report._meta.get_fields()
        field_dict = {}
        for field in fields:
            if hasattr(field, 'verbose_name'):
                field_dict[field.name] = field.verbose_name
        for name in editable_fields:
            if name == 'quotation_plans':
                verbose_name = "报价方案"
            else:
                verbose_name = field_dict[name] if name in field_dict else name
            old_value = origin_data[name] if name in origin_data else None
            new_value = updated_data[name] if name in updated_data else None
            if old_value != new_value:
                if name == 'quotation_plans':
                    plans_diff = build_plans_log_data(old_value, new_value)
                    for plan in plans_diff['insert']:
                        op_data = {"type": "insert", "name": "quotation_plan", "verbose_name": verbose_name,
                                   "value": plan}
                        content_data["fields"].append(op_data)
                    for plan in plans_diff['delete']:
                        op_data = {"type": "delete", "name": "quotation_plan", "verbose_name": verbose_name,
                                   "value": plan}
                        content_data["fields"].append(op_data)
                    for plan in plans_diff['update']:
                        op_data = {"type": "update", "name": "quotation_plan", "verbose_name": verbose_name,
                                   "old_value": plan["old_value"],
                                   "new_value": plan["new_value"]}
                        content_data["fields"].append(op_data)

                elif name == 'meeting_participants':
                    old_value_str = get_meeting_participants_text(old_value)
                    new_value_str = get_meeting_participants_text(new_value)
                    op_data = {"type": "update", "name": name, "verbose_name": verbose_name,
                               "old_value": old_value_str,
                               "new_value": new_value_str}
                    content_data["fields"].append(op_data)
                elif name == 'main_content_text':
                    # 文本
                    old_html = old_value if old_value else ''
                    new_html = new_value if new_value else ''
                    if re.sub(r'\r|\n|\s', '', new_html) == re.sub(r'\r|\n|\s', '', old_html):
                        continue
                    diff_html_parser = DiffReportHTML(old_value, new_value, )
                    diff_html = diff_html_parser.build_diff_html()
                    if diff_html:
                        html_op_data = {"type": "update", "name": "main_content_html", "verbose_name": "报告内容",
                                        "old_value": old_html,
                                        "new_value": new_html,
                                        "diff_result": diff_html}
                        content_data["fields"].append(html_op_data)
                elif name == 'main_content_html':
                    # 图片
                    old_html = old_value if old_value else ''
                    new_html = new_value if new_value else ''
                    old_html = re.sub(r'<p>[\s]*(<br[/]?>)?[\s]*</p>', '', old_html).strip()
                    new_html = re.sub(r'<p>[\s]*(<br[/]?>)?[\s]*</p>', '', new_html).strip()
                    if re.sub(r'\s+', '', new_html) == re.sub(r'\s+', '', old_html):
                        continue
                    diff_html_parser = DiffReportHTML(old_value, new_value)
                    diff_images = diff_html_parser.build_diff_images()
                    for image in diff_images['insert']:
                        op_data = {"type": "insert", "name": "image", "verbose_name": "图片",
                                   "value": image}
                        content_data["fields"].append(op_data)
                    for image in diff_images['delete']:
                        op_data = {"type": "delete", "name": "image", "verbose_name": "图片",
                                   "value": image}
                        content_data["fields"].append(op_data)
                else:
                    op_data = {"type": "update", "name": name, "verbose_name": verbose_name,
                               "old_value": old_value,
                               "new_value": new_value}
                    content_data["fields"].append(op_data)
        if content_data["fields"]:
            page_view_uuid = None
            if request:
                page_view_uuid = request.data.get('page_view_uuid', None)
            send_report_update_reminder.delay(report.id, operator.id, page_view_uuid=page_view_uuid)
            return cls.build_log(operator, content_data, report, read_only=read_only)

    @classmethod
    def build_log(cls, operator, content_data, report, read_only=False, is_created=False):
        content_data = json.dumps(content_data, ensure_ascii=False)
        log = cls(operator=operator, report=report, content_data=content_data)
        if not read_only:
            log.save()
        if not read_only and not is_created:
            send_report_new_log.delay(report.id)
        return log


def get_meeting_participants_text(meeting_participants):
    # [{"company": '公司', "name": '姓名', "position": '职位'， "contact":'联系方式'}]
    result_text = ''
    for item in meeting_participants:
        item_str = "{company} {name} {position} {contact}\n".format(
            company=item['company'], name=item['name'], position=item['position'], contact=item['contact']
        )
        result_text += item_str
    return result_text


def build_plans_log_data(old_plans, plans):
    diff_plans = {'insert': [], 'delete': [], 'update': []}
    old_plan_dict = {}
    plan_dict = {}
    if old_plans:
        for plan in old_plans:
            old_plan_dict[plan['id']] = clean_plan_data(plan)
    if plans:
        for plan in plans:
            plan_dict[plan['id']] = clean_plan_data(plan)
    plan_keys = plan_dict.keys()
    old_plan_keys = old_plan_dict.keys()
    for plan_key in plan_keys:
        if plan_key not in old_plan_keys:
            diff_plans['insert'].append(plan_dict[plan_key])
        elif plan_dict[plan_key] != old_plan_dict[plan_key]:
            update_data = {'old_value': old_plan_dict[plan_key], 'new_value': plan_dict[plan_key]}
            diff_plans['update'].append(update_data)
    for plan_key in old_plan_keys:
        if plan_key not in plan_keys:
            diff_plans['delete'].append(old_plan_dict[plan_key])
    return diff_plans


def clean_plan_data(data):
    plan_fields = ('id', 'uid', 'title', 'price', 'period', 'projects', 'services')
    plan_data = {}
    for field in plan_fields:
        plan_data[field] = data[field]
    return plan_data


class RevisionHistory(models.Model):
    report = models.ForeignKey(Report, related_name="histories", verbose_name="报告", on_delete=models.CASCADE)
    author = models.ForeignKey(
        User,
        verbose_name='制作人',
        related_name="report_histories",
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    report_data = models.TextField(verbose_name='报告数据', blank=True, null=True)
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    number = models.IntegerField(verbose_name="编号", default=1)
    remarks = models.CharField(verbose_name='备注', max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = '历史版本'

    def __str__(self):
        return self.report.title
