import json
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Sum, IntegerField, When, Case, Q
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers

from gearfarm.utils.page_path_utils import build_page_path
from farmbase.serializers import UserBasicSerializer, GroupField
from clients.models import Client
from finance.models import JobContract
from projects.models import Project, JobPosition, ProjectGanttChart, GanttTaskCatalogue, GanttTaskTopic, \
    GanttRole, DeliveryDocument, DeliveryDocumentType, \
    ProjectContract, ProjectPrototype, PrototypeCommentPoint, JobPositionNeed, JobPositionCandidate, ClientCalendar, \
    ProjectLinks, TechnologyCheckpoint, JobStandardScore, JobReferenceScore, ProjectTest, \
    ProjectStage, ProjectWorkHourPlan, WorkHourRecord, ProjectWorkHourOperationLog, Choice, GradeQuestionnaire, \
    Questionnaire, Question, AnswerSheet

from logs.models import Log
from logs.serializers import BrowsingHistorySerializer, LogSerializer
from tasks.serializers import TaskSerializer
from developers.models import Role, Developer
from comments.serializers import CommentSerializer
from projects.utils.common_utils import get_project_members_data, get_project_members_dict, get_project_developers_data
from proposals.models import Proposal, HandoverReceipt
from farmbase.utils import gen_uuid, get_user_data
from geargitlab.tasks import get_gitlab_project_data, get_gitlab_group_data, get_gitlab_user_data


class ClientSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class ProposalField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = Proposal.objects.get(pk=value.pk)
        if proposal.description:
            description = proposal.description[0:80]
        else:
            description = proposal.description
        dict = {"id": value.pk, "name": proposal.name, "description": description}
        return dict


class RoleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        role = Role.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": role.name}
        return dict


class GanttChartWithProjectField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        gantt_chart = ProjectGanttChart.objects.get(pk=value.pk)
        dict = {"id": value.pk, "project": {'id': gantt_chart.project.id, 'name': gantt_chart.project.name,
                                            'stage_display': gantt_chart.project.stage_display}}
        return dict


class GanttChartField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        gantt_chart = ProjectGanttChart.objects.get(pk=value.pk)
        dict = {"id": gantt_chart.id, 'uid': gantt_chart.uid}
        return dict


class GanttRoleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        role = GanttRole.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": role.name, "role_type": role.role_type}
        return dict


class GanttTaskCatalogueField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        catalogue = GanttTaskCatalogue.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": catalogue.name, "number": catalogue.number}
        return dict


class DeveloperField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        developer = Developer.objects.get(pk=value.pk)
        avatar = None
        if developer.avatar:
            avatar = developer.avatar.url
        dict = {"id": value.pk, "name": developer.name, 'username': developer.name, 'phone': developer.phone,
                'avatar': avatar, 'avatar_url': avatar}
        return dict


class DeliveryDocumentTypeField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        document_type = DeliveryDocumentType.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": document_type.name, "suffix": document_type.suffix,
                "number": document_type.number}
        return dict


class DeveloperWithBankInfoField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        developer = Developer.objects.get(pk=value.pk)
        last_login = developer.last_login.strftime(settings.DATETIME_FORMAT) if developer.last_login else None
        dict = {"id": value.pk, "name": developer.name, "payment_info": developer.payment_info,
                'gitlab_user_id': developer.gitlab_user_id, 'last_login': last_login,
                'is_active': developer.is_active, 'phone': developer.phone,
                'id_card_number': developer.id_card_number}
        return dict


class DeveloperDashboardCardField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        developer = Developer.objects.get(pk=value.pk)
        last_login = developer.last_login.strftime(settings.DATETIME_FORMAT) if developer.last_login else None
        avatar = None
        if developer.avatar:
            avatar = developer.avatar.url
        dict = {"id": value.pk,
                "name": developer.name,
                'username': developer.name,
                'avatar': avatar,
                'avatar_url': avatar,
                'avatar_color': developer.avatar_color,
                'is_active': developer.is_active,
                'last_login': last_login,
                'gitlab_user_id': developer.gitlab_user_id,
                "gitlab_user": {"id": developer.gitlab_user_id} if developer.gitlab_user_id else None,
                "committers": []
                }
        return dict


class PositionNeedField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        position_need = JobPositionNeed.objects.get(pk=value.pk)
        dict = {"id": value.pk, "role": {'id': position_need.role.id, 'name': position_need.role.name}}
        return dict


class UserField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        users = User.objects.filter(pk=value.pk)
        if users.exists():
            user = users[0]
        else:
            return None

        avatar_url = None
        if user.profile.avatar:
            avatar_url = user.profile.avatar.url
        avatar_color = user.profile.avatar_color
        dict = {"id": value.pk, "username": user.username, "avatar": avatar_url, "avatar_url": avatar_url,
                'avatar_color': avatar_color, 'phone': user.profile.phone, 'is_active': user.is_active}
        return dict


class ProjectField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        done_at = project.done_at
        if done_at:
            done_at = done_at.strftime(settings.DATETIME_FORMAT)
        created_at = project.created_at
        if created_at:
            created_at = created_at.strftime(settings.DATETIME_FORMAT)

        manager_data = None
        if project.manager_id:
            manager_data = get_user_data(project.manager)
        tests_data = []
        # 【test】
        project_tests = project.tests.all()
        for project_test in project_tests:
            tests_data.append(get_user_data(project_test))
        test_data = None
        if project.test_id:
            test_data = get_user_data(project.test)
        designer_data = None
        if project.designer_id:
            designer_data = get_user_data(project.designer)
        tpm_data = None
        if project.tpm_id:
            tpm_data = get_user_data(project.tpm)
        product_manager_data = None
        if project.product_manager_id:
            product_manager_data = get_user_data(project.product_manager)
        deployment_servers = []
        if project.deployment_servers:
            deployment_servers = json.loads(project.deployment_servers, encoding='utf-8')
        current_stages = ProjectStageSimpleSerializer(project.current_stages, many=True).data
        dict = {"id": value.pk, "name": project.name, "done_at": done_at, "created_at": created_at,
                "current_stages": current_stages, "stage_display": project.stage_display, 'manager': manager_data,
                'tpm': tpm_data, 'test': test_data, 'designer': designer_data,
                'product_manager': product_manager_data, 'tests': tests_data,
                'deployment_servers': deployment_servers, 'members_dict': get_project_members_dict(project)}
        return dict


class JobProjectField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        dict = {
            "id": value.pk,
            "name": project.name,
            "created_at": project.created_at.strftime(settings.DATETIME_FORMAT),
            "end_date": project.end_date
        }
        return dict


class ProjectSimpleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": project.name,
                "created_at": project.created_at.strftime(settings.DATETIME_FORMAT),
                'manager': get_user_data(project.manager) if project.manager else None, 'end_date': project.end_date,
                "is_done": project.is_done
                }
        return dict


class ProjectWithMembersField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        done_at = project.done_at
        if done_at:
            done_at = done_at.strftime(settings.DATETIME_FORMAT)
        created_at = project.created_at
        if created_at:
            created_at = created_at.strftime(settings.DATETIME_FORMAT)
        current_stages = ProjectStageSimpleSerializer(project.current_stages, many=True).data
        dict = {"id": value.pk, "name": project.name, "done_at": done_at, "created_at": created_at,
                "current_stages": current_stages, "stage_display": project.stage_display,
                "members": get_project_members_data(project, with_bd=False)}
        return dict


class ProjectLinksSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLinks
        fields = '__all__'


