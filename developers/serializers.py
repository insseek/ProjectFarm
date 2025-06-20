import json

from django.core.cache import cache
from django.contrib.auth.models import Group, User
from django.conf import settings
from rest_framework import serializers

from farmbase.utils import gen_uuid, get_user_data
from developers.models import Developer, Role, DailyWork, Document, DocumentSyncLog, DocumentVersion, DocumentReadLog
from developers.utils import get_project_developer_daily_works_statistics
from reports.serializers import TagField
from projects.models import Project, GanttTaskTopic
from projects.serializers import JobSerializer, JobPositionCandidateViewSerializer, \
    ProjectField, ProjectStageSimpleSerializer
from finance.models import JobPayment
from geargitlab.tasks import get_gitlab_user_data, get_gitlab_user_simple_data
from farmbase.serializers import UserField
from auth_top.serializers import TopUserViewSerializer, TopUser


class JobPaymentDateSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    start_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateField(read_only=True)

    class Meta:
        model = JobPayment
        fields = ['created_at', 'start_at', 'completed_at', 'status', 'amount']


class JobPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPayment
        fields = '__all__'


class ProjectSimpleSerializer(serializers.ModelSerializer):
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "done_at", 'status', 'status_display', 'current_stages']


class DeveloperField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        developer = Developer.objects.get(pk=value.pk)
        avatar = None
        if developer.avatar:
            avatar = developer.avatar.url

        last_login = developer.last_login.strftime(settings.DATETIME_FORMAT) if developer.last_login else None
        dict = {"id": value.pk, "name": developer.name, 'username': developer.name, 'phone': developer.phone,
                'avatar': avatar, 'avatar_url': avatar, "payment_info": developer.payment_info,
                'gitlab_user_id': developer.gitlab_user_id, 'last_login': last_login,
                'is_active': developer.is_active}
        return dict


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


class DocumentVersionField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        role = DocumentVersion.objects.get(pk=value.pk)
        dict = {"id": value.pk, "version": role.version}
        return dict


class RoleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        role = Role.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": role.name}
        return dict


class DeveloperSimpleSerializer(serializers.ModelSerializer):
    roles = RoleField(many=True, queryset=Role.objects.all())
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Developer
        fields = ["id", "name", "roles", 'avatar_url', 'avatar', 'last_login', 'is_active', 'payment_info',
                  'gitlab_user_id']

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url


class DeveloperVerySimpleSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Developer
        fields = ["id", "name", 'username']

    def get_username(self, obj):
        return obj.name


class DeveloperAvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = ['avatar']


class DeveloperCreateSerializer(serializers.ModelSerializer):
    roles = RoleField(many=True, queryset=Role.objects.all())

    class Meta:
        model = Developer
        exclude = ['id', 'modified_at', 'created_at']


class DeveloperCompileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        exclude = ['id', 'modified_at', 'created_at', 'roles']


class DeveloperEditSerializer(serializers.ModelSerializer):
    roles = RoleField(many=True, queryset=Role.objects.all(), required=False)
    name = serializers.CharField(required=False)

    class Meta:
        model = Developer
        exclude = ['id', 'modified_at', 'created_at']


class DeveloperOpenApiEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        exclude = ['id', 'name', 'phone', 'modified_at', 'created_at', 'roles',
                   'is_active']


class DeveloperRealNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = (
            'name', 'id_card_number', 'phone', 'front_side_of_id_card', 'back_side_of_id_card', 'is_real_name_auth')


class DeveloperIDCardEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Developer
        fields = ('front_side_of_id_card', 'back_side_of_id_card')


class DeveloperPersonalInfoSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    gitlab_user = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    star_rating = serializers.SerializerMethodField()
    project_total = serializers.IntegerField(read_only=True)
    roles = RoleField(many=True, read_only=True)

    class Meta:
        model = Developer
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_gitlab_user(self, obj):
        gitlab_user_id = obj.gitlab_user_id
        if gitlab_user_id:
            return get_gitlab_user_simple_data(gitlab_user_id)

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url

    def get_star_rating(self, obj):
        return obj.star_rating

    #
    # def get_top_user(self, obj):
    #     top_user, created = TopUser.get_or_create(developer=obj)
    #     data = TopUserViewSerializer(top_user).data
    #     return data


class DeveloperListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(read_only=True)

    roles = RoleField(many=True, queryset=Role.objects.all())
    development_languages = TagField(many=True, read_only=True)
    frameworks = TagField(many=True, read_only=True)

    project_total = serializers.IntegerField(read_only=True)
    active_projects = ProjectSimpleSerializer(many=True, read_only=True)

    last_project = ProjectSimpleSerializer(many=False, read_only=True)
    position_candidates = serializers.SerializerMethodField()

    # 最近打款
    latest_payment = JobPaymentDateSerializer(many=False, read_only=True)
    recent_average_payment = serializers.IntegerField(read_only=True)

    # 来自于缓存  在api里重新赋值
    star_rating = serializers.SerializerMethodField()
    partners = serializers.SerializerMethodField()
    gitlab_user = serializers.SerializerMethodField()

    class Meta:
        model = Developer
        fields = '__all__'

    def get_position_candidates(self, obj):
        position_candidates = obj.position_candidates.all().order_by('-created_at')
        return JobPositionCandidateViewSerializer(position_candidates[:5], many=True).data

    # 来自于缓存  在api里重新赋值
    def get_star_rating(self, obj):
        return None

    def get_partners(self, obj):
        return None

    def get_gitlab_user(self, obj):
        return None


class DeveloperStatisticSerializer(serializers.ModelSerializer):
    role_names = serializers.SerializerMethodField()
    payment_total = serializers.IntegerField(read_only=True)
    project_total = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField()

    class Meta:
        model = Developer
        fields = ['name', 'location', 'status_display', 'role_names', 'created_at', 'payment_total', 'project_total']

    def get_role_names(self, obj):
        return ",".join(obj.roles.values_list("name", flat=True))


class DeveloperDetailSerializer(DeveloperListSerializer):
    pass


class DeveloperStatusSerializer(serializers.ModelSerializer):
    expected_work_at = serializers.DateField(allow_null=True, required=False)
    abandoned_reason = serializers.CharField(allow_null=True, required=False)
    refuse_new_job_reason = serializers.CharField(allow_null=True, required=False)

    class Meta:
        model = Developer
        fields = ['status', 'expected_work_at', 'abandoned_reason', 'refuse_new_job_reason']


class DeveloperExportSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    development_languages = serializers.SerializerMethodField()
    frameworks = serializers.SerializerMethodField()

    project_total = serializers.IntegerField(read_only=True)
    status_display = serializers.SerializerMethodField()

    average_star_rating = serializers.SerializerMethodField()

    class Meta:
        model = Developer
        fields = ['created_at', 'status_display', 'name', 'roles', 'development_languages', 'frameworks',
                  'abandoned_at', 'abandoned_reason', 'project_total', 'average_star_rating']

    def get_roles(self, obj):
        return ' '.join([role.name for role in obj.roles.all()])

    def get_development_languages(self, obj):
        return ' '.join([role.name for role in obj.development_languages.all()])

    def get_frameworks(self, obj):
        return ' '.join([role.name for role in obj.frameworks.all()])

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_average_star_rating(self, obj):
        return self.average_star_rating


class DeveloperWithGitlabUserSerializer(serializers.ModelSerializer):
    gitlab_user = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Developer
        fields = ['id', 'name', 'username', 'gitlab_user']

    def get_gitlab_user(self, obj):
        gitlab_user_id = obj.gitlab_user_id
        if gitlab_user_id:
            return get_gitlab_user_simple_data(gitlab_user_id)

    def get_username(self, obj):
        return obj.name


class DailyWorkSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField(read_only=True)
    statistics = serializers.SerializerMethodField(read_only=True)
    gantt_tasks = serializers.SerializerMethodField()
    other_task = serializers.SerializerMethodField()

    class Meta:
        model = DailyWork
        fields = '__all__'

    def get_statistics(self, obj):
        return get_project_developer_daily_works_statistics(obj.project, obj.developer)

    def get_gantt_tasks(self, obj):
        if obj.gantt_tasks:
            return json.loads(obj.gantt_tasks, encoding='utf-8')

    def get_other_task(self, obj):
        if obj.other_task:
            return json.loads(obj.other_task, encoding='utf-8')

    def get_status_display(self, obj):
        status_display = obj.get_status_display()
        return status_display


class DailyWorkNextDayPlanSerializer(serializers.ModelSerializer):
    gantt_tasks = serializers.SerializerMethodField()
    other_task = serializers.SerializerMethodField()

    class Meta:
        model = DailyWork
        fields = '__all__'

    def get_other_task(self, obj):
        if obj.other_task_plan:
            return json.loads(obj.other_task_plan, encoding='utf-8')

    def get_gantt_tasks(self, obj):
        if obj.gantt_tasks_plan:
            return json.loads(obj.gantt_tasks_plan, encoding='utf-8')


class DailyWorkViewSerializer(DailyWorkSerializer):
    project = ProjectField(read_only=True)
    developer = DeveloperField(read_only=True)
    next_day_work = DailyWorkNextDayPlanSerializer(many=False, read_only=True)
    view_users = serializers.SerializerMethodField(read_only=True)
    gitlab_commits = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DailyWork
        fields = '__all__'

    def get_view_users(self, obj):
        user_set = set()
        users_data = []
        if obj.browsing_histories.exists():
            for item in obj.browsing_histories.order_by('created_at'):
                user = item.visitor
                if user.id not in user_set:
                    user_data = get_user_data(user)
                    user_data['last_view_at'] = item.created_at.strftime(settings.DATETIME_FORMAT)
                    users_data.append(user_data)
                    user_set.add(user.id)
        return users_data

    def get_gitlab_commits(self, obj):
        if obj.gitlab_commits:
            data = json.loads(obj.gitlab_commits, encoding='utf-8')
            return data


class DailyWorkCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyWork
        fields = ['project', 'developer', 'leave_at', 'return_at', 'remarks', 'day']


class DailyWorkWorkTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyWork
        fields = ['leave_at', 'return_at']


class DailyWorkNextDayEditSerializer(serializers.ModelSerializer):
    gantt_tasks_plan = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    other_task_plan = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    other_task = serializers.CharField(allow_null=True, allow_blank=True, required=False)

    class Meta:
        model = DailyWork
        fields = ['leave_at', 'return_at', 'gantt_tasks_plan', 'other_task_plan', 'other_task']


class DailyWorkWithNextDaySimpleSerializer(serializers.ModelSerializer):
    next_day_work = DailyWorkWorkTimeSerializer(many=False, read_only=True)

    class Meta:
        model = DailyWork
        fields = '__all__'


class GanttTaskTopicDailyWorkSerializer(serializers.ModelSerializer):
    remarks = serializers.SerializerMethodField(read_only=True)
    result_remarks = serializers.SerializerMethodField(read_only=True)
    task_type = serializers.SerializerMethodField(read_only=True)
    task_status = serializers.SerializerMethodField(read_only=True)
    gantt_task_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GanttTaskTopic
        fields = ['id', 'gantt_task_id', 'catalogue_name', 'name', 'start_time', 'only_workday', 'expected_finish_time',
                  'timedelta_days', 'task_type', 'task_status', 'remarks', 'result_remarks']

    def get_task_status(self, obj):
        if obj.is_dev_done:
            return 'done'
        return 'pending'

    def get_gantt_task_id(self, obj):
        return obj.id

    def get_task_type(self, obj):
        return 'gantt'

    def get_remarks(self, obj):
        return None

    def get_result_remarks(self, obj):
        return None


class DocumentVersionSerializer(serializers.ModelSerializer):
    submitter = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = DocumentVersion
        fields = '__all__'


class DocumentVersionViewSerializer(serializers.ModelSerializer):
    submitter = UserField(many=False, queryset=User.objects.all())
    clean_html = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DocumentVersion
        fields = '__all__'

    def get_clean_html(self, obj):
        if obj.clean_html:
            return obj.clean_html
        if obj.html:
            from developers.tasks import build_document_version_clean_html
            build_document_version_clean_html.delay(obj.id)
            return obj.html


class DocumentVersionSimpleSerializer(serializers.ModelSerializer):
    submitter = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = DocumentVersion
        exclude = ['html', 'clean_html']


class DocumentDetailSerializer(serializers.ModelSerializer):
    roles = RoleField(many=True, queryset=Role.objects.all())
    importance_display = serializers.SerializerMethodField(read_only=True)

    online_version = DocumentVersionSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = Document
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_importance_display(self, obj):
        return obj.get_importance_display()


class DocumentListSerializer(serializers.ModelSerializer):
    roles = RoleField(many=True, queryset=Role.objects.all())
    importance_display = serializers.SerializerMethodField(read_only=True)

    online_version = DocumentVersionSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = Document
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_importance_display(self, obj):
        return obj.get_importance_display()


class DocumentListWithVersionsSerializer(serializers.ModelSerializer):
    roles = RoleField(many=True, queryset=Role.objects.all())
    importance_display = serializers.SerializerMethodField(read_only=True)

    online_version = DocumentVersionViewSerializer(many=False, read_only=True)
    history_versions = DocumentVersionViewSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_importance_display(self, obj):
        return obj.get_importance_display()


class DocumentEditSerializer(serializers.ModelSerializer):
    roles = RoleField(many=True, queryset=Role.objects.all())

    class Meta:
        model = Document
        fields = ['title', 'is_public', 'roles', 'importance']


class DocumentSyncLogSerializer(serializers.ModelSerializer):
    user = UserField(many=False, queryset=User.objects.all())
    developer = DeveloperField(many=False, queryset=Developer.objects.all())
    document = DocumentVersionField(many=False, queryset=DocumentVersion.objects.all())

    class Meta:
        model = DocumentSyncLog
        fields = '__all__'


class DocumentReadLogSerializer(serializers.ModelSerializer):
    user = UserField(many=False, read_only=True)
    developer = DeveloperField(many=False, read_only=True)
    document = DocumentVersionField(many=False, queryset=DocumentVersion.objects.all())

    class Meta:
        model = DocumentReadLog
        fields = '__all__'
