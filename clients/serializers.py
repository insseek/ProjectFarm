from datetime import datetime, timedelta
import json

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import serializers, fields

from auth_top.models import TopUser
from auth_top.serializers import TopUserField
from clients.models import Lead, LeadIndividual, LeadOrganization, RequirementInfo, LeadPunchRecord, \
    TrackCodeFile, LeadTrack, LeadSource, LeadQuotation, ClientInfo, LeadReportFile, Client
from proposals.models import Proposal
from projects.models import Project, ProjectClient
from projects.serializers import ProjectField, ProjectSimpleField, ProjectStageSimpleSerializer

from farmbase.serializers import UserField
from tasks.serializers import TaskField
from files.serializers import FileField, File, FileSerializer


class LeadField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        lead = Lead.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": lead.name}
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


class ProposalStatusField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = Proposal.objects.get(pk=value.pk)
        dict = {"id": value.pk, "status": proposal.status, "status_display": proposal.get_status_display()}
        return dict


class ProjectStatusField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        current_stages = ProjectStageSimpleSerializer(project.current_stages, many=True).data
        dict = {"id": value.pk, "current_stages": current_stages, "stage_display": project.stage_display}

        return dict


class ClientSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    projects = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = '__all__'

    def get_projects(self, obj):
        data = []
        for project_client in obj.project_clients.all():
            project = project_client.project
            project_data = {"name": project.name, 'id': project.id, 'is_admin': project_client.is_admin}
            data.append(project_data)
        return data


class ClientSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class ProjectClientSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    project = ProjectSimpleField(many=False, read_only=True)
    client = ClientSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = ProjectClient
        fields = '__all__'

    def get_permissions(self, obj):
        if obj.is_admin:
            return obj.ADMIN_PERMISSIONS
        else:
            return obj.permissions


# class ClientField(serializers.PrimaryKeyRelatedField):
#     def to_representation(self, value):
#         if not value:
#             return None
#         client = Client.objects.get(pk=value.pk)
#         dict = {"id": value.pk, "name": client.name}
#         return dict


class LeadIndividualSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadIndividual
        fields = '__all__'


class LeadOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadOrganization
        fields = '__all__'


class LeadSerializer(serializers.ModelSerializer):
    leave_info_at = serializers.DateTimeField(format=settings.DATETIME_FORMAT, allow_null=True, required=False)
    salesman = UserField(many=False, queryset=User.objects.all(), required=True)

    class Meta:
        model = Lead
        fields = '__all__'


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = '__all__'


class LeadSourceViewSerializer(serializers.ModelSerializer):
    organization = LeadOrganizationSerializer(many=False, read_only=True)
    organization_name = serializers.SerializerMethodField(read_only=True)
    source_type_display = serializers.CharField()
    sem_type_display = serializers.CharField()
    leave_info_type_display = serializers.CharField()
    content_marketing_type_display = serializers.CharField()
    activity_type_display = serializers.CharField()
    organization_type_display = serializers.CharField()

    leave_info_date = serializers.SerializerMethodField()
    leave_info_time = serializers.SerializerMethodField()

    class Meta:
        model = LeadSource
        fields = '__all__'

    def get_organization_name(self, obj):
        if obj.organization:
            return obj.organization.name

    def get_leave_info_date(self, obj):
        if obj.leave_info_at:
            return obj.leave_info_at.strftime(settings.DATE_FORMAT)
        return ''

    def get_leave_info_time(self, obj):
        if obj.leave_info_at:
            return obj.leave_info_at.strftime(settings.TIME_FORMAT)
        return ''


class ClientInfoSerializer(serializers.ModelSerializer):
    communication_cost = fields.MultipleChoiceField(choices=ClientInfo.COMMUNICATIONS)

    communication_cost_display = serializers.SerializerMethodField()
    client_background_display = serializers.SerializerMethodField()
    contact_role_display = serializers.SerializerMethodField()
    decision_making_capacity_display = serializers.SerializerMethodField()
    technical_capacity_display = serializers.SerializerMethodField()

    class Meta:
        model = ClientInfo
        fields = '__all__'

    def get_communication_cost_display(self, obj):
        data = []
        if obj.communication_cost:
            for code, name in obj.COMMUNICATIONS:
                if code in obj.communication_cost:
                    data.append(name)
        return data

    def get_client_background_display(self, obj):
        return obj.get_client_background_display()

    def get_contact_role_display(self, obj):
        return obj.get_contact_role_display()

    def get_decision_making_capacity_display(self, obj):
        return obj.get_decision_making_capacity_display()

    def get_technical_capacity_display(self, obj):
        return obj.get_technical_capacity_display()