class ProjectLinksDetailSerializer(serializers.ModelSerializer):
    gitlab_project = serializers.SerializerMethodField()
    quip_folder = serializers.CharField(read_only=True)
    quip_folder_data = serializers.SerializerMethodField()
    quip_engineer_folder = serializers.CharField(read_only=True)
    quip_engineer_folder_data = serializers.SerializerMethodField()
    ui_links = serializers.SerializerMethodField()

    class Meta:
        model = ProjectLinks
        fields = '__all__'

    def get_gitlab_project(self, obj):
        if obj.gitlab_group_id:
            return get_gitlab_group_data(obj.gitlab_group_id)
        elif obj.gitlab_project_id:
            return get_gitlab_project_data(obj.gitlab_project_id)

    def get_quip_folder_data(self, obj):
        return obj.quip_folder_data()

    def get_quip_engineer_folder_data(self, obj):
        return obj.quip_engineer_folder_data()

    def get_ui_links(self, obj):
        if obj.ui_links:
            return json.loads(obj.ui_links, encoding='utf-8')
        return []


class ProjectLinksWithEngineerDocsSerializer(serializers.ModelSerializer):
    gitlab_project = serializers.SerializerMethodField()
    engineer_contact_docs = serializers.SerializerMethodField()
    quip_engineer_folder = serializers.CharField(read_only=True)
    quip_engineer_folder_data = serializers.SerializerMethodField()
    ui_links = serializers.SerializerMethodField()

    class Meta:
        model = ProjectLinks
        fields = '__all__'

    def get_ui_links(self, obj):
        if obj.ui_links:
            return json.loads(obj.ui_links, encoding='utf-8')
        return []

    def get_gitlab_project(self, obj):
        if obj.gitlab_group_id:
            return get_gitlab_group_data(obj.gitlab_group_id)
        elif obj.gitlab_project_id:
            return get_gitlab_project_data(obj.gitlab_project_id)

    def get_engineer_contact_docs(self, obj):
        if obj.quip_engineer_folder_id:
            quip_projects_dev_contact_docs = cache.get('quip_projects_dev_contact_docs', {})
            if obj.project_id in quip_projects_dev_contact_docs:
                docs = quip_projects_dev_contact_docs[obj.project_id]
                doc_list = sorted(docs, key=lambda doc: doc['updated_usec'], reverse=True)
                return doc_list
            else:
                from farmbase.tasks import crawl_project_engineer_contact_folder_docs
                crawl_project_engineer_contact_folder_docs.delay(obj.project_id)
        return []

    def get_quip_engineer_folder_data(self, obj):
        return obj.quip_engineer_folder_data()


class JobStandardScoreSerializer(serializers.ModelSerializer):
    job_position = serializers.PrimaryKeyRelatedField(many=False, queryset=JobPosition.objects.all())
    total_rate = serializers.FloatField(read_only=True)
    average_score = serializers.FloatField(read_only=True)
    total = serializers.FloatField(read_only=True)
    average = serializers.FloatField(read_only=True)
    score_person = UserField(many=False, queryset=User.objects.all(), required=False)

    class Meta:
        model = JobStandardScore
        fields = '__all__'


class JobWithProjectSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, read_only=True)
    developer = DeveloperField(many=False, read_only=True)
    project = ProjectSimpleField(many=False, read_only=True)

    class Meta:
        model = JobPosition
        fields = '__all__'


class JobSimpleSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all())
    developer = DeveloperField(many=False, queryset=Developer.objects.all())

    class Meta:
        model = JobPosition
        fields = '__all__'


class JobField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        job = JobPosition.objects.get(pk=value.pk)
        return JobSimpleSerializer(job).data


class JobReferenceScoreSerializer(serializers.ModelSerializer):
    job_position = JobField(many=False, queryset=JobPosition.objects.all())
    score_person = UserField(many=False, queryset=User.objects.all(), required=False)

    total = serializers.IntegerField(read_only=True)
    average = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobReferenceScore
        fields = '__all__'


class JobContractWithPaymentSerializer(serializers.ModelSerializer):
    payments_statistics = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    remit_way = serializers.SerializerMethodField()
    project_results_show = serializers.SerializerMethodField()
    contract_type = serializers.CharField()

    class Meta:
        model = JobContract
        fields = '__all__'

    def get_payments(self, obj):
        payments = obj.payments.all().order_by('created_at')
        job_payments_data = JobPaymentListSerializer(payments, many=True).data
        return job_payments_data

    def get_remit_way(self, obj):
        return json.loads(obj.remit_way) if obj.remit_way else ''

    def get_project_results_show(self, obj):
        return json.loads(obj.project_results_show) if obj.project_results_show else []

    def get_payments_statistics(self, obj):
        return obj.payments_statistics


class JobReadOnlySerializer(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all())
    project = ProjectSimpleField(many=False, queryset=Project.objects.all())
    developer = DeveloperWithBankInfoField(many=False, queryset=Developer.objects.all())
    # 【code explain】【工程师评分】
    job_reference_scores = JobReferenceScoreSerializer(many=True, read_only=True)
    job_standard_score = JobStandardScoreSerializer(read_only=True, many=False)
    # star_rating与job_standard_score是一个东西
    star_rating = JobStandardScoreSerializer(read_only=True, many=False)

    class Meta:
        model = JobPosition
        fields = '__all__'


class JobSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all())
    project = ProjectSimpleField(many=False, queryset=Project.objects.all())
    developer = DeveloperWithBankInfoField(many=False, queryset=Developer.objects.all())
    # 【code explain】【工程师评分】
    job_reference_scores = JobReferenceScoreSerializer(many=True, read_only=True)

    job_standard_score = JobStandardScoreSerializer(read_only=True, many=False)
    # star_rating与job_standard_score是一个东西
    star_rating = JobStandardScoreSerializer(read_only=True, many=False)
    project_bugs_statistics = serializers.SerializerMethodField(read_only=True)

    total_amount = serializers.FloatField(read_only=True)
    # 总合同报酬
    total_contract_amount = serializers.FloatField(read_only=True)
    # 总合同天数
    total_contract_develop_days = serializers.IntegerField(read_only=True)

    can_be_deleted = serializers.BooleanField(read_only=True)

    current_stages = serializers.SerializerMethodField()
    grade_questionnaire = serializers.SerializerMethodField()
    is_have_questionnaires = serializers.BooleanField(read_only=True)

    class Meta:
        model = JobPosition
        fields = '__all__'

    def get_project_bugs_statistics(self, obj):
        return obj.project_bugs_statistics

    def get_current_stages(self, obj):
        current_stages = ProjectStageSimpleSerializer(obj.project.current_stages, many=True).data
        return current_stages

    def get_grade_questionnaire(self, obj):
        grade_questionnaires = obj.grade_questionnaires.all()
        grade_questionnaires_data = GradeQuestionnaireSerializer(grade_questionnaires, many=True).data
        return grade_questionnaires_data


class JobCreateSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all())
    project = ProjectSimpleField(many=False, queryset=Project.objects.all())
    developer = DeveloperWithBankInfoField(many=False, queryset=Developer.objects.all())
    role_remarks = serializers.CharField(allow_null=True, required=False, allow_blank=True)

    class Meta:
        model = JobPosition
        fields = ['project', 'role', 'developer', 'role_remarks']


# class JobPositionEditSerializer(serializers.ModelSerializer):
#     pay = serializers.FloatField(allow_null=True)
#     period = serializers.FloatField(allow_null=True)
#
#     class Meta:
#         model = JobPosition
#         fields = ['pay', 'period']


from finance.serializers import JobPaymentRetrieveSerializer, JobPaymentListSerializer


class JobWithPaymentsSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all())
    project = ProjectSimpleField(many=False, queryset=Project.objects.all())
    developer = DeveloperWithBankInfoField(many=False, queryset=Developer.objects.all())
    # 【code explain】【工程师评分】
    job_reference_scores = JobReferenceScoreSerializer(many=True, read_only=True)

    job_standard_score = JobStandardScoreSerializer(read_only=True, many=False)
    # star_rating与job_standard_score是一个东西
    star_rating = JobStandardScoreSerializer(read_only=True, many=False)
    project_bugs_statistics = serializers.SerializerMethodField(read_only=True)

    total_amount = serializers.FloatField(read_only=True)
    # 总合同报酬
    total_contract_amount = serializers.FloatField(read_only=True)
    # 总合同天数
    total_contract_develop_days = serializers.IntegerField(read_only=True)

    job_contracts = serializers.SerializerMethodField()
    no_contract_payments = JobPaymentListSerializer(many=True, read_only=True)
    payments_statistics = serializers.SerializerMethodField()

    can_be_deleted = serializers.BooleanField(read_only=True)
    grade_questionnaire = serializers.SerializerMethodField()
    is_have_questionnaires = serializers.BooleanField(read_only=True)

    class Meta:
        model = JobPosition
        fields = '__all__'

    def get_project_bugs_statistics(self, obj):
        return obj.project_bugs_statistics

    def get_payments_statistics(self, obj):
        return obj.payments_statistics

    def get_job_contracts(self, obj):
        job_contracts = obj.job_contracts.all().order_by('created_at')
        return JobContractWithPaymentSerializer(job_contracts, read_only=True, many=True).data

    def get_grade_questionnaire(self, obj):
        grade_questionnaires = obj.grade_questionnaires.all()
        grade_questionnaires_data = GradeQuestionnaireSerializer(grade_questionnaires, many=True).data
        return grade_questionnaires_data


class JobPositionWithCommittersSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all())
    developer = DeveloperDashboardCardField(many=False, queryset=Developer.objects.all())
    committers = serializers.SerializerMethodField()

    class Meta:
        model = JobPosition
        fields = '__all__'

    # 接口里处理
    def get_committers(self, obj):
        return None


class ProjectStageCreateSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())

    class Meta:
        model = ProjectStage
        fields = '__all__'


class ProjectWithStagesSerializer(serializers.ModelSerializer):
    project_stages = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'start_date', 'end_date', 'project_stages']

    def get_project_stages(self, obj):
        stages = obj.project_stages.order_by('index')
        return ProjectStageSimpleSerializer(stages, many=True).data


class ProjectStageSimpleSerializer(serializers.ModelSerializer):
    stage_type_display = serializers.CharField(read_only=True)

    class Meta:
        model = ProjectStage
        fields = '__all__'


class ProjectStageEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStage
        fields = ['start_date', 'end_date', 'name', 'index']


class TechnologyCheckpointSerializer(serializers.ModelSerializer):
    project = ProjectWithMembersField(many=False, queryset=Project.objects.all())
    principal = UserField(many=False, queryset=User.objects.all(), required=False)
    status_display = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    quip_document_data = serializers.SerializerMethodField()

    quip_documents = serializers.SerializerMethodField()
    quip_document_ids = serializers.SerializerMethodField()
    project_stage = ProjectStageSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = TechnologyCheckpoint
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_quip_document_data(self, obj):
        return obj.quip_document_data()

    def get_quip_documents(self, obj):
        return obj.quip_documents

    def get_quip_document_ids(self, obj):
        if obj.quip_document_ids:
            return json.loads(obj.quip_document_ids, encoding='utf-8')


class TechnologyCheckpointEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnologyCheckpoint
        fields = ['status', 'expected_at', 'done_at', 'quip_document_ids']
        extra_kwargs = {
            'done_at': {"read_only": True}
        }


class ProjectSimpleSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all(), required=False)
    mentor = UserField(many=False, queryset=User.objects.all(), required=False)
    product_manager = UserField(many=False, queryset=User.objects.all(), required=False)
    tpm = UserField(many=False, queryset=User.objects.all(), required=False)
    test = UserField(many=False, queryset=User.objects.all(), required=False)

    status_display = serializers.CharField(read_only=True)
    tests = UserField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'manager', 'tpm', 'mentor', 'product_manager', 'test', 'status', 'status_display', 'tests')


class ProjectVerySimpleSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all(), required=False)

    class Meta:
        model = Project
        fields = ('id', 'name', 'manager')


class ProjectWithDeveloperListSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all(), required=False)
    mentor = UserField(many=False, queryset=User.objects.all(), required=False)
    product_manager = UserField(many=False, queryset=User.objects.all(), required=False)
    tpm = UserField(many=False, queryset=User.objects.all(), required=False)
    test = UserField(many=False, queryset=User.objects.all(), required=False)

    status_display = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    developers = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    members_dict = serializers.SerializerMethodField()

    tests = UserField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = (
            'id', 'name', 'manager', 'tpm', 'mentor', 'product_manager', 'test', 'status', 'status_display', 'tests',
            'developers', 'members', 'members_dict')

    def get_developers(self, obj):
        return get_project_developers_data(obj)

    def get_members(self, obj):
        return get_project_members_data(obj)

    def get_members_dict(self, obj):
        return get_project_members_dict(obj)


class ProjectDeploymentSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all())
    tpm = UserField(many=False, queryset=User.objects.all(), required=False)
    deployment_servers = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'manager', 'tpm', 'deployment_servers']

    def get_deployment_servers(self, obj):
        if obj.deployment_servers:
            return json.loads(obj.deployment_servers, encoding='utf-8')
        return []


class ProjectWithScheduleSerializer(serializers.ModelSerializer):
    gantt_chart = GanttChartField(many=False, queryset=ProjectGanttChart.objects.all())
    stages = serializers.SerializerMethodField()

    members = serializers.SerializerMethodField()
    members_dict = serializers.SerializerMethodField()
    job_positions = JobSimpleSerializer(many=True, read_only=True)

    schedule_remarks = serializers.SerializerMethodField()
    show_schedule_remarks = serializers.SerializerMethodField()
    work_hour_plans = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'

    def get_stages(self, obj):
        stages = obj.project_stages.order_by('index')
        return ProjectStageSimpleSerializer(stages, many=True).data

    def get_members(self, obj):
        return get_project_members_data(obj)

    def get_members_dict(self, obj):
        return get_project_members_dict(obj)

    def get_schedule_remarks(self, obj):
        comment = obj.comments.filter(codename='schedule_remarks').order_by('-created_at').first()
        if comment:
            return comment.content_text

    def get_show_schedule_remarks(self, obj):
        project_schedule_remarks_hidden_set = cache.get('project_schedule_remarks_hidden_set', set())
        if obj.id in project_schedule_remarks_hidden_set:
            return False
        return True

    def get_work_hour_plans(self, obj):
        project_work_hour_plans = obj.project_work_hour_plans.all()
        work_hour_plan_data = {}
        for project_work_hour_plan in project_work_hour_plans:
            project_work_hour_plan_data = ProjectWorkHourPlanSerializer(project_work_hour_plan).data
            work_hour_record = project_work_hour_plan.work_hour_records.order_by('-modified_at').first()
            work_hour_record_data = {}
            if work_hour_record:
                work_hour_record_data = WorkHourRecordSerializer(work_hour_record).data
                week_consume_days = Decimal(work_hour_record.week_consume_hours / 8).quantize(Decimal("0.1"),
                                                                                              rounding="ROUND_HALF_UP")
                work_hour_record_data['week_consume_days'] = week_consume_days
            project_work_hour_plan_data['work_hour_record_data'] = work_hour_record_data
            role = project_work_hour_plan.role
            if role not in work_hour_plan_data:
                work_hour_plan_data[role] = []
            work_hour_plan_data[role].append(project_work_hour_plan_data)
        return work_hour_plan_data


