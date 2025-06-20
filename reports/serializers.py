import json
from collections import Counter

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers
from taggit.models import Tag

from clients.models import Lead
from comments.serializers import CommentSerializer
from farmbase.serializers import UserField
from proposals.models import Proposal, Industry, ApplicationPlatform, ProductType
from reports.models import Report, FrameDiagramTag, FrameDiagram, MindMap, \
    ReportFile, QuotationPlan, CommentPoint, RevisionHistory, OperatingRecord, ReportEvaluation


class TagField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        tag = Tag.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": tag.name}
        return dict


class ProposalField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = Proposal.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": proposal.name, "description": proposal.description}
        return dict


class ProposalSimpleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = Proposal.objects.get(pk=value.pk)
        title = proposal.name if proposal.name else '需求【{}】'.format(proposal.id)

        rebate_info = proposal.rebate_info if proposal.rebate in ['0', '1'] and proposal.rebate_info else ''
        data = {"id": value.pk, "name": title, "rebate_info": rebate_info}
        return data


def build_proposal_filed_data(obj):
    if obj:
        data = {"id": obj.id, "name": obj.name, "description": obj.description}
        for member_name in ['pm', 'bd']:
            member = getattr(obj, member_name, None)
            member_data = None
            if member:
                member_data = {'id': member.id, 'username': member.username}
            data[member_name] = member_data
        return data


def build_lead_filed_data(obj):
    if obj:
        data = {"id": obj.id, "name": obj.name, "description": obj.description}
        for member_name in ['creator', 'salesman']:
            member = getattr(obj, member_name, None)
            member_data = None
            if member:
                member_data = {'id': member.id, 'username': member.username}
            data[member_name] = member_data
        return data


class LeadField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        lead = Lead.objects.get(pk=value.pk)
        return build_lead_filed_data(lead)


class LeadSimpleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        lead = Lead.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": lead.name}
        return dict


class ProductTypeField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = ProductType.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": obj.name}
        return dict


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = '__all__'


class ApplicationPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationPlatform
        fields = '__all__'


class ProductTypeSerializer(serializers.ModelSerializer):
    parent = ProductTypeField(many=False, read_only=True)

    class Meta:
        model = ProductType
        fields = '__all__'


class ProductTypeWithChildrenSerializer(serializers.ModelSerializer):
    children = ProductTypeSerializer(many=True, read_only=True)

    class Meta:
        model = ProductType
        fields = '__all__'


class ReportPageSerializer(serializers.ModelSerializer):
    description = serializers.CharField()
    industries = IndustrySerializer(many=True, read_only=True)
    application_platforms = ApplicationPlatformSerializer(many=True, read_only=True)
    product_types = ProductTypeSerializer(many=True, read_only=True)
    evaluations_statistics = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ('id', 'title', 'description', 'uid', 'version', 'author',
                  'industries', 'application_platforms', 'product_types',
                  'created_at', 'expired_at', 'published_at',
                  'creation_source',
                  "evaluations_statistics")

    def get_evaluations_statistics(self, obj):
        levels = obj.evaluations.values_list('level', flat=True)
        return dict(Counter(levels))


class ProposalReportListSerializer(serializers.ModelSerializer):
    proposal = ProposalField(many=False, queryset=Proposal.objects.all())
    is_expired = serializers.BooleanField()
    report_url = serializers.CharField(read_only=True)
    creation_source_display = serializers.SerializerMethodField(read_only=True)
    publisher = UserField(many=False, queryset=User.objects.all())
    reviewer = UserField(many=False, queryset=User.objects.all())
    evaluations_statistics = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = (
            'id', 'title', 'uid', 'version', 'report_url', 'author', 'proposal', 'created_at', 'expired_at',
            'is_expired', 'is_public', 'published_at', 'creation_source_display', 'creation_source', 'updated_at',
            'reviewer', 'publisher', 'evaluations_statistics')

    def get_creation_source_display(self, obj):
        return obj.get_creation_source_display()

    def get_evaluations_statistics(self, obj):
        levels = obj.evaluations.values_list('level', flat=True)
        return dict(Counter(levels))


class ReportReviewerSerializer(serializers.ModelSerializer):
    reviewer = UserField(many=False, queryset=User.objects.all(), required=True)
    publish_applicant = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = Report
        fields = ('reviewer', 'publish_applicant', 'publish_applicant_comment', 'publish_applicant_at')


class FrameDiagramTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FrameDiagramTag
        fields = '__all__'


class FrameDiagramSerializer(serializers.ModelSerializer):
    tags = FrameDiagramTagSerializer(many=True, read_only=True)

    class Meta:
        model = FrameDiagram
        fields = '__all__'


class MindMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = MindMap
        fields = '__all__'


class ReportFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportFile
        fields = '__all__'


class RevisionHistoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevisionHistory
        fields = '__all__'


class RevisionHistoryDetailSerializer(serializers.ModelSerializer):
    author = UserField(many=False, read_only=True)
    report_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RevisionHistory
        fields = '__all__'

    def get_report_data(self, obj):
        if obj.report_data:
            return json.loads(obj.report_data, encoding='utf-8')


class OperatingRecordDetailSerializer(serializers.ModelSerializer):
    operator = UserField(many=False, read_only=True)
    content_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OperatingRecord
        fields = '__all__'

    def get_content_data(self, obj):
        if obj.content_data:
            return json.loads(obj.content_data, encoding='utf-8')


class ReportCreateSerializer(serializers.ModelSerializer):
    proposal = ProposalField(many=False, queryset=Proposal.objects.all())
    title = serializers.CharField()

    class Meta:
        model = Report
        fields = ['uid', 'creation_source', 'report_type', 'proposal', 'title', 'is_public', 'author', 'date',
                  'version',
                  'version_content', 'last_operator', 'creator', 'main_content', 'main_content_html',
                  'main_content_text']


class LeadReportCreateSerializer(serializers.ModelSerializer):
    lead = LeadField(many=False, queryset=Lead.objects.all())
    title = serializers.CharField()

    class Meta:
        model = Report
        fields = ['uid', 'creation_source', 'report_type', 'lead', 'title', 'is_public', 'author', 'creator',
                  'last_operator', 'show_plan',
                  'meeting_participants', 'main_content', 'main_content_html',
                  'main_content_text']


class ReportCopySerializer(serializers.ModelSerializer):
    proposal = ProposalField(many=False, queryset=Proposal.objects.all())
    title = serializers.CharField()

    class Meta:
        model = Report
        fields = '__all__'


class ReportEditSerializer(serializers.ModelSerializer):
    last_operator = UserField(many=False, queryset=User.objects.all())
    version_content = serializers.CharField(allow_null=True, required=False)
    author = serializers.CharField(allow_null=True, required=False)
    date = serializers.CharField(allow_null=True, required=False)
    version = serializers.CharField(allow_null=True, required=False)
    meeting_participants = serializers.CharField(allow_null=True, required=False)
    meeting_time = serializers.DateField(allow_null=True, required=False)
    meeting_place = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = Report
        fields = ["title", 'author', 'date', 'version', "version_content", "main_content", "main_content_html",
                  "main_content_text",
                  "show_next", "show_services",
                  "show_plan", 'last_operator', 'meeting_participants', "meeting_time", "meeting_place",
                  "show_company_about",
                  "show_company_clients"
                  ]


class ReportCommentPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentPoint
        fields = '__all__'


class ReportCommentPointWithCommentsSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = CommentPoint
        fields = '__all__'


class QuotationPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotationPlan
        fields = '__all__'


class QuotationPlanDetailSerializer(serializers.ModelSerializer):
    price_detail = serializers.SerializerMethodField(read_only=True)
    comment_points = ReportCommentPointSerializer(many=True, read_only=True)
    projects_list = serializers.SerializerMethodField(read_only=True)
    services_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QuotationPlan
        fields = '__all__'

    def get_projects_list(self, obj):
        data = []
        if obj.projects:
            data = [i for i in obj.projects.split('+') if i]
        return data

    def get_services_list(self, obj):
        data = []
        if obj.services:
            data = [i for i in obj.services.split('+') if i]
        return data

    def get_price_detail(self, obj):
        if obj.price_detail:
            price_detail = json.loads(obj.price_detail, encoding='utf-8')
            # 总报价
            sum_num = 0
            # 个人所得税
            tax_num = 0
            # 固定成本
            cost = price_detail['cost']
            # 齿轮提成
            deduction_num = 0
            # 介绍费
            referral_num = 0
            sum_tax_num = 0
            if price_detail:
                # 税前总金额
                tax_sum_num = 0
                for item in price_detail['listData']:
                    tax_sum_num += round(item['cost'] / 4.3 * item['time'])
                # 交税金额
                tax_num = round(tax_sum_num * (price_detail['tax'] / (100 - price_detail['tax'])))

                # 齿轮提成前总金额
                deduction_sum_num = tax_sum_num + tax_num + price_detail['cost']
                # 齿轮提成
                deduction_num = round(
                    deduction_sum_num * (price_detail['deduction'] / (100 - price_detail['deduction'])))

                # 介绍费基数总金额
                referral_sum_num = deduction_num + deduction_sum_num
                # 介绍费
                referral_num = round(referral_sum_num * (price_detail['referral'] / (100 - price_detail['referral'])))

                # 税前总金额
                no_tax_sum_num = referral_sum_num + referral_num
                price_detail['sum_tax_point'] = price_detail.get('sum_tax_point', 0)
                sum_tax_num = round(no_tax_sum_num * (price_detail['sum_tax_point'] / 100))

                sum_num = no_tax_sum_num + sum_tax_num

            price_detail['sum_num'] = sum_num
            price_detail['tax_num'] = tax_num
            price_detail['deduction_num'] = deduction_num
            price_detail['referral_num'] = referral_num
            price_detail['sum_tax_num'] = sum_tax_num

            return price_detail


