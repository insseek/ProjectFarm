from django.contrib.auth.models import User
from rest_framework import serializers

from auth_top.serializers import TopUserField
from comments.serializers import CommentSerializer
from files.serializers import FileField
from workorder.models import CommonWorkOrder, WorkOrderOperationLog
from farmbase.serializers import UserField
from projects.models import Project
from proposals.models import Proposal


class ProjectField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        project = Project.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": project.name}

        return dict


class ProposalField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        proposal = Proposal.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": proposal.name}
        return dict


class CommonWorkOrderCreateSerializer(serializers.ModelSerializer):
    work_order_type = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['submitter', 'principal', 'priority', 'title', 'work_order_type', 'content_type', 'object_id',
                  'description', 'expiration_date', 'data_link']


class StyleWorkOrderCreateSerializer(serializers.ModelSerializer):
    work_order_type = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['submitter', 'principal', 'priority', 'title', 'work_order_type', 'content_type', 'object_id',
                  'page_number', 'style_type',
                  'description', 'expiration_date']


class GlobalWorkOrderCreateSerializer(serializers.ModelSerializer):
    work_order_type = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['submitter', 'principal', 'priority', 'title', 'work_order_type', 'content_type', 'object_id',
                  'page_number_range', 'description', 'expiration_date']


class ChangesWorkOrderCreateSerializer(serializers.ModelSerializer):
    work_order_type = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['submitter', 'principal', 'priority', 'title', 'work_order_type', 'content_type', 'object_id',
                  'modify_page_number', 'add_page_number', 'description', 'expiration_date']


class BugWorkOrderCreateSerializer(serializers.ModelSerializer):
    work_order_type = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['submitter', 'principal', 'priority', 'content_type', 'object_id', 'title',
                  'work_order_type', 'bug_link', 'description', 'expiration_date']


class CommonWorkOrderListSerializer(serializers.ModelSerializer):
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    principal = UserField(many=False, queryset=User.objects.all())
    content = serializers.SerializerMethodField(read_only=True)
    content_object = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    work_order_type_display = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True)
    done_by = UserField(many=False, queryset=User.objects.all())
    closed_by = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = CommonWorkOrder
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_priority_display(self, obj):
        return obj.get_priority_display()

    def get_work_order_type_display(self, obj):
        return obj.get_work_order_type_display()

    def get_content(self, obj):
        if obj.content_object:
            return {'name': obj.content_object.name, 'model': obj.content_type.model, 'id': obj.content_object.id,
                    'model_name': obj.content_object._meta.verbose_name}

    def get_content_object(self, obj):
        if obj.content_object:
            return {
                "content_type": {
                    "app_label": obj.content_type.app_label,
                    "model": obj.content_type.model,
                    "model_verbose_name": obj.content_object._meta.verbose_name
                },
                "object_name": obj.content_object.name,
                "object_id": obj.content_object.id,
            }


class CommonWorkOrderDetailSerializer(serializers.ModelSerializer):
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    principal = UserField(many=False, queryset=User.objects.all())
    content = serializers.SerializerMethodField(read_only=True)
    content_object = serializers.SerializerMethodField(read_only=True)
    status_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    work_order_type_display = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True)
    files = FileField(many=True, read_only=True)
    done_by = UserField(many=False, queryset=User.objects.all())
    closed_by = UserField(many=False, queryset=User.objects.all())

    class Meta:
        model = CommonWorkOrder
        fields = '__all__'

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_priority_display(self, obj):
        return obj.get_priority_display()

    def get_work_order_type_display(self, obj):
        return obj.get_work_order_type_display()

    def get_content(self, obj):
        if obj.content_object:
            return {'name': obj.content_object.name, 'model': obj.content_type.model, 'id': obj.content_object.id,
                    'model_name': obj.content_object._meta.verbose_name}

    def get_content_object(self, obj):
        if obj.content_object:
            return {
                "content_type": {
                    "app_label": obj.content_type.app_label,
                    "model": obj.content_type.model,
                    "model_verbose_name": obj.content_object._meta.verbose_name
                },
                "object_name": obj.content_object.name,
                "object_id": obj.content_object.id,
            }


class WorkOrderOperationLogSerializer(serializers.ModelSerializer):
    operator = UserField(many=False, read_only=True)
    log_type_display = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    origin_assignee = UserField(many=False, read_only=True)
    new_assignee = UserField(many=False, read_only=True)

    class Meta:
        model = WorkOrderOperationLog
        fields = '__all__'

    def get_log_type_display(self, obj):
        return obj.get_log_type_display()

    def get_comments(self, obj):
        comments = obj.comments.filter(parent_id=None).order_by('created_at')
        return CommentSerializer(comments, many=True).data


class CommonWorkOrderDateSerializer(serializers.ModelSerializer):
    start_at = serializers.DateTimeField()
    expected_at = serializers.DateField()
    status = serializers.IntegerField()

    class Meta:
        model = CommonWorkOrder
        fields = ['start_at', 'expected_at', 'status']


class CommonWorkOrderDoneSerializer(serializers.ModelSerializer):
    done_at = serializers.DateTimeField()
    status = serializers.IntegerField()
    done_by = UserField(many=False, queryset=User.objects.all())
    principal = UserField(many=False, queryset=User.objects.all(), required=False)

    class Meta:
        model = CommonWorkOrder
        fields = ['done_at', 'done_by', 'status', 'principal']


class ChangesWorkOrderDoneSerializer(CommonWorkOrderDoneSerializer):
    modify_page_number = serializers.IntegerField(required=True)
    add_page_number = serializers.IntegerField(required=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['done_at', 'done_by', 'status', 'principal', 'modify_page_number', 'add_page_number']


class StyleWorkOrderDoneSerializer(CommonWorkOrderDoneSerializer):
    style_type = serializers.IntegerField(required=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['done_at', 'done_by', 'status', 'principal', 'page_number', 'style_type']


class GlobalWorkOrderDoneSerializer(CommonWorkOrderDoneSerializer):
    practical_page_number = serializers.IntegerField(required=True)

    class Meta:
        model = CommonWorkOrder
        fields = ['done_at', 'done_by', 'status', 'principal', 'practical_page_number']