class ProjectWithWorkHourPlanSerializer(serializers.ModelSerializer):
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)
    members_dict = serializers.SerializerMethodField()
    job_positions = JobSimpleSerializer(many=True, read_only=True)
    roles_work_hour_records = serializers.SerializerMethodField()
    work_hour_plan_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'

    def get_members_dict(self, obj):
        return get_project_members_dict(obj)

    def get_work_hour_plan_count(self, obj):
        return obj.project_work_hour_plans.count()

    def get_roles_work_hour_records(self, obj):
        project_work_hour_plans = obj.project_work_hour_plans.order_by("created_at")
        work_hour_plan_data = {}
        for project_work_hour_plan in project_work_hour_plans:
            project_work_hour_plan_data = ProjectWorkHourPlanSerializer(project_work_hour_plan).data
            work_hour_record = project_work_hour_plan.work_hour_records.order_by('-statistic_end_date').first()
            record_data = None
            if work_hour_record:
                record_data = WorkHourRecordSerializer(work_hour_record).data
                week_consume_days = Decimal(work_hour_record.week_consume_hours / 8).quantize(Decimal("0.1"),
                                                                                              rounding="ROUND_HALF_UP")
                record_data['week_consume_days'] = week_consume_days
                project_work_hour_plan_data['work_hour_record_data'] = record_data
            role = project_work_hour_plan.role
            if role not in work_hour_plan_data:
                work_hour_plan_data[role] = {
                    'statistic_start_date': None,
                    'statistic_end_date': None,
                    'role_plan_data': []}
            if work_hour_record and not work_hour_plan_data[role]['statistic_start_date']:
                work_hour_plan_data[role]['statistic_start_date'] = record_data['statistic_start_date']
                work_hour_plan_data[role]['statistic_end_date'] = record_data['statistic_end_date']
            work_hour_plan_data[role]['role_plan_data'].append(project_work_hour_plan_data)
        return work_hour_plan_data


class ProjectCreateSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all(), required=True)
    bd = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)

    # tpm = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True, allow_blank=True)
    # test = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True, allow_blank=True)
    # mentor = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True, allow_blank=True)
    # product_manager = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True, allow_blank=True)
    # designer = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True, allow_blank=True)
    #
    # desc = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'manager', 'tpm', 'mentor', 'product_manager', 'test', 'designer', 'bd', 'desc',
                  'start_date', 'end_date']


class ProjectSimpleEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['start_date', 'end_date', 'desc']


class ProjectEditSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all())
    mentor = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    product_manager = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    tpm = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    test = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    designer = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    bd = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)

    tests = UserField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'desc',
                  'manager', 'tpm', 'mentor', 'product_manager', 'test', 'designer', 'bd',
                  'deployment_servers', 'tests']
        extra_kwargs = {
            'id': {"read_only": True},
        }


# 外部工程师看到的数据 只能看到特定字段
class ProjectPrototypeDeveloperSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPrototype
        fields = ['id', 'uid', 'cipher', 'title', 'filename', 'version', 'prototype_url', 'created_at', 'modified_at']


# 外部工程师看到的数据 只能看到特定字段
class ProjectDeveloperDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    gantt_chart = GanttChartField(many=False, queryset=ProjectGanttChart.objects.all())
    links = ProjectLinksWithEngineerDocsSerializer(many=False, read_only=True)
    prototypes = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'status', 'status_display', 'status', 'gantt_chart', 'created_at', 'links',
                  'prototypes']

    def get_prototypes(self, obj):
        prototypes = ProjectPrototype.developer_public_prototypes(obj.prototypes.filter(is_deleted=False)).order_by(
            '-created_at')
        data = ProjectPrototypeDeveloperSerializer(prototypes, many=True).data
        return data


# 外部客户看到的数据 只能看到特定字段
class ProjectDetailClientSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    links = ProjectLinksWithEngineerDocsSerializer(many=False, read_only=True)
    manager = UserField(many=False, read_only=True)
    product_manager = UserField(many=False, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'status', 'status_display', 'created_at', 'links', 'manager', 'product_manager']


class ProjectDetailSerializer(serializers.ModelSerializer):
    clients = ClientSimpleSerializer(many=True, read_only=True)
    tests = UserField(many=True, read_only=True)

    manager = UserField(many=False, queryset=User.objects.all())
    product_manager = UserField(many=False, queryset=User.objects.all(), required=False)
    mentor = UserField(many=False, queryset=User.objects.all(), required=False)
    designer = UserField(many=False, queryset=User.objects.all(), required=False)
    tpm = UserField(many=False, queryset=User.objects.all())
    test = UserField(many=False, queryset=User.objects.all())
    bd = UserField(many=False, queryset=User.objects.all())

    members = serializers.SerializerMethodField()
    members_dict = serializers.SerializerMethodField()

    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    serializers.CharField(read_only=True)
    proposal_data = serializers.SerializerMethodField()
    gantt_chart = GanttChartField(many=False, queryset=ProjectGanttChart.objects.all())
    handover_receipt_url = serializers.SerializerMethodField()
    deployment_servers = serializers.SerializerMethodField()
    has_delivery_document = serializers.SerializerMethodField()
    has_job_role = serializers.SerializerMethodField()
    links = ProjectLinksDetailSerializer(many=False, read_only=True)
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'

    def get_has_job_role(self, obj):
        return obj.job_positions.exists()

    def get_has_delivery_document(self, obj):
        return obj.has_delivery_document()

    def get_deployment_servers(self, obj):
        if obj.deployment_servers:
            return json.loads(obj.deployment_servers, encoding='utf-8')
        return []

    def get_proposal_data(self, obj):
        if Proposal.objects.filter(project_id=obj.id).exists():
            quip_folder = obj.proposal.quip_folder
            quip_doc = obj.proposal.quip_doc()
            latest_report = obj.proposal.latest_report_data()
            has_share_link = False
            if any([quip_folder, quip_doc, latest_report]):
                has_share_link = True
            return {"quip_folder": quip_folder, "quip_doc": quip_doc, 'latest_report': latest_report,
                    'id': obj.proposal.id, 'name': obj.proposal.name, 'has_share_link': has_share_link}
        else:
            return None

    def get_handover_receipt_url(self, obj):
        if Proposal.objects.filter(project_id=obj.id).exists():
            if HandoverReceipt.objects.filter(proposal_id=obj.proposal.id).exists():
                url = '/proposals/detail/handover_receipt/?proposalId={}'.format(obj.proposal.id)
                return url

    def get_members(self, obj):
        return get_project_members_data(obj)

    def get_members_dict(self, obj):
        return get_project_members_dict(obj)


class ProjectMembersSerializer(serializers.ModelSerializer):
    manager = UserField(many=False, queryset=User.objects.all(), required=False)
    mentor = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    product_manager = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)

    tpm = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    test = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    designer = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    bd = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)

    tests = UserField(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'manager', 'tpm', 'test', 'mentor', 'product_manager', 'bd', 'designer', 'tests']

    extra_kwargs = {
        'id': {"read_only": True},
        'name': {"read_only": True},
    }


# 配置gitlab committer页面

class ProjectGitlabCommittersSerializer(serializers.ModelSerializer):
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)
    members = serializers.SerializerMethodField()
    job_positions = serializers.SerializerMethodField()
    committers = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()
    gitlab_project = serializers.SerializerMethodField()

    class Meta:
        model = Project

        fields = ["id", "name", "current_stages", "members", "job_positions", "committers",
                  "gitlab_project", "links"]

    def get_links(self, obj):
        if getattr(obj, 'links', None):
            obj_links = obj.links
            return {"gitlab_group_id": obj_links.gitlab_group_id, "gitlab_project_id": obj_links.gitlab_project_id}

    # 接口里处理
    def get_gitlab_project(self, obj):
        return None

    def get_committers(self, obj):
        return None

    def get_members(self, obj):
        return get_project_members_data(obj)

    def get_job_positions(self, obj):
        positions = obj.job_positions.all()
        developer_ids = set()
        clean_positions = []
        for position in positions:
            if position.developer_id not in developer_ids:
                clean_positions.append(position)
                developer_ids.add(position.developer_id)
        return JobPositionWithCommittersSerializer(clean_positions, many=True).data


# 全部列表页面
class ProjectsPageSerializer(serializers.ModelSerializer):
    undone_tasks = TaskSerializer(many=True, read_only=True)
    manager = UserField(many=False, queryset=User.objects.all())
    tpm = UserField(many=False, queryset=User.objects.all(), required=False)
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'