class QuotationPlanEditSerializer(serializers.ModelSerializer):
    title = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = QuotationPlan
        fields = ['title', 'price', 'period', 'projects', 'services', 'price_detail']


class ReportSimpleSerializer(serializers.ModelSerializer):
    proposal = ProposalSimpleField(queryset=Proposal.objects.all(), many=False, required=False)
    lead = LeadSimpleField(queryset=Lead.objects.all(), many=False, required=False)
    report_title = serializers.SerializerMethodField(read_only=True)

    published_date = serializers.SerializerMethodField(read_only=True)
    created_date = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'uid', "lead", "proposal", 'report_url', 'report_type', 'creation_source', 'title',
                  'report_title', 'published_date', 'created_date']

    def get_report_title(self, obj):
        if obj.report_type == 'proposal':
            if obj.title:
                return obj.title.replace('项目反馈报告', '').replace('反馈报告', '').strip()
        elif obj.report_type == 'lead':
            if obj.title:
                return obj.title.replace('沟通反馈记录', '').replace('反馈记录', '').strip()
        elif obj.title:
            return obj.title.strip()
        return obj.title

    def get_published_date(self, obj):
        if obj.published_at:
            return obj.published_at.strftime(settings.SAMPLE_DATE_FORMAT)

    def get_created_date(self, obj):
        if obj.created_at:
            return obj.created_at.strftime(settings.SAMPLE_DATE_FORMAT)


class ReportDetailSerializer(serializers.ModelSerializer):
    proposal = ProposalField(queryset=Proposal.objects.all(), many=False, required=False)
    lead = LeadField(queryset=Lead.objects.all(), many=False, required=False)

    version_content = serializers.SerializerMethodField(read_only=True)
    meeting_participants = serializers.SerializerMethodField(read_only=True)
    main_content = serializers.SerializerMethodField(read_only=True)
    quotation_plans = serializers.SerializerMethodField(read_only=True)
    report_url = serializers.CharField(read_only=True)
    is_expired = serializers.SerializerMethodField(read_only=True)

    report_title = serializers.SerializerMethodField(read_only=True)

    published_date = serializers.SerializerMethodField(read_only=True)
    created_date = serializers.SerializerMethodField(read_only=True)

    meeting_time = serializers.DateField(format=settings.SAMPLE_DATE_FORMAT, allow_null=True, required=False)

    publisher = UserField(many=False, queryset=User.objects.all())
    reviewer = UserField(many=False, queryset=User.objects.all())

    latest_lead_quotation = serializers.SerializerMethodField(read_only=True)

    application_platforms_text = serializers.SerializerMethodField(read_only=True)
    industries_text = serializers.SerializerMethodField(read_only=True)
    product_types_text = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = '__all__'

    def get_report_title(self, obj):
        if obj.report_type == 'proposal':
            if obj.title:
                return obj.title.replace('项目反馈报告', '').replace('反馈报告', '').strip()
        elif obj.report_type == 'lead':
            if obj.title:
                return obj.title.replace('沟通反馈记录', '').replace('反馈记录', '').strip()
        elif obj.title:
            return obj.title.strip()
        return obj.title

    def get_version_content(self, obj):
        if obj.version_content:
            return json.loads(obj.version_content, encoding='utf-8')
        elif obj.report_type == 'proposal':
            return []

    def get_meeting_participants(self, obj):
        if obj.meeting_participants:
            return json.loads(obj.meeting_participants, encoding='utf-8')
        elif obj.report_type == 'lead':
            return []

    def get_main_content(self, obj):
        if obj.main_content:
            return json.loads(obj.main_content, encoding='utf-8')

    def get_quotation_plans(self, obj):
        quotation_plans = obj.quotation_plans.all().order_by('position', 'created_at')
        data = QuotationPlanDetailSerializer(quotation_plans, many=True).data
        return data

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_published_date(self, obj):
        if obj.published_at:
            return obj.published_at.strftime(settings.SAMPLE_DATE_FORMAT)

    def get_created_date(self, obj):
        if obj.created_at:
            return obj.created_at.strftime(settings.SAMPLE_DATE_FORMAT)

    def get_latest_lead_quotation(self, obj):
        from clients.serializers import LeadQuotationViewSerializer
        lead = None
        if obj.lead_id:
            lead = obj.lead
        elif obj.proposal_id and obj.proposal.lead_id:
            lead = obj.proposal.lead
        if lead:
            quotation = lead.quotations.filter(status='quoted').order_by('-quoted_at').first()
            if quotation:
                return LeadQuotationViewSerializer(quotation).data

    def get_application_platforms_text(self, obj):
        if obj.application_platforms:
            return '，'.join(obj.application_platforms.values_list('name', flat=True))

    def get_industries_text(self, obj):
        if obj.industries:
            return '，'.join(obj.industries.values_list('name', flat=True))

    def get_product_types_text(self, obj):
        if obj.product_types:
            return '，'.join(obj.product_types.values_list('name', flat=True))