class RequirementSerializer(serializers.ModelSerializer):
    service = fields.MultipleChoiceField(choices=RequirementInfo.SERVICES)
    reliability_factor = fields.MultipleChoiceField(choices=RequirementInfo.RELIABILITY_FACTORS)
    application_platform = fields.MultipleChoiceField(choices=RequirementInfo.PLATFORMS)
    available_material = fields.MultipleChoiceField(choices=RequirementInfo.MATERIALS)
    decision_factor = fields.MultipleChoiceField(choices=RequirementInfo.DECISION_FACTORS)
    rigid_requirement = fields.MultipleChoiceField(choices=RequirementInfo.RIGID_REQUIREMENTS)
    communication_cost = fields.MultipleChoiceField(choices=RequirementInfo.COMMUNICATIONS)
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    files = FileField(many=True, read_only=True)

    class Meta:
        model = RequirementInfo
        fields = '__all__'


class LeadPunchRecordCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadPunchRecord
        fields = ['lead', 'contact_type', 'contact_time', 'contact_result', 'remarks', 'creator']


class LeadPunchRecordViewSerializer(serializers.ModelSerializer):
    lead = LeadField(many=False, queryset=Lead.objects.all(), required=False)
    creator = UserField(many=False, required=False, read_only=True)
    contact_type_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LeadPunchRecord
        fields = '__all__'

    def get_contact_type_display(self, obj):
        return obj.get_contact_type_display()


class LeadQuotationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadQuotation
        fields = ['lead', 'company_name', 'company_business', 'product_description', 'product_applications', 'remarks',
                  'creator', 'development_goal', 'integrity_require']


class LeadQuotationViewSerializer(serializers.ModelSerializer):
    lead = LeadField(many=False, queryset=Lead.objects.all(), required=False)
    creator = UserField(many=False, required=False, read_only=True)
    quoter = UserField(many=False, required=False, read_only=True)
    editor = UserField(many=False, required=False, read_only=True)
    rejecter = UserField(many=False, required=False, read_only=True)
    files = FileField(many=True, read_only=True)
    status_display = serializers.SerializerMethodField()
    quotation_list = serializers.SerializerMethodField()

    class Meta:
        model = LeadQuotation
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_quotation_list(self, obj):
        if obj.quotation_list:
            return json.loads(obj.quotation_list, encoding='utf-8')
        elif obj.quotation_content:
            return [{'title': '', 'content': obj.quotation_content, 'calculator_link': obj.calculator_link}]


class LeadQuotationEditSerializer(serializers.ModelSerializer):
    lead = LeadField(many=False, queryset=Lead.objects.all(), required=False)
    creator = UserField(many=False, required=False, read_only=True)
    contact_type_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LeadQuotation
        fields = '__all__'

    def get_contact_type_display(self, obj):
        return obj.get_contact_type_display()


class LeadListSerializer(serializers.ModelSerializer):
    lead_source = LeadSourceViewSerializer(many=False, read_only=True)
    creator = UserField(many=False, required=False, read_only=True)
    salesman = UserField(many=False, required=False, read_only=True)
    closed_by = UserField(many=False, required=False, read_only=True)
    apply_closed_by = UserField(many=False, required=False, read_only=True)
    proposal = ProposalField(required=False, many=False, read_only=True)

    company = LeadOrganizationSerializer(many=False, read_only=True)
    undone_tasks = TaskField(many=True, read_only=True)
    can_be_converted_to_proposal = serializers.BooleanField()

    status_display = serializers.SerializerMethodField()
    reliability_display = serializers.SerializerMethodField()

    requirement = RequirementSerializer()
    punch_records = LeadPunchRecordViewSerializer(many=True, read_only=True)
    latest_punch_record = LeadPunchRecordViewSerializer(many=False, read_only=True)

    latest_report = serializers.SerializerMethodField()
    files = FileField(many=True, read_only=True)

    quotations = serializers.SerializerMethodField()

    quotation_status_display = serializers.SerializerMethodField()
    quotation_status = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_reliability_display(self, obj):
        return obj.get_reliability_display()

    def get_latest_report(self, obj):
        return obj.latest_report_data()

    def get_quotations(self, obj):
        quotations = obj.quotations.order_by('-edited_at')
        return LeadQuotationViewSerializer(quotations, many=True).data

    def get_quotation_status_display(self, obj):
        quotations = obj.quotations.order_by('-edited_at')
        if quotations.exists():
            return quotations.first().get_status_display()

    def get_quotation_status(self, obj):
        quotations = obj.quotations.order_by('-edited_at')
        if quotations.exists():
            return quotations.first().status