# 全部列表页面
class ProjectsManageSerializer(serializers.ModelSerializer):
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)
    manager = UserField(many=False, queryset=User.objects.all())
    members = serializers.SerializerMethodField()

    links = ProjectLinksDetailSerializer(many=False, read_only=True)
    deployment_servers = serializers.SerializerMethodField()

    this_week_daily_works_statistics = serializers.SerializerMethodField()
    daily_works_statistics = serializers.SerializerMethodField()

    last_gantt_update = serializers.SerializerMethodField()
    last_email_record = serializers.SerializerMethodField()
    playbook_stages = serializers.SerializerMethodField()
    payments_statistics = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'manager', 'members', 'current_stages', 'links', 'deployment_servers',
                  'daily_works_statistics',
                  'this_week_daily_works_statistics', 'last_gantt_update', 'last_email_record', 'playbook_stages',
                  'payments_statistics']

    def get_payments_statistics(self, obj):
        paid_stage_count = 0
        need_paid_stage_count = 0
        for payment in obj.project_payments.exclude(status='termination'):
            need_paid_stage_count += payment.need_paid_stage_count
            paid_stage_count += payment.paid_stage_count
        return {"paid_stage_count": paid_stage_count, "need_paid_stage_count": need_paid_stage_count}

    def get_playbook_stages(self, obj):
        cache_key = 'project_{}_playbook_stages'.format(obj.id)
        data = cache.get(cache_key, None)
        if data is None:
            product_manager_stages = obj.playbook_stages.filter(member_type='product_manager')
            manager_stages = obj.playbook_stages.filter(member_type='manager').order_by('index')
            data = []
            for index, manager_stage in enumerate(manager_stages):
                if manager_stage.is_next_stage:
                    continue
                manager_data = {"check_group_total": manager_stage.check_groups.count(),
                                "finished_check_group_count": manager_stage.check_groups.filter(
                                    completed_at__isnull=False).count()}

                product_manager_data = None
                product_manager_stage = product_manager_stages.filter(name=manager_stage.name).first()
                if product_manager_stage:
                    product_manager_data = {
                        "check_group_total": product_manager_stage.check_groups.count(),
                        "finished_check_group_count": product_manager_stage.check_groups.filter(
                            completed_at__isnull=False).count()}
                stage_data = {
                    'stage_name': manager_stage.name,
                    "manager_data": manager_data,
                    "product_manager_data": product_manager_data
                }
                data.append(stage_data)
            cache.set(cache_key, data, 60 * 60 * 1)
        return data

    def get_deployment_servers(self, obj):
        if obj.deployment_servers:
            return json.loads(obj.deployment_servers, encoding='utf-8')
        return []

    def get_last_email_record(self, obj):
        last_email_record = obj.email_records.filter(status=1).order_by('-sent_at').first()
        if last_email_record:
            return {'sent_at': last_email_record.sent_at.strftime(settings.DATETIME_FORMAT)}

    def get_last_gantt_update(self, obj):
        if getattr(obj, 'gantt_chart', None):
            gantt_chart = obj.gantt_chart
            task = gantt_chart.task_topics.order_by('-modified_at').first()
            if task:
                return {'modified_at': task.modified_at.strftime(settings.DATETIME_FORMAT)}

    def get_members(self, obj):
        return get_project_members_data(obj)

    def get_this_week_daily_works_statistics(self, obj):
        # 最近7天的打卡统计
        cache_key = 'project_{}_recent_daily_works_statistic_data'.format(obj.id)
        data = cache.get(cache_key, None)
        if data is None:
            start_date = timezone.now().date() - timedelta(days=6)
            data = self.get_date_daily_works_statistics(obj, start_date)
            cache.set(cache_key, data, 60 * 60 * 2)
        return data

    def get_daily_works_statistics(self, obj):
        # 全部打卡统计
        cache_key = 'project_{}_daily_works_statistic_data'.format(obj.id)
        data = cache.get(cache_key, None)
        if data is None:
            data = self.get_date_daily_works_statistics(obj, None)
            cache.set(cache_key, data, 60 * 60 * 3)
        return data

    def get_date_daily_works_statistics(self, obj, start_date):
        from developers.utils import get_need_submit_daily_work
        developers_dict = {}
        users_read_dict = {}
        project = obj
        today = timezone.now().date()
        developers = project.get_active_developers()
        for developer in developers:
            developers_dict[developer.id] = {"punched_days": set(), "need_punched_days": set(), "id": developer.id,
                                             "name": developer.name}
            if get_need_submit_daily_work(project, developer, today):
                developers_dict[developer.id]["need_punched_days"].add(today.strftime(settings.DATE_FORMAT))

        # punched_daily_works = set()
        # 日报记录
        daily_works = project.daily_works.exclude(status="pending").filter(day__lte=today)
        if start_date:
            daily_works = daily_works.filter(day__gte=start_date)
        need_read_daily_works = len(daily_works)

        member_ids = set()
        project_member_fields = [
            {"field_name": 'manager', "name": "项目经理", "short_name": 'PMO'},
            {"field_name": 'product_manager', "name": "产品", "short_name": 'PM'},
            {"field_name": 'tpm', "name": "TPM", "short_name": 'TPM'},
        ]
        for member_field in project_member_fields:
            member = getattr(project, member_field['field_name'], None)
            if member:
                member_ids.add(member.id)

        for daily_work in daily_works:
            day_str = daily_work.day.strftime(settings.DATE_FORMAT)
            developer = daily_work.developer

            if developer.id not in developers_dict:
                developers_dict[developer.id] = {"punched_days": set(), "need_punched_days": set(),
                                                 "id": developer.id,
                                                 "name": developer.name}
            if daily_work.status != 'absence':
                developers_dict[developer.id]["punched_days"].add(day_str)
                # punched_daily_works.add(daily_work)
            # 只要打卡了 都统计到需要打卡中
            developers_dict[developer.id]["need_punched_days"].add(day_str)

            if member_ids:
                for browsing_history in daily_work.browsing_histories.filter(visitor_id__in=member_ids):
                    visitor_id = browsing_history.visitor_id
                    if visitor_id:
                        if visitor_id not in users_read_dict:
                            users_read_dict[visitor_id] = set()
                        users_read_dict[visitor_id].add(daily_work)

        existed_members = set()
        members_data = []
        for member_field in project_member_fields:
            member = getattr(project, member_field['field_name'], None)
            if member and member.id not in existed_members:
                member_data = {"role": member_field, "username": member.username, 'id': member.id,
                               "read_daily_works_count": 0,
                               "need_read_daily_works": need_read_daily_works}
                if member.id in users_read_dict:
                    member_data['read_daily_works_count'] = len(users_read_dict[member.id])
                members_data.append(member_data)
                existed_members.add(member.id)
        developers_data = []
        for developer_data in developers_dict.values():
            item_data = deepcopy(developer_data)
            item_data['need_punched_days_count'] = len(item_data['need_punched_days'])
            item_data['punched_days_count'] = len(item_data['punched_days'])
            developers_data.append(item_data)
        data = {"developer": developers_data, "members": members_data}
        return data


class DeliveryDocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryDocumentType
        fields = '__all__'


class DeliveryDocumentSerializer(serializers.ModelSerializer):
    project = ProjectSimpleField(many=False, queryset=Project.objects.all())
    document_type = DeliveryDocumentTypeField(many=False, queryset=DeliveryDocumentType.objects.all())
    uid = serializers.CharField()
    document_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DeliveryDocument
        fields = '__all__'

    def get_document_url(self, obj):
        if obj.document_type.number == DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER:
            return settings.PROJECT_DELIVERY_DOCUMENTS_HOST + build_page_path("project_delivery_document_download",
                                                                              kwargs={"uid": obj.uid})


class ProjectContractSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    file = serializers.FileField(required=False)

    class Meta:
        model = ProjectContract
        fields = '__all__'


class ProjectWithContractSerializer(serializers.ModelSerializer):
    contracts = ProjectContractSerializer(many=True, read_only=True)
    status_display = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'created_at', 'done_at', 'status_display', 'contracts', "status")


