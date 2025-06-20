import json
from copy import deepcopy

from rest_framework import serializers

from auth_top.models import TopUser
from auth_top.serializers import TopUserField
from auth_top.utils import get_top_user_data
from projects.models import Project
from projects.serializers import ProjectStageSimpleSerializer
from testing.utils import get_project_members_top_user_data, get_project_developers_top_user_data, \
    get_project_members_top_user_dict

from testing.models import TestCaseLibrary, TestCaseModule, TestCase, ProjectPlatform, ProjectTestCaseModule, \
    ProjectTestCase, TestCaseReviewLog, ProjectTestCaseReviewLog, ProjectTestCaseExecuteLog, ProjectTag, \
    ProjectTestPlan, TestPlanModule, TestPlanCase, Bug, BugOperationLog, TestDayBugStatistic

from comments.serializers import CommentSerializer
from logs.serializers import LogSerializer


class ProjectField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = Project.objects.get(pk=value.pk)
        obj_data = {"id": value.pk, "name": obj.name, "status": obj.status, "status_display": obj.status_display}
        return obj_data


class ProjectTestCaseField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = ProjectTestCase.objects.get(pk=value.pk)
        obj_data = {"id": value.pk, "description": obj.description}
        return obj_data


# 用例库开始
class TestCaseLibrarySerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    latest_log = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseLibrary
        fields = '__all__'
        extra_kwargs = {
            'id': {"read_only": True},
            'created_at': {"read_only": True},
            'updated_at': {"read_only": True},
        }

    def get_latest_log(self, obj):
        latest_log = obj.logs.order_by('-created_at').first()
        if latest_log:
            return LogSerializer(latest_log).data


class TestCaseLibraryField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = TestCaseLibrary.objects.filter(pk=value.pk).first()
        if obj:
            data = TestCaseLibraryUpdateSerializer(obj).data
            return data


# read_only 是只读，不能写
# write_only是只写不能读
class TestCaseLibraryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseLibrary
        fields = ['id', 'name', 'description']
        extra_kwargs = {
            'id': {"read_only": True},
        }


class TestCaseModuleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = TestCaseModule.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id, 'name': obj.name, 'full_name': obj.full_name, 'full_index': obj.full_index}


class TestCaseModuleSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    library = TestCaseLibraryField(many=False, queryset=TestCaseLibrary.objects.all())
    parent = TestCaseModuleField(many=False, queryset=TestCaseModule.objects.all(), required=False, allow_null=True)

    class Meta:
        model = TestCaseModule
        fields = '__all__'


class TestCaseModuleWithChildrenSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    library = TestCaseLibraryField(many=False, queryset=TestCaseLibrary.objects.all())
    parent = TestCaseModuleField(many=False, queryset=TestCaseModule.objects.all())
    children = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseModule
        fields = '__all__'

    def get_children(self, obj):
        return TestCaseModuleWithChildrenSerializer(obj.children.order_by('index'), many=True).data


class TestCaseModuleWithChildrenWithCaseSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    library = TestCaseLibraryField(many=False, queryset=TestCaseLibrary.objects.all())
    parent = TestCaseModuleField(many=False, queryset=TestCaseModule.objects.all())
    children = serializers.SerializerMethodField()
    test_cases = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseModule
        fields = '__all__'

    def get_children(self, obj):
        return TestCaseModuleWithChildrenWithCaseSerializer(obj.children.order_by('index'), many=True).data

    def get_test_cases(self, obj):
        return TestCaseSimpleSerializer(obj.test_cases.filter(is_active=True).order_by('created_at'), many=True).data


class TestCaseModuleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseLibrary
        fields = ['id', 'name']
        extra_kwargs = {
            'id': {"read_only": True}
        }


class TestCaseSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    module = TestCaseModuleField(many=False, queryset=TestCaseModule.objects.all())
    status_display = serializers.SerializerMethodField()
    precondition = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = TestCase
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    module_full_name = serializers.SerializerMethodField()

    def get_module_full_name(self, obj):
        return obj.module.full_name


class TestCaseUpdateSerializer(serializers.ModelSerializer):
    precondition = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    module = TestCaseModuleField(many=False, queryset=TestCaseModule.objects.all())

    class Meta:
        model = TestCase
        fields = ['id', 'description', 'precondition', 'expected_result', 'module']
        extra_kwargs = {
            'id': {"read_only": True}
        }


class TestCaseSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'description', 'status', 'status_display']


class TestCaseStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    status = serializers.CharField(required=True)

    class Meta:
        model = TestCase
        fields = ['id', 'status', 'status_display']
        extra_kwargs = {
            'id': {"read_only": True},
        }

    def get_status_display(self, obj):
        return obj.get_status_display()