class QuotationPlanDetailPageViewSerializer(QuotationPlanDetailSerializer):
    price = serializers.SerializerMethodField(read_only=True)
    price_unit = serializers.SerializerMethodField(read_only=True)

    def get_price(self, obj):
        if obj.price and "万" in obj.price:
            return obj.price.replace("万", '')
        return obj.price

    def get_price_unit(self, obj):
        if obj.price and "万" in obj.price:
            return "万"


class ReportDetailPageViewSerializer(ReportDetailSerializer):
    quotation_plans = serializers.SerializerMethodField(read_only=True)

    def get_quotation_plans(self, obj):
        quotation_plans = obj.quotation_plans.all().order_by('position', 'created_at')
        data = QuotationPlanDetailPageViewSerializer(quotation_plans, many=True).data
        return data


class ReportTagSerializer(serializers.ModelSerializer):
    industries = IndustrySerializer(many=True, read_only=True)
    application_platforms = ApplicationPlatformSerializer(many=True, read_only=True)
    product_types = ProductTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = ['industries', 'application_platforms', 'product_types', 'uid', 'id']


class ProposalTagSerializer(serializers.ModelSerializer):
    industries = IndustrySerializer(many=True, read_only=True)
    application_platforms = ApplicationPlatformSerializer(many=True, read_only=True)

    class Meta:
        model = Proposal
        fields = ['industries', 'application_platforms']


class ReportPublishApplicantSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField(read_only=True)
    report_title = serializers.SerializerMethodField(read_only=True)
    proposal_title = serializers.SerializerMethodField(read_only=True)

    publish_applicant = serializers.SerializerMethodField(read_only=True)
    reviewer = serializers.SerializerMethodField(read_only=True)
    publisher = serializers.SerializerMethodField(read_only=True)

    created_at = serializers.DateTimeField(format=settings.SAMPLE_DATETIME_FORMAT)
    publish_applicant_at = serializers.DateTimeField(format=settings.SAMPLE_DATETIME_FORMAT)
    published_at = serializers.DateTimeField(format=settings.SAMPLE_DATETIME_FORMAT)

    publish_applicant_during = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = ['status_display', 'report_title', 'proposal_title', 'publish_applicant', 'reviewer', 'publisher',
                  'created_at', 'publish_applicant_at', 'published_at', 'publish_applicant_during']

    def get_report_title(self, obj):
        if obj.report_type == 'proposal':
            if obj.title:
                return obj.title.replace('项目反馈报告', '').replace('反馈报告', '').strip()
        elif obj.report_type == 'lead':
            if obj.title:
                return obj.title.replace('沟通反馈记录', '').replace('反馈记录', '').strip()
        elif obj.title:
            return obj.title.strip()
        return obj.title

    def get_proposal_title(self, obj):
        if obj.proposal:
            return '【{}】{}'.format(obj.proposal.id, obj.proposal.name)

    def get_publish_applicant(self, obj):
        if obj.publish_applicant:
            return obj.publish_applicant.username

    def get_reviewer(self, obj):
        if obj.reviewer:
            return obj.reviewer.username

    def get_publisher(self, obj):
        if obj.publisher:
            return obj.publisher.username

    def get_status_display(self, obj):
        if obj.is_public:
            return '已发布'
        elif obj.reviewer:
            return '审核发布中'
        return '草稿'

    def get_publish_applicant_during(self, obj):
        if obj.publish_applicant_at and obj.published_at:
            during = obj.published_at - obj.publish_applicant_at
            days = during.days
            seconds = during.seconds
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            date_str = "{}小时{}分钟{}秒".format(hours, minutes, seconds)
            if days:
                date_str = str(days) + "天" + date_str
            return date_str


class ReportEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportEvaluation
        fields = '__all__'


class ReportEvaluationViewSerializer(serializers.ModelSerializer):
    address = serializers.SerializerMethodField(read_only=True)
    remark_list = serializers.ListField(read_only=True)

    class Meta:
        model = ReportEvaluation
        fields = '__all__'

    def get_address(self, obj):
        if not obj.address:
            obj.build_ip_address()
        return obj.address
