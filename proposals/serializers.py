from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import serializers, fields

from clients.models import Lead, LeadIndividual, LeadOrganization
from clients.serializers import RequirementSerializer, LeadSourceViewSerializer, LeadQuotationViewSerializer, \
    ClientInfoSerializer
from files.models import File
from farmbase.serializers import UserField

from gearfarm.utils.const import PROPOSAL_STATUS_ACTIONS
from proposals.models import Proposal, HandoverReceipt
from projects.models import Project
from tasks.serializers import TaskSerializer
from reports.serializers import IndustrySerializer, ApplicationPlatformSerializer

PROPOSAL_STATUS_DICT = Proposal.PROPOSAL_STATUS_DICT


class ProjectField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        created_at = project.created_at
        if created_at:
            created_at = created_at.strftime(settings.DATETIME_FORMAT)
        dict = {"id": value.pk, "name": project.name, "created_at": created_at}
        return dict


class HandoverReceiptField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = HandoverReceipt.objects.get(pk=value.pk)
        created_at = project.created_at
        if created_at:
            created_at = created_at.strftime(settings.SAMPLE_DATE_FORMAT)
        dict = {"id": value.pk, "created_at": created_at}
        return dict


class FileField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        file = File.objects.get(pk=value.pk)
        dict = {"id": value.pk, "url": file.file.url, 'filename': file.filename, 'suffix': file.suffix}
        return dict


class ProposalField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = Proposal.objects.get(pk=value.pk)
        if proposal.description:
            description = proposal.description[0:80]
        else:
            description = proposal.description
        closed_at = proposal.closed_at
        if closed_at:
            closed_at = closed_at.strftime(settings.SAMPLE_DATE_FORMAT)
        dict = {"id": value.pk, "name": proposal.name, "description": description,
                "closed_reason_text": proposal.closed_reason_text, "closed_at": closed_at,
                "closed_reason_remarks": proposal.closed_reason_remarks}
        return dict


class LeadField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        lead = Lead.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": lead.name}
        return dict


class LeadSimpleSerializer(serializers.ModelSerializer):
    creator = UserField(many=False, queryset=User.objects.all(), required=False)
    salesman = UserField(many=False, queryset=User.objects.all(), required=False)
    latest_lead_quotation = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = ['id', 'name', 'creator', 'salesman', 'latest_lead_quotation']

    def get_latest_lead_quotation(self, obj):
        quotation = obj.quotations.filter(status='quoted').order_by('-quoted_at').first()
        if quotation:
            return LeadQuotationViewSerializer(quotation).data


class LeadIndividualSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadIndividual
        fields = '__all__'


class LeadOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadOrganization
        fields = '__all__'


class ProposalSerializer(serializers.ModelSerializer):
    files = FileField(many=True, read_only=True)
    title = serializers.CharField(read_only=True)

    available_material = fields.MultipleChoiceField(choices=Proposal.MATERIALS, required=False, allow_null=True)
    rigid_requirement = fields.MultipleChoiceField(choices=Proposal.RIGID_REQUIREMENTS, required=False, allow_null=True)

    quip_folder_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Proposal
        fields = '__all__'

    def get_quip_folder_data(self, obj):
        return obj.quip_folder_data()


class ProposalEditSerializer(serializers.ModelSerializer):
    quip_folder_id = serializers.CharField(required=False)

    available_material = fields.MultipleChoiceField(choices=Proposal.MATERIALS)
    rigid_requirement = fields.MultipleChoiceField(choices=Proposal.RIGID_REQUIREMENTS)

    class Meta:
        model = Proposal
        fields = ['name', 'description', 'business_objective', 'period', 'available_material', 'material_remarks',
                  'reference', 'reference_remarks', 'rigid_requirement',
                  'rigid_requirement_remarks', 'quip_folder_type', 'quip_folder_id', 'rebate', 'rebate_info']


class ProposalSimpleSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    reliability_display = serializers.SerializerMethodField()
    source_display = serializers.SerializerMethodField()
    source_remark = serializers.CharField(required=False)

    class Meta:
        model = Proposal
        fields = ('id', 'created_at', 'name', 'description', 'submitter', 'status_display', 'reliability_display',
                  'source_display',
                  'source_remark')

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_reliability_display(self, obj):
        return obj.get_reliability_display()

    def get_source_display(self, obj):
        return obj.get_source_display()


class ProposalDetailSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    pm = UserField(many=False, queryset=User.objects.all(), required=False)
    bd = UserField(many=False, queryset=User.objects.all(), required=False)
    lead = LeadSimpleSerializer(many=False, read_only=True)
    lead_source = LeadSourceViewSerializer(many=False, read_only=True)
    client_info = ClientInfoSerializer(many=False, read_only=True)
    # requirement = RequirementSerializer(many=False, read_only=True)
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)

    status_display = serializers.SerializerMethodField()
    rebate_display = serializers.SerializerMethodField()

    reliability_display = serializers.SerializerMethodField()

    closed_reason_display = serializers.SerializerMethodField()
    files = FileField(many=True, read_only=True)

    project = ProjectField(many=False, queryset=Project.objects.all(), required=False)
    handover_receipt = HandoverReceiptField(many=False, queryset=HandoverReceipt.objects.all(), required=False)

    quip_doc = serializers.CharField(read_only=True)
    budget = serializers.CharField(required=False)
    actions = serializers.SerializerMethodField()
    quip_folder = serializers.CharField(read_only=True)
    quip_folder_data = serializers.SerializerMethodField()

    industries = IndustrySerializer(many=True, read_only=True)
    application_platforms = ApplicationPlatformSerializer(many=True, read_only=True)

    available_material = fields.MultipleChoiceField(choices=Proposal.MATERIALS)
    rigid_requirement = fields.MultipleChoiceField(choices=Proposal.RIGID_REQUIREMENTS)

    available_material_display = serializers.SerializerMethodField()
    rigid_requirement_display = serializers.SerializerMethodField()
    reference_display = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = '__all__'

    def get_available_material_display(self, obj):
        data = []
        if obj.available_material:
            for code, name in obj.MATERIALS:
                if code in obj.available_material:
                    data.append(name)
        return data

    def get_rigid_requirement_display(self, obj):
        data = []
        if obj.rigid_requirement:
            for code, name in obj.RIGID_REQUIREMENTS:
                if code in obj.rigid_requirement:
                    data.append(name)
        return data

    def get_rebate_display(self, obj):
        return obj.get_rebate_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_reliability_display(self, obj):
        return obj.get_reliability_display()

    def get_closed_reason_display(self, obj):
        return obj.get_closed_reason_display()

    def get_reference_display(self, obj):
        return obj.get_reference_display()

    def get_actions(self, obj):
        if obj.status in PROPOSAL_STATUS_ACTIONS:
            return PROPOSAL_STATUS_ACTIONS[obj.status]['actions']

    def get_quip_folder_data(self, obj):
        return obj.quip_folder_data()


class ProposalsPageSerializer(serializers.ModelSerializer):
    undone_tasks = TaskSerializer(many=True, read_only=True)
    pm = UserField(many=False, queryset=User.objects.all())
    bd = UserField(many=False, queryset=User.objects.all())
    quip_folder = serializers.CharField(read_only=True)
    quip_doc = serializers.CharField(read_only=True)
    description = serializers.SerializerMethodField()
    latest_report = serializers.SerializerMethodField()
    title = serializers.CharField(read_only=True)
    reliability_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    closed_reason_display = serializers.SerializerMethodField()
    lead = LeadField(many=False, queryset=Lead.objects.all(), required=False)
    latest_lead_quotation = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = '__all__'

    def get_description(self, obj):
        if obj.description:
            return obj.description[0:80]
        return obj.description

    def get_reliability_display(self, obj):
        return obj.get_reliability_display()

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_latest_report(self, obj):
        return obj.latest_report_data()

    def get_closed_reason_display(self, obj):
        return obj.get_closed_reason_display()

    def get_latest_lead_quotation(self, obj):
        if obj.lead_id:
            quotation = obj.lead.quotations.filter(status='quoted').order_by('-quoted_at').first()
            if quotation:
                return LeadQuotationViewSerializer(quotation).data