class ProjectPrototypeSerializer(serializers.ModelSerializer):
    project = ProjectSimpleField(many=False, queryset=Project.objects.all())
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    prototype_url = serializers.CharField(read_only=True)
    public_status_display = serializers.CharField(read_only=True)

    class Meta:
        model = ProjectPrototype
        fields = '__all__'


class ProjectPrototypeContentTypeSerializer(serializers.ModelSerializer):
    app_label = serializers.SerializerMethodField(read_only=True)
    model = serializers.SerializerMethodField(read_only=True)
    object_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProjectPrototype
        fields = ['id', 'title', 'uid', 'app_label', 'model', 'object_id']

    def get_object_id(self, obj):
        return obj.id

    def get_app_label(self, obj):
        return 'projects'

    def get_model(self, obj):
        return 'projectprototype'


class ProjectPrototypeDetailSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all(), required=False)
    file = serializers.FileField(required=False)
    uid = serializers.CharField(required=False)
    prototype_url = serializers.CharField(read_only=True)
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    public_status_display = serializers.CharField(read_only=True)

    class Meta:
        model = ProjectPrototype
        fields = '__all__'


class ProjectPrototypeWithBrowsingHistorySerializer(serializers.ModelSerializer):
    browsing_histories = BrowsingHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ProjectPrototype
        fields = ('id', 'title', 'version', 'prototype_url', 'browsing_histories')


class PrototypeCommentPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrototypeCommentPoint
        fields = '__all__'


class PrototypeCommentPointWithCommentsSerializer(serializers.ModelSerializer):
    comments = serializers.SerializerMethodField(read_only=True)

    # comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = PrototypeCommentPoint
        fields = '__all__'

    def get_comments(self, obj):
        comments = obj.comments.order_by('created_at')
        return CommentSerializer(comments, many=True).data


class GanttRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GanttRole
        fields = '__all__'


class GanttRoleWithUserSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all(), required=False, allow_null=True)
    user = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)

    class Meta:
        model = GanttRole
        fields = '__all__'


class ProjectGanttChartRetrieveSerializer(serializers.ModelSerializer):
    project = ProjectSimpleField(many=False, queryset=Project.objects.all())

    roles = GanttRoleWithUserSerializer(many=True, read_only=True)
    task_catalogues = GanttTaskCatalogueField(many=True, read_only=True)

    start_time = serializers.SerializerMethodField(read_only=True)
    finish_time = serializers.SerializerMethodField(read_only=True)

    project_stages = serializers.SerializerMethodField(read_only=True)
    uid = serializers.SerializerMethodField(read_only=True)
    share_link = serializers.SerializerMethodField(read_only=True)
    need_update_template = serializers.BooleanField(read_only=True)
    template_init_status_display = serializers.CharField()

    class Meta:
        model = ProjectGanttChart
        fields = '__all__'

    def get_finish_time(self, obj):
        finish_time = obj.project.end_date
        task_topic = obj.task_topics.order_by('-expected_finish_time').first()
        if task_topic:
            if not finish_time:
                finish_time = task_topic.expected_finish_time
            elif task_topic.expected_finish_time > finish_time:
                finish_time = task_topic.expected_finish_time
        return finish_time

    def get_start_time(self, obj):
        start_time = obj.project.start_date
        task_topic = obj.task_topics.order_by('start_time').first()
        if task_topic:
            if not start_time:
                start_time = task_topic.start_time
            elif task_topic.start_time < start_time:
                start_time = task_topic.start_time
        return start_time

    def get_project_stages(self, obj):
        stages = obj.project.project_stages.all()
        return ProjectStageCreateSerializer(stages, many=True).data

    def get_uid(self, obj):
        if not obj.uid:
            obj.uid = gen_uuid()
            obj.save()
        return obj.uid

    def get_share_link(self, obj):
        if obj.uid:
            share_link = settings.REPORTS_HOST + '/projects/gantt_charts/view/?uid={}'.format(obj.uid)
            return share_link


class GanttTaskTopicCleanSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField(read_only=True)
    number = serializers.IntegerField(required=False)
    catalogue = GanttTaskCatalogueField(many=False, queryset=GanttTaskCatalogue.objects.all(), required=False)
    gantt_chart = GanttChartWithProjectField(many=False, queryset=ProjectGanttChart.objects.all())
    role = GanttRoleWithUserSerializer(many=False)
    half_day_position_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GanttTaskTopic
        fields = '__all__'

    def get_type(self, obj):
        return 'topic'

    def get_half_day_position_display(self, obj):
        return obj.get_half_day_position_display()


class GanttTaskCatalogueCleanSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField(read_only=True)
    task_topics = serializers.SerializerMethodField(read_only=True)
    number = serializers.IntegerField(required=False)

    class Meta:
        model = GanttTaskCatalogue
        fields = '__all__'

    def get_type(self, obj):
        return 'catalogue'

    def get_task_topics(self, obj):
        return []


class GanttTaskTopicTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GanttTaskTopic
        fields = ['id', 'expected_finish_time', 'start_time']


class GanttTaskTopicCreateSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField(read_only=True)
    number = serializers.IntegerField(required=False)
    catalogue = GanttTaskCatalogueField(many=False, queryset=GanttTaskCatalogue.objects.all(), required=False)
    gantt_chart = GanttChartWithProjectField(many=False, queryset=ProjectGanttChart.objects.all())
    role = GanttRoleField(many=False, queryset=GanttRole.objects.all())

    half_day_position_display = serializers.SerializerMethodField(read_only=True)

    is_deleted = serializers.SerializerMethodField(read_only=True)
    last_week_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GanttTaskTopic
        fields = '__all__'

    def get_type(self, obj):
        return 'topic'

    def get_half_day_position_display(self, obj):
        return obj.get_half_day_position_display()

    def get_is_deleted(self, obj):
        return False

    def get_last_week_data(self, obj):
        return None


class GanttTaskTopicSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField(read_only=True)
    number = serializers.IntegerField(required=False)
    catalogue = GanttTaskCatalogueField(many=False, queryset=GanttTaskCatalogue.objects.all(), required=False)
    gantt_chart = GanttChartWithProjectField(many=False, queryset=ProjectGanttChart.objects.all())
    role = GanttRoleWithUserSerializer(many=False)
    half_day_position_display = serializers.SerializerMethodField(read_only=True)
    is_deleted = serializers.SerializerMethodField(read_only=True)
    last_week_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GanttTaskTopic
        fields = '__all__'

    def get_type(self, obj):
        return 'topic'

    def get_half_day_position_display(self, obj):
        return obj.get_half_day_position_display()

    def get_is_deleted(self, obj):
        return False

    def get_last_week_data(self, obj):
        return None


class GanttTaskCatalogueSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField(read_only=True)
    task_topics = serializers.SerializerMethodField(read_only=True)
    number = serializers.IntegerField(required=False)
    is_deleted = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GanttTaskCatalogue
        fields = '__all__'

    def get_type(self, obj):
        return 'catalogue'

    def get_task_topics(self, obj):
        task_topics = obj.task_topics.all().order_by('number', 'id')
        data = GanttTaskTopicSerializer(task_topics, many=True).data
        return data

    def get_is_deleted(self, obj):
        return False


class JobPositionCandidateViewSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    handler = serializers.SerializerMethodField(read_only=True)

    is_first_collaboration = serializers.SerializerMethodField(read_only=True)
    position_need = PositionNeedField(many=False, queryset=JobPositionNeed.objects.all())
    created_at = serializers.DateTimeField(read_only=True)
    confirmed_at = serializers.DateTimeField(read_only=True)
    project = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JobPositionCandidate
        fields = '__all__'

    def get_project(self, obj):
        project = obj.position_need.project
        if project:
            manager_data = None
            if project.manager_id and User.objects.filter(
                    pk=project.manager_id).exists():
                manager_data = get_user_data(project.manager)
            return {"id": project.pk, "name": project.name, 'manager': manager_data}

    def get_is_first_collaboration(self, obj):
        if obj.is_first_collaboration is None:
            is_first_collaboration = True
            if obj.developer.job_positions.exists():
                is_first_collaboration = False
            obj.is_first_collaboration = is_first_collaboration
            obj.save()
        return obj.is_first_collaboration

    def get_handler(self, obj):
        if obj.handler:
            return get_user_data(obj.handler)
        elif obj.position_need.project:
            return get_user_data(obj.position_need.project.manager)

    def get_status_display(self, obj):
        return obj.get_status_display()


class JobPositionCandidateSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)

    is_first_collaboration = serializers.SerializerMethodField(read_only=True)
    position_need = PositionNeedField(many=False, queryset=JobPositionNeed.objects.all())
    created_at = serializers.DateTimeField(read_only=True)
    confirmed_at = serializers.DateTimeField(read_only=True)
    project = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = JobPositionCandidate
        fields = '__all__'

    def get_project(self, obj):
        project = obj.position_need.project
        if project:
            manager_data = None
            if project.manager_id and User.objects.filter(
                    pk=project.manager_id).exists():
                manager_data = get_user_data(project.manager)
            return {"id": project.pk, "name": project.name, 'manager': manager_data}

    def get_is_first_collaboration(self, obj):
        if obj.is_first_collaboration is None:
            is_first_collaboration = True
            if obj.developer.job_positions.exists():
                is_first_collaboration = False
            obj.is_first_collaboration = is_first_collaboration
            obj.save()
        return obj.is_first_collaboration


class JobPositionNeedSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all(), required=False)
    project = ProjectField(many=False, queryset=Project.objects.all(), required=False)
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    principal = UserField(many=False, queryset=User.objects.all(), required=False)
    candidates = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    expected_date = serializers.DateField()
    confirmed_at = serializers.DateTimeField(read_only=True)
    need_new_candidate = serializers.BooleanField(read_only=True)
    status_display = serializers.SerializerMethodField(read_only=True)
    is_today = serializers.BooleanField(required=False, read_only=True)
    is_past = serializers.BooleanField(required=False, read_only=True)
    remaining_days = serializers.IntegerField(required=False, read_only=True)

    class Meta:
        model = JobPositionNeed
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_candidates(self, obj):
        candidates = obj.candidates.order_by('created_at')
        return JobPositionCandidateViewSerializer(candidates, many=True).data


class PositionNeedCreateSerializer(serializers.ModelSerializer):
    role_remarks = serializers.CharField(required=False, allow_null=True)
    expected_date = serializers.DateField()
    period = serializers.FloatField(required=False, allow_null=True)
    remarks = serializers.CharField()

    class Meta:
        model = JobPositionNeed
        fields = ['project', 'role', 'role_remarks', 'expected_date', 'period', 'remarks', 'submitter']


class PositionNeedEditSerializer(serializers.ModelSerializer):
    expected_date = serializers.DateField()
    remarks = serializers.CharField()
    period = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = JobPositionNeed
        fields = ['expected_date', 'remarks', 'period']


class GanttTaskTopicStartTimeSerializer(serializers.ModelSerializer):
    start_time = serializers.DateField()

    class Meta:
        model = GanttTaskTopic
        fields = ['start_time', ]


class GanttTaskTopicWorkDateSerializer(serializers.ModelSerializer):
    expected_finish_time = serializers.DateField()
    start_time = serializers.DateField()

    class Meta:
        model = GanttTaskTopic
        fields = ['expected_finish_time', 'start_time']


class ClientCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCalendar
        fields = '__all__'

    def save_to_cache(self, validated_data):
        calendar = ClientCalendar(**validated_data)
        calendar.period_days = calendar.build_period_days()
        cache.set('calendar' + calendar.uid, calendar, 600)
        return calendar

    def update_to_cache(self, instance, validated_data):
        for field_name in validated_data:
            field_value = validated_data.get(field_name, getattr(instance, field_name))
            setattr(instance, field_name, field_value)
        instance.period_days = instance.build_period_days()
        cache.set('calendar' + instance.uid, instance, 600)
        return instance


class ClientCalendarReadOnlySerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    share_link = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    period_days = serializers.IntegerField(read_only=True)
    remaining_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClientCalendar
        fields = '__all__'

    def get_share_link(self, obj):
        if obj.uid:
            share_link = settings.REPORTS_HOST + build_page_path("project_calendar_detail", kwargs={"uid": obj.uid})
            return share_link

    def get_created_at(self, obj):
        if obj.created_at:
            created_at = obj.created_at
            created_at = "{}年{}月{}日".format(created_at.year, created_at.month, created_at.day)
            return created_at


class ClientCalendarSimpleSerializer(serializers.ModelSerializer):
    share_link = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    project = ProjectField(many=False, queryset=Project.objects.all())
    created_at = serializers.DateTimeField(format=settings.SAMPLE_DATE_FORMAT, read_only=True)
    creator = UserField(many=False, queryset=User.objects.all(), required=False)

    class Meta:
        model = ClientCalendar
        fields = ['project', 'created_at', 'share_link', 'title', 'uid', 'creator', 'is_public']

    def get_share_link(self, obj):
        if obj.uid:
            share_link = settings.REPORTS_HOST + build_page_path("project_calendar_detail", kwargs={"uid": obj.uid})
            return share_link

    def get_title(self, obj):
        return obj.get_title()


class ProjectWorkHourPlanCreateSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    developer = DeveloperField(many=False, queryset=Developer.objects.all(), required=False, allow_null=True)
    user = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)

    class Meta:
        model = ProjectWorkHourPlan
        fields = '__all__'


class ProjectWorkHourPlanEditSerializer(serializers.ModelSerializer):
    developer = DeveloperField(many=False, queryset=Developer.objects.all(), required=False, allow_null=True)
    user = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)

    class Meta:
        model = ProjectWorkHourPlan
        fields = ['role', 'developer', 'user', 'plan_consume_days']


class ProjectWorkHourPlanSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    developer = DeveloperField(many=False, queryset=Developer.objects.all(), required=False, allow_null=True)
    user = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    role_display = serializers.SerializerMethodField(read_only=True)
    last_predict_residue_days = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProjectWorkHourPlan
        fields = '__all__'

    def get_role_display(self, obj):
        return obj.get_role_display()

    def get_last_predict_residue_days(self, obj):
        last_record = obj.work_hour_records.all().order_by('-statistic_end_date').first()
        if last_record:
            return last_record.predict_residue_days


class ProjectWorkHourPlanField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = ProjectWorkHourPlan.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id, 'role': obj.role,
                    'developer_name': obj.developer.name if obj.developer else '',
                    'username': obj.user.username if obj.user else ''}


class WorkHourRecordCreateSerializer(serializers.ModelSerializer):
    project_work_hour_plan = ProjectWorkHourPlanField(queryset=ProjectWorkHourPlan.objects.all())

    class Meta:
        model = WorkHourRecord
        fields = '__all__'


class WorkHourRecordEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkHourRecord
        fields = ['week_consume_hours', 'predict_residue_days', 'statistic_start_date', 'statistic_end_date']


class WorkHourRecordSerializer(serializers.ModelSerializer):
    project_work_hour_plan = ProjectWorkHourPlanField(queryset=ProjectWorkHourPlan.objects.all())

    class Meta:
        model = WorkHourRecord
        fields = '__all__'


class ProjectWorkHourOperationLogSerializer(serializers.ModelSerializer):
    project_work_hour = ProjectWorkHourPlanField(queryset=WorkHourRecord.objects.all())
    operator = UserField(many=False, queryset=User.objects.all())
    log_type_display = serializers.SerializerMethodField()

    class Meta:
        model = ProjectWorkHourOperationLog
        fields = '__all__'

    def get_log_type_display(self, obj):
        return obj.get_log_type_display()


class QuestionnaireField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = Questionnaire.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id}


class QuestionField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = Question.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id, 'title': obj.title}


class ChoiceField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = Choice.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id, 'choice': obj.choice}