# 用例库结束
class ProjectListSerializer(serializers.ModelSerializer):
    test_case_statistics = serializers.SerializerMethodField()
    bug_statistics = serializers.SerializerMethodField()
    test_plan_count = serializers.SerializerMethodField()
    members_dict = serializers.SerializerMethodField()
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'current_stages', 'test_case_statistics', 'test_plan_count',
                  'bug_statistics', 'created_at', 'done_at', 'members_dict')

    def get_members_dict(self, obj):
        return get_project_members_top_user_dict(obj)

    def get_test_case_statistics(self, obj):
        test_cases = obj.test_cases.filter(is_active=True)
        approved_cases = test_cases.filter(status='approved')
        executed_cases = test_cases.filter(plan_cases__status__in=['pass', 'failed']).distinct()
        return {"all": test_cases.count(), 'approved': approved_cases.count(), 'executed': executed_cases.count()}

    def get_test_plan_count(self, obj):
        return obj.test_plans.count()

    def get_bug_statistics(self, obj):
        bugs = obj.bugs.all()
        pending_bugs = bugs.filter(status='pending')
        return {"all": bugs.count(), 'pending': pending_bugs.count()}


class ProjectDetailSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    current_stages = ProjectStageSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'name', 'current_stages', 'members')

    def get_members(self, obj):
        result = []
        members = get_project_members_top_user_data(obj)
        developers = get_project_developers_top_user_data(obj)
        result.extend(members)
        result.extend(developers)
        return result


# 项目平台开始
class ProjectPlatformSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    project = ProjectField(many=False, queryset=Project.objects.all())
    is_default = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectPlatform
        fields = '__all__'
        extra_kwargs = {
            'id': {"read_only": True},
            'created_at': {"read_only": True},
            'updated_at': {"read_only": True},
        }


class ProjectPlatformUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlatform
        fields = ['id', 'name', 'created_at']
        extra_kwargs = {
            'id': {"read_only": True},
            'created_at': {"read_only": True}
        }


class ProjectPlatformField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = ProjectPlatform.objects.filter(pk=value.pk).first()
        if obj:
            return {"id": obj.id, 'name': obj.name}


# 项目平台结束


# 项目标签开始
class ProjectTagSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    project = ProjectField(many=False, queryset=Project.objects.all())
    is_default = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectTag
        fields = '__all__'
        extra_kwargs = {
            'id': {"read_only": True},
            'created_at': {"read_only": True},
            'updated_at': {"read_only": True},
        }


class ProjectTagListSerializer(serializers.ModelSerializer):
    is_default = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectTag
        fields = ['id', 'is_default', 'name', 'index']
        extra_kwargs = {
            'id': {"read_only": True},
            'index': {"read_only": True}
        }


class ProjectTagUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTag
        fields = ['id', 'name']
        extra_kwargs = {
            'id': {"read_only": True}
        }


class ProjectTagField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = ProjectTag.objects.filter(pk=value.pk).first()
        if obj:
            data = ProjectTagUpdateSerializer(obj).data
            return data


# 项目标签结束


# 项目用例模块开始
class ProjectTestCaseModuleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = ProjectTestCaseModule.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id, 'name': obj.name, 'full_name': obj.full_name, 'full_index': obj.full_index}


class ProjectTestCaseModuleSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    project = ProjectField(many=False, queryset=Project.objects.all())
    platforms = ProjectPlatformField(many=True, queryset=ProjectPlatform.objects.all(), required=True, allow_null=False,
                                     allow_empty=False)
    parent = ProjectTestCaseModuleField(many=False, queryset=ProjectTestCaseModule.objects.all(), required=False,
                                        allow_null=True)

    class Meta:
        model = ProjectTestCaseModule
        fields = '__all__'


class ProjectTestCaseModuleWithChildrenSerializer(serializers.ModelSerializer):
    # creator = TopUserField(many=False, queryset=TopUser.objects.all())
    # project = ProjectField(many=False, queryset=Project.objects.all())
    # parent = ProjectTestCaseModuleField(many=False, queryset=ProjectTestCaseModule.objects.all())
    platforms = ProjectPlatformField(many=True, queryset=ProjectPlatform.objects.all())
    children = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTestCaseModule
        fields = ('id', 'name', 'platforms', 'children')

    def get_children(self, obj):
        return ProjectTestCaseModuleWithChildrenSerializer(obj.children.order_by('index'), many=True).data