class LeadSimpleSerializer(serializers.ModelSerializer):
    creator = UserField(many=False, required=False, read_only=True)
    salesman = UserField(many=False, required=False, read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = ['id', 'name', 'creator', 'salesman', 'contact_name', 'contact_job', 'phone_number', 'company_name',
                  'status_display', 'created_at', 'closed_at']

    def get_status_display(self, obj):
        return obj.get_status_display()


class LeadTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadTrack
        exclude = ['id', 'modified_at', 'created_at']


class LeadSemTrackSerializer(serializers.ModelSerializer):
    created_time = serializers.SerializerMethodField()
    creator_username = serializers.SerializerMethodField()
    salesman_username = serializers.SerializerMethodField()

    closed_within_a_day = serializers.SerializerMethodField()
    closed_within_a_week = serializers.SerializerMethodField()

    lead_track = serializers.SerializerMethodField()
    undone_tasks = serializers.SerializerMethodField()

    lead_source = LeadSourceViewSerializer(many=False, read_only=True)

    class Meta:
        model = Lead
        fields = ['creator_username', 'created_at', 'created_time', 'created_date', 'address', 'name',
                  'closed_within_a_day', 'lead_track', 'lead_source', 'closed_within_a_week', 'closed_reason',
                  'closed_at', 'undone_tasks', 'salesman_username']

    def get_creator_username(self, obj):
        if obj.creator:
            return obj.creator.username
        return ''

    def get_salesman_username(self, obj):
        if obj.salesman:
            return obj.salesman.username
        return ''

    def get_closed_within_a_day(self, obj):
        if obj.status == 'invalid' and obj.closed_at and obj.created_at + timedelta(hours=24) >= obj.closed_at:
            return '是'
        if obj.status == 'apply_close' and obj.created_at + timedelta(hours=24) >= obj.apply_closed_at:
            return '是'
        elif obj.status == 'contact' and obj.created_at + timedelta(hours=24) >= datetime.now():
            return 'T+1前期沟通中'
        return '否'

    def get_closed_within_a_week(self, obj):
        if obj.status == 'invalid' and obj.closed_at and obj.created_at + timedelta(hours=24 * 7) >= obj.closed_at:
            return '是'
        elif obj.status == 'apply_close' and obj.created_at + timedelta(hours=24 * 7) >= obj.apply_closed_at:
            return '是'
        elif obj.status == 'contact' and obj.created_at + timedelta(hours=24 * 7) >= datetime.now():
            return 'T+7前期沟通中'
        return '否'

    def get_lead_track(self, obj):
        if obj.lead_source and obj.lead_source.sem_track_code:
            sem_track_code = obj.lead_source.sem_track_code
            lead_tracks = LeadTrack.objects.filter(track_code=sem_track_code)
            if lead_tracks.exists():
                lead_track = lead_tracks.first()
                return LeadTrackSerializer(lead_track).data
        return {}

    def get_created_time(self, obj):
        return obj.created_at.strftime(settings.TIME_FORMAT)

    def get_undone_tasks(self, obj):
        if obj.undone_tasks():
            return '; '.join([task.name for task in obj.undone_tasks()])
        return ''


class LeadExportSerializer(serializers.ModelSerializer):
    creator = UserField(many=False, required=False, read_only=True)
    salesman = UserField(many=False, required=False, read_only=True)
    creator_username = serializers.SerializerMethodField()
    salesman_username = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    lead_source = LeadSourceViewSerializer(many=False, read_only=True)

    source_display = serializers.SerializerMethodField()
    source_info = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = ['id', 'created_at', 'status_display', 'name', 'description', 'remarks', 'proposal', 'closed_at',
                  'closed_reason', 'lead_source', 'source_display', 'source_info',
                  'creator', 'salesman', 'creator_username', 'salesman_username',
                  'contact_name', 'company_name', 'contact_job',
                  'phone_number',
                  'address']

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_source_display(self, obj):
        if obj.lead_source:
            return obj.lead_source.get_source_type_display()

    def get_creator_username(self, obj):
        if obj.creator:
            return obj.creator.username

    def get_salesman_username(self, obj):
        if obj.salesman:
            return obj.salesman.username

    def get_source_info(self, obj):
        if obj.lead_source:
            return obj.lead_source.source_info


class LeadConversionRateSerializer(serializers.ModelSerializer):
    lead_source = LeadSourceViewSerializer(many=False, read_only=True)
    status_display = serializers.SerializerMethodField()
    proposal = ProposalStatusField(many=False, read_only=True)
    project = ProjectStatusField(many=False, read_only=True)

    class Meta:
        model = Lead
        fields = ['created_at', 'status', 'lead_source', 'status_display', 'proposal', 'project']

    def get_status_display(self, obj):
        return obj.get_status_display()


class LeadRequiredFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['company_name', 'address', 'contact_name', 'contact_job', 'phone_number', 'company']


class TrackCodeFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackCodeFile
        fields = '__all__'


class LeadReportFileSerializer(serializers.ModelSerializer):
    creator = UserField(many=False, queryset=User.objects.all(), required=True)
    file_url = serializers.SerializerMethodField(read_only=True)
    creation_source = serializers.SerializerMethodField()

    class Meta:
        model = LeadReportFile
        fields = '__all__'

    def get_file_url(self, obj):
        return obj.file.url

    def get_creation_source(self, obj):
        return 'uploaded_file'