class GradeQuestionnaireField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = GradeQuestionnaire.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id}


class QuestionnaireSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    statistic_data = serializers.SerializerMethodField()

    class Meta:
        model = Questionnaire
        fields = '__all__'

    def get_questions(self, obj):
        questions = obj.questions.all().order_by('index')
        questions_data = QuestionSerializer(questions, many=True).data
        return questions_data

    def get_statistic_data(self, obj):
        grade_questionnaires = obj.grade_questionnaires.filter(is_skip_grade=False)
        submit_count = grade_questionnaires.count()
        stage1 = 0
        stage2 = 0
        stage3 = 0
        total_score = 0
        for grade_questionnaire in grade_questionnaires:
            job_reference_score = JobReferenceScore.objects.filter(job_position=grade_questionnaire.job_position,
                                                                   score_person=grade_questionnaire.score_person).first()
            if job_reference_score:
                score = job_reference_score.average_score if job_reference_score.average_score else 0
                if 1 <= score <= 3.4:
                    stage1 += 1
                if 3.5 <= score <= 4.4:
                    stage2 += 1
                if 4.5 <= score <= 5:
                    stage3 += 1
                total_score += score
        average_score = round(total_score / submit_count, 1) if submit_count else 0
        data = {'submit_count': submit_count, '1~3.4': stage1, '3.5~4.4': stage2, '4.5~5': stage3,
                'average_score': average_score}
        return data


class QuestionSerializer(serializers.ModelSerializer):
    questionnaire = QuestionnaireField(queryset=Questionnaire.objects.all())
    choices = serializers.SerializerMethodField()
    statistic_data = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = '__all__'

    def get_choices(self, obj):
        choices = obj.choices.all().order_by('index')
        choices_data = ChoiceCreateSerializer(choices, many=True).data
        return choices_data

    def get_statistic_data(self, obj):
        answer_sheets = obj.answer_sheets.filter(choice__isnull=False)
        submit_count = answer_sheets.count()
        stage1 = 0
        stage2 = 0
        stage3 = 0
        total_score = 0
        for answer_sheet in answer_sheets:
            score = answer_sheet.choice.score if answer_sheet.choice else 0
            if score:
                if 1 <= score <= 3.4:
                    stage1 += 1
                if 3.5 <= score <= 4.4:
                    stage2 += 1
                if 4.5 <= score <= 5:
                    stage3 += 1
                total_score += score
        average_score = round(total_score / submit_count, 1) if submit_count else 0
        data = {'submit_count': submit_count, '1~3.4': stage1, '3.5~4.4': stage2, '4.5~5': stage3,
                'average_score': average_score}
        return data


class QuestionnaireCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Questionnaire
        fields = '__all__'


class QuestionCreateSerializer(serializers.ModelSerializer):
    questionnaire = QuestionnaireField(queryset=Questionnaire.objects.all())

    class Meta:
        model = Question
        fields = '__all__'


class QuestionEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        exclude = ['questionnaire', 'type', 'index']


class ChoiceCreateSerializer(serializers.ModelSerializer):
    question = QuestionField(queryset=Question.objects.all())

    class Meta:
        model = Choice
        fields = '__all__'


class ChoiceEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        exclude = ['question', 'index']


class AnswerSheetSerializer(serializers.ModelSerializer):
    question = QuestionField(queryset=Question.objects.all())
    choice = ChoiceField(queryset=Choice.objects.all())

    class Meta:
        model = AnswerSheet
        fields = '__all__'


class AnswerSheetCreateSerializer(serializers.ModelSerializer):
    grade_questionnaire = GradeQuestionnaireField(queryset=GradeQuestionnaire.objects.all())
    question = QuestionField(queryset=Question.objects.all())
    choice = ChoiceField(queryset=Choice.objects.all(), allow_null=True)

    class Meta:
        model = AnswerSheet
        fields = '__all__'


class GradeQuestionnaireCreateSerializer(serializers.ModelSerializer):
    score_person = UserField(queryset=User.objects.all())
    questionnaire = QuestionnaireField(queryset=Questionnaire.objects.all())
    job_position = JobField(queryset=JobPosition.objects.all())

    class Meta:
        model = GradeQuestionnaire
        fields = '__all__'


class GradeQuestionnaireSerializer(serializers.ModelSerializer):
    score_person = UserField(queryset=User.objects.all())
    questionnaire = serializers.SerializerMethodField()
    job_position = JobField(queryset=JobPosition.objects.all())

    class Meta:
        model = GradeQuestionnaire
        fields = '__all__'

    def get_questionnaire(self, obj):
        return QuestionnaireSerializer(obj.questionnaire).data


class JobPositionWithQuestionnaire(serializers.ModelSerializer):
    role = RoleField(many=False, queryset=Role.objects.all())
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    need_star_rating_members = serializers.SerializerMethodField()

    class Meta:
        model = JobPosition
        fields = '__all__'

    def get_need_star_rating_members(self, obj):
        members = set()
        for field_name in Project.NEED_STAR_RATING_MEMBERS_FIELDS:
            if field_name == 'tests':
                tests = getattr(obj.project, field_name).all()
                for test in tests:
                    if test.is_active:
                        members.add(test)
            else:
                member = getattr(obj.project, field_name, None)
                if member and member.is_active:
                    members.add(member)
        members_data = []
        for member in members:
            member_data = get_user_data(member)
            member_data['is_grade'] = False
            member_data['is_skip_grade'] = False
            member_data['is_questionnaire'] = False
            user_id = int(member_data['id'])
            role = None
            if obj.project.tests.all():
                for test in obj.project.tests.all():
                    if user_id == test.id:
                        role = 'test'
            if obj.project.designer:
                if user_id == obj.project.designer.id:
                    role = 'designer'
            if obj.project.tpm:
                if user_id == obj.project.tpm.id:
                    role = 'tpm'
            if obj.project.manager:
                if user_id == obj.project.manager.id:
                    role = 'manager'
            if obj.project.product_manager:
                if user_id == obj.project.product_manager.id:
                    role = 'manager'
            job_position_role = 'developer'
            if obj.role.name in '测试工程师':
                job_position_role = 'test'
            elif obj.role.name in '设计师':
                job_position_role = 'designer'
            questionnaire = Questionnaire.objects.filter(written_by=role, engineer_type=job_position_role,
                                                         status='online').first()
            if questionnaire:
                member_data['is_questionnaire'] = True
            grade_questionnaire = member.grade_questionnaires.filter(job_position=obj).first()
            if grade_questionnaire:
                member_data['is_grade'] = True
                if grade_questionnaire.is_skip_grade:
                    member_data['is_skip_grade'] = True
            members_data.append(member_data)
        return members_data


class JobStandardScoreWithGradeSerializer(serializers.ModelSerializer):
    job_position = serializers.PrimaryKeyRelatedField(many=False, queryset=JobPosition.objects.all())
    total_rate = serializers.FloatField(read_only=True)
    average_score = serializers.FloatField(read_only=True)
    total = serializers.FloatField(read_only=True)
    average = serializers.FloatField(read_only=True)
    score_person = UserField(many=False, queryset=User.objects.all(), required=False)
    grade_questionnaires = serializers.SerializerMethodField()

    class Meta:
        model = JobStandardScore
        fields = '__all__'

    def get_grade_questionnaires(self, obj):
        job_position = obj.job_position
        grade_questionnaires = job_position.grade_questionnaires.all()
        grade_questionnaires_data = GradeQuestionnaireSerializer(grade_questionnaires, many=True).data
        if grade_questionnaires_data:
            for grade_questionnaire in grade_questionnaires_data:
                for question in grade_questionnaire['questionnaire']['questions']:
                    answer_sheet = AnswerSheet.objects.filter(question=question['id'],
                                                              grade_questionnaire_id=grade_questionnaire['id']).first()
                    answer_sheet_data = AnswerSheetSerializer(answer_sheet).data
                    question['answer'] = answer_sheet_data
        return grade_questionnaires_data