class ProjectTestCaseModuleWithChildrenWithCaseSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    project = ProjectField(many=False, queryset=Project.objects.all())
    parent = ProjectTestCaseModuleField(many=False, queryset=ProjectTestCaseModule.objects.all())
    platforms = ProjectPlatformField(many=True, queryset=ProjectPlatform.objects.all())
    children = serializers.SerializerMethodField()

    test_cases = serializers.SerializerMethodField()
    approved_test_cases = serializers.SerializerMethodField()
    approved_test_cases_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTestCaseModule
        fields = '__all__'

    def get_children(self, obj):
        return ProjectTestCaseModuleWithChildrenWithCaseSerializer(obj.children.order_by('index'), many=True).data

    def get_test_cases(self, obj):
        cases = obj.test_cases.filter(is_active=True).order_by('created_at')
        return ProjectTestCaseSimpleSerializer(cases, many=True).data

    def get_approved_test_cases(self, obj):
        cases = obj.test_cases.filter(is_active=True, status='approved').order_by('created_at')
        return ProjectTestCaseSimpleSerializer(cases, many=True).data

    def get_approved_test_cases_count(self, obj):
        return len(obj.test_cases.filter(is_active=True, status='approved'))


class ProjectTestCaseModuleUpdateSerializer(serializers.ModelSerializer):
    platforms = ProjectPlatformField(many=True, queryset=ProjectPlatform.objects.all(), required=True, allow_null=False,
                                     allow_empty=False)

    class Meta:
        model = TestCaseLibrary
        fields = ['id', 'name', 'platforms']
        extra_kwargs = {
            'id': {"read_only": True}
        }


# 项目用例模块结束


# 项目用例开始
class ProjectTestCaseSimpleSerializer(serializers.ModelSerializer):
    platforms = ProjectPlatformField(many=True, read_only=True)

    class Meta:
        model = ProjectTestCase
        fields = ['id', 'description', 'status', 'status_display', 'platforms']


class TestCaseReviewLogSerializer(serializers.ModelSerializer):
    log_type_display = serializers.SerializerMethodField()
    operator = TopUserField(many=False, queryset=TopUser.objects.all())
    content_data = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseReviewLog
        fields = '__all__'

    def get_log_type_display(self, obj):
        return obj.get_log_type_display()

    def get_content_data(self, obj):
        return json.loads(obj.content_data) if obj.content_data else None


class ProjectTestCaseReviewLogSerializer(serializers.ModelSerializer):
    log_type_display = serializers.SerializerMethodField()
    operator = TopUserField(many=False, queryset=TopUser.objects.all())
    content_data = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTestCaseReviewLog
        fields = '__all__'

    def get_log_type_display(self, obj):
        return obj.get_log_type_display()

    def get_content_data(self, obj):
        return json.loads(obj.content_data) if obj.content_data else None


class ProjectTestCaseSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    # project = ProjectField(many=False, queryset=Project.objects.all())

    module_full_name = serializers.SerializerMethodField()
    module = ProjectTestCaseModuleField(many=False, queryset=ProjectTestCaseModule.objects.all())
    platforms = ProjectPlatformField(many=True, queryset=ProjectPlatform.objects.all())
    tags = ProjectTagField(many=True, queryset=ProjectTag.objects.all(), required=False)

    tags_str = serializers.SerializerMethodField()
    precondition = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    status_display = serializers.SerializerMethodField()
    execution_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectTestCase
        fields = '__all__'

    def get_tags_str(self, obj):
        return ','.join([i.name for i in obj.tags.order_by('index')])

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_execution_count(self, obj):
        return obj.execution_count

    def get_module_full_name(self, obj):
        return obj.module.full_name


class ProjectTestCaseUpdateSerializer(serializers.ModelSerializer):
    module = ProjectTestCaseModuleField(many=False, queryset=ProjectTestCaseModule.objects.all())
    platforms = ProjectPlatformField(many=True, queryset=ProjectPlatform.objects.all())
    tags = ProjectTagField(many=True, queryset=ProjectTag.objects.all())
    precondition = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = ProjectTestCase
        fields = ['id', 'description', 'precondition', 'expected_result', 'module', 'platforms', 'tags', 'case_type',
                  'flow_type']
        extra_kwargs = {
            'id': {"read_only": True}
        }


class ProjectTestCaseStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    status = serializers.CharField(required=True)

    class Meta:
        model = ProjectTestCase
        fields = ['id', 'status', 'status_display']
        extra_kwargs = {
            'id': {"read_only": True},
        }

    def get_status_display(self, obj):
        return obj.get_status_display()


# 项目用例结束