class BusinessOpportunitySerializer(serializers.ModelSerializer):
    budget = serializers.CharField(required=True)
    decision_time = serializers.DateField(format=settings.SAMPLE_DATE_FORMAT, required=True)
    decision_makers = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    decision_email = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    title = serializers.CharField(read_only=True)
    pm = UserField(many=False, read_only=True)
    bd = UserField(many=False, read_only=True)
    biz_opp_created_at = serializers.DateTimeField(format=settings.SAMPLE_DATE_FORMAT, required=False)
    status = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(format=settings.SAMPLE_DATE_FORMAT, read_only=True)

    class Meta:
        model = Proposal
        fields = (
            'decision_time', 'budget', 'budget_unit', 'decision_makers', 'decision_email', 'title', 'pm', 'bd',
            'biz_opp_created_at',
            'id', 'status', 'created_at')


class HandoverReceiptSerializer(serializers.ModelSerializer):
    proposal = ProposalField(queryset=Proposal.objects.all(), many=False)
    submitter = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = HandoverReceipt
        fields = '__all__'


class HandoverReceiptDetailSerializer(serializers.ModelSerializer):
    proposal = ProposalField(queryset=Proposal.objects.all(), required=False, many=False)
    submitter = UserField(many=False, required=False, queryset=User.objects.all())

    invoice_type_display = serializers.SerializerMethodField()
    invoice_mode_display = serializers.SerializerMethodField()
    invoice_period_display = serializers.SerializerMethodField()
    op_invoice_mode_display = serializers.SerializerMethodField()
    op_payment_mode_display = serializers.SerializerMethodField()

    class Meta:
        model = HandoverReceipt
        fields = '__all__'

    def get_invoice_type_display(self, obj):
        return obj.get_invoice_type_display()

    def get_invoice_mode_display(self, obj):
        return obj.get_invoice_mode_display()

    def get_invoice_period_display(self, obj):
        return obj.get_invoice_period_display()

    def get_op_invoice_mode_display(self, obj):
        return obj.get_op_invoice_mode_display()

    def get_op_payment_mode_display(self, obj):
        return obj.get_op_payment_mode_display()


class ProposalExportSerializer(serializers.ModelSerializer):
    submitter_username = serializers.SerializerMethodField()
    pm_username = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    source_display = serializers.SerializerMethodField()
    source_info = serializers.SerializerMethodField()
    closed_reason = serializers.SerializerMethodField()
    lead_name = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = ['id', 'created_at', 'status_display', 'name', 'description', 'source_display', 'source_info',
                  'submitter_username', 'pm_username',
                  'contact_at', 'report_at', 'closed_at', 'closed_reason', 'lead_name']

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_source_display(self, obj):
        if obj.lead_source:
            return obj.lead_source.source_type_display

    def get_submitter_username(self, obj):
        if obj.submitter:
            return obj.submitter.username

    def get_pm_username(self, obj):
        if obj.pm:
            return obj.pm.username

    def get_source_info(self, obj):
        if obj.lead_source:
            return obj.lead_source.source_info

    def get_closed_reason(self, obj):
        if obj.get_closed_reason_display():
            return "{} ({})".format(obj.closed_reason_text or '', obj.closed_reason_remarks or '')

    def get_lead_name(self, obj):
        if obj.lead:
            return "【{}】{}".format(obj.lead.id, obj.lead.name)


class ProposalMembersSerializer(serializers.ModelSerializer):
    bd = UserField(many=False, queryset=User.objects.all(), required=False)
    pm = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    submitter = UserField(many=False, read_only=True)
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Proposal
        fields = ['id', 'name', 'bd', 'pm', 'submitter']
