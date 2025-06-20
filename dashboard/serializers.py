import json

from rest_framework import serializers

from projects.serializers import ProjectStageSimpleSerializer, GanttChartField, DeveloperDashboardCardField, RoleField
from projects.utils.common_utils import get_project_members_data
from projects.models import Project, JobPosition, ProjectLinks


class ProjectLinkDashBoardSerializer(serializers.ModelSerializer):
    gitlab_project = serializers.SerializerMethodField()
    quip_folder = serializers.CharField(read_only=True)
    quip_folder_data = serializers.SerializerMethodField()
    quip_engineer_folder = serializers.CharField(read_only=True)
    quip_engineer_folder_data = serializers.SerializerMethodField()
    ui_links = serializers.SerializerMethodField()

    class Meta:
        model = ProjectLinks
        fields = '__all__'

    # 接口中统一构造
    def get_gitlab_project(self, obj):
        return None

    def get_quip_folder_data(self, obj):
        return obj.quip_folder_data()

    def get_quip_engineer_folder_data(self, obj):
        return obj.quip_engineer_folder_data()

    def get_ui_links(self, obj):
        if obj.ui_links:
            return json.loads(obj.ui_links, encoding='utf-8')
        return []


# DashBoard页面
class ProjectDashBoardSerializer(serializers.ModelSerializer):
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)
    gantt_chart = GanttChartField(many=False, read_only=True)
    members = serializers.SerializerMethodField()

    deployment_servers = serializers.SerializerMethodField()
    prototype_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    job_positions = serializers.SerializerMethodField()

    undone_bugs_count = serializers.SerializerMethodField()
    unread_daily_works_count = serializers.SerializerMethodField()
    links = ProjectLinkDashBoardSerializer(many=False, read_only=True)
    gitlab_project = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "name", "current_stages", "gantt_chart", "members", "deployment_servers", "prototype_count",
                  "comment_count", "job_positions", "undone_bugs_count", "unread_daily_works_count", "gitlab_project", "links"]

    # 接口中统一构造
    def get_gitlab_project(self, obj):
        return None

    def get_members(self, obj):
        return get_project_members_data(obj)

    def get_deployment_servers(self, obj):
        if obj.deployment_servers:
            return json.loads(obj.deployment_servers, encoding='utf-8')
        return []

    def get_prototype_count(self, obj):
        return obj.prototypes.filter(is_deleted=False).count()

    def get_comment_count(self, obj):
        return obj.comments.count()

    # 接口中从缓存中构造数据
    def get_job_positions(self, obj):
        positions = obj.job_positions.all()
        developer_ids = set()
        clean_positions = []
        for position in positions:
            if position.developer_id not in developer_ids:
                clean_positions.append(position)
                developer_ids.add(position.developer_id)
        return JobPositionWithGitDataSerializer(clean_positions, many=True).data

    def get_undone_bugs_count(self, obj):
        return 0

    def get_unread_daily_works_count(self, obj):
        return 0


class JobPositionWithGitDataSerializer(serializers.ModelSerializer):
    role = RoleField(many=False, read_only=True)
    developer = DeveloperDashboardCardField(many=False, read_only=True)
    gitlab_commits = serializers.SerializerMethodField()
    pending_bugs_count = serializers.SerializerMethodField()

    class Meta:
        model = JobPosition
        fields = '__all__'

    # 接口里处理
    def get_gitlab_commits(self, obj):
        # if obj.developer.gitlab_user_id:
        return None

    def get_pending_bugs_count(self, obj):
        top_user = obj.developer.get_top_user()
        return obj.project.bugs.filter(assignee_id=top_user.id, status='pending').count()