# 项目测试计划
class ProjectTestPlanListSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    platform = ProjectPlatformField(many=False, queryset=ProjectPlatform.objects.all())
    creator = TopUserField(many=False, queryset=TopUser.objects.all())

    status_display = serializers.SerializerMethodField()
    case_statistics = serializers.SerializerMethodField()

    plan_modules = serializers.SerializerMethodField()
    executors = TopUserField(many=True, queryset=TopUser.objects.all(), required=False)
    case_tags = ProjectTagField(many=True, queryset=ProjectTag.objects.all(), required=False)

    class Meta:
        model = ProjectTestPlan
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_case_statistics(self, obj):
        plan_cases = obj.plan_cases.all()
        pass_cases = plan_cases.filter(status='pass')
        failed_cases = plan_cases.filter(status='failed')
        bugs_count = 0
        for case in failed_cases:
            if case.bugs.exists():
                bugs_count += case.bugs.count()
        executed_count = pass_cases.count() + failed_cases.count()
        return {"all": plan_cases.count(), 'pass': pass_cases.count(), 'failed': failed_cases.count(),
                'executed': executed_count, 'bugs': bugs_count}

    def get_plan_modules(self, obj):
        plan_modules = obj.plan_modules.order_by('created_at')
        data = []
        for item in plan_modules:
            if item.plan_cases.exists():
                data.append({'id': item.id, 'name': item.name})
        return data


class ProjectTestPlanVerifyFieldSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    platform = ProjectPlatformField(many=False, queryset=ProjectPlatform.objects.all())
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    executors = TopUserField(many=True, queryset=TopUser.objects.all(), required=False)
    case_tags = ProjectTagField(many=True, queryset=ProjectTag.objects.all(), required=False)

    modules = ProjectTestCaseModuleField(many=True, queryset=ProjectTestCaseModule.objects.all())

    class Meta:
        model = ProjectTestPlan
        fields = '__all__'


class ProjectTestPlanSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    platform = ProjectPlatformField(many=False, queryset=ProjectPlatform.objects.all())
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    executors = TopUserField(many=True, queryset=TopUser.objects.all(), required=False)
    case_tags = ProjectTagField(many=True, queryset=ProjectTag.objects.all(), required=False)

    class Meta:
        model = ProjectTestPlan
        fields = '__all__'


class ProjectTestPlanField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = ProjectTestPlan.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id, 'name': obj.name}


class TestPlanModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestPlanModule
        fields = ['id', 'name']


class TestPlanModuleWithChildrenSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = TestPlanModule
        fields = ['id', 'name', 'children']

    def get_children(self, obj):
        return TestPlanModuleWithChildrenSerializer(obj.children.order_by('index'), many=True).data


class TestPlanCaseSimpleSerializer(serializers.ModelSerializer):
    case = serializers.SerializerMethodField()

    class Meta:
        model = TestPlanCase
        fields = ['case', 'description', 'precondition', 'expected_result']

    def get_case(self, obj):
        if obj.case and obj.case.is_active:
            return {"id": obj.case.pk, "description": obj.case.description}


class TestPlanModuleField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = TestPlanModule.objects.filter(pk=value.pk).first()
        if obj:
            return {'id': obj.id, 'name': obj.name, 'full_name': obj.full_name, 'full_index': obj.full_index}


# 项目计划用例开始
class BugSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bug
        fields = ['id', 'title', 'index', 'status', 'status_display', 'plan_case']


class TestPlanCaseSerializer(serializers.ModelSerializer):
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    tags = ProjectTagField(many=True, read_only=True)
    status_display = serializers.CharField()

    bugs = BugSimpleSerializer(many=True, read_only=True)

    module = TestPlanModuleField(many=False, read_only=True)
    platform = serializers.SerializerMethodField()

    class Meta:
        model = TestPlanCase
        fields = '__all__'

    def get_platform(self, obj):
        if obj.platform:
            return {'id': obj.platform.id, 'name': obj.platform.name}


class TestPlanCaseStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    status = serializers.CharField(required=True)

    class Meta:
        model = TestPlanCase
        fields = ['id', 'status', 'status_display']
        extra_kwargs = {
            'id': {"read_only": True},
        }

    def get_status_display(self, obj):
        return obj.get_status_display()


class TestPlanCaseField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = TestPlanCase.objects.filter(pk=value.pk).first()
        if obj:
            data = TestPlanCaseSimpleSerializer(obj).data
            return data


# 项目测试计划结束

# 项目Bug开始

class BugSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    creator = TopUserField(many=False, queryset=TopUser.objects.all())
    assignee = TopUserField(many=False, queryset=TopUser.objects.all())

    closed_by = TopUserField(many=False, queryset=TopUser.objects.all(), required=False, allow_null=True)
    fixed_by = TopUserField(many=False, queryset=TopUser.objects.all(), required=False, allow_null=True)

    module = ProjectTestCaseModuleField(many=False, queryset=ProjectTestCaseModule.objects.all())
    platform = ProjectPlatformField(many=False, queryset=ProjectPlatform.objects.all())
    tags = ProjectTagField(many=True, queryset=ProjectTag.objects.all(), required=False)

    plan_case = TestPlanCaseField(many=False, queryset=TestPlanCase.objects.all(), required=False)

    priority_display = serializers.CharField(read_only=True)
    bug_type_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)

    comments = CommentSerializer(many=True, read_only=True)

    comments_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Bug
        fields = '__all__'
        extra_kwargs = {
            'id': {"read_only": True},
            'status': {"read_only": True},
        }


class BugUpdateSerializer(serializers.ModelSerializer):
    assignee = TopUserField(many=False, queryset=TopUser.objects.all())

    module = ProjectTestCaseModuleField(many=False, queryset=ProjectTestCaseModule.objects.all())
    platform = ProjectPlatformField(many=False, queryset=ProjectPlatform.objects.all())
    tags = ProjectTagField(many=True, queryset=ProjectTag.objects.all(), required=False)

    class Meta:
        model = Bug
        fields = ['id', 'module', 'platform', 'tags', 'assignee', 'title', 'description', 'priority', 'bug_type',
                  'description_text']
        extra_kwargs = {
            'id': {"read_only": True}
        }


class BugStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bug
        fields = ['id', 'title', 'status', 'status_display']
        extra_kwargs = {
            'id': {"read_only": True},
        }


class BugAssigneeSerializer(serializers.ModelSerializer):
    assignee = TopUserField(many=False, queryset=TopUser.objects.all())

    class Meta:
        model = Bug
        fields = ['id', 'assignee', 'status', 'status_display']
        extra_kwargs = {
            'id': {"read_only": True},
            'status': {"read_only": True},
        }


# 项目Bug结束


class BugOperationLogSerializer(serializers.ModelSerializer):
    operator = TopUserField(many=False, read_only=True)
    log_type_display = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    origin_assignee = TopUserField(many=False, read_only=True)
    new_assignee = TopUserField(many=False, read_only=True)

    class Meta:
        model = BugOperationLog
        fields = '__all__'

    def get_log_type_display(self, obj):
        return obj.get_log_type_display()

    def get_comments(self, obj):
        comments = obj.comments.filter(parent_id=None).order_by('created_at')
        return CommentSerializer(comments, many=True).data


class BugExportSerializer(serializers.ModelSerializer):
    project_name = serializers.SerializerMethodField()
    title = serializers.CharField()
    module_full_name = serializers.CharField()
    bug_type_display = serializers.CharField(read_only=True)

    platform_name = serializers.SerializerMethodField()
    priority_display = serializers.CharField(read_only=True)

    creator_username = serializers.SerializerMethodField()
    assignee_username = serializers.SerializerMethodField()
    fixed_by_username = serializers.SerializerMethodField()

    status_display = serializers.CharField(read_only=True)

    class Meta:
        model = Bug
        fields = '__all__'

    def get_project_name(self, obj):
        return obj.project.name

    def get_platform_name(self, obj):
        return obj.platform.name

    def get_creator_username(self, obj):
        user = obj.creator
        if user:
            return user.username
        return ''

    def get_assignee_username(self, obj):
        user = obj.assignee
        if user:
            return user.username
        return ''

    def get_fixed_by_username(self, obj):
        user = obj.fixed_by
        if user:
            return user.username
        return ''


class ProjectTestCaseExecuteLogSerializer(serializers.ModelSerializer):
    executed_type_display = serializers.SerializerMethodField()
    executed_status_display = serializers.SerializerMethodField()
    operator = TopUserField(many=False, queryset=TopUser.objects.all())
    plan = ProjectTestPlanField(many=False, queryset=ProjectTestPlan.objects.all())
    bug = BugSimpleSerializer(many=False, read_only=True)

    class Meta:
        model = ProjectTestCaseExecuteLog
        fields = '__all__'

    def get_executed_type_display(self, obj):
        return obj.get_executed_type_display()

    def get_executed_status_display(self, obj):
        return obj.get_executed_status_display()


class TestDayBugStatisticSerializer(serializers.ModelSerializer):
    project = ProjectField(many=False, queryset=Project.objects.all())
    bugs_detail = serializers.SerializerMethodField()

    class Meta:
        model = TestDayBugStatistic
        fields = '__all__'

    def get_bugs_detail(self, obj):
        return json.loads(obj.bugs_detail) if obj.bugs_detail else {}
