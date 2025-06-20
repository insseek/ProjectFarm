from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from farmbase.serializers import UserField
from farmbase.utils import get_user_data
from tasks.models import Task
from reports.serializers import TagField


class TaskEditSerializer(serializers.ModelSerializer):
    principal = UserField(many=False, queryset=User.objects.all())
    update_comment = serializers.CharField(required=True)

    class Meta:
        model = Task
        fields = ['principal', 'update_comment', 'expected_at', 'name']


class TaskSerializer(serializers.ModelSerializer):
    principal = UserField(many=False, queryset=User.objects.all())
    creator = UserField(many=False, queryset=User.objects.all())
    is_today = serializers.BooleanField(required=False, read_only=True)
    is_past = serializers.BooleanField(required=False, read_only=True)
    update_comment = serializers.CharField(required=False, write_only=True)
    content = serializers.SerializerMethodField(read_only=True)
    content_object = serializers.SerializerMethodField(read_only=True)
    source_object = serializers.SerializerMethodField(read_only=True)
    is_done = serializers.BooleanField(required=False, read_only=True)
    done_at = serializers.DateTimeField(required=False, read_only=True)
    task_type_display = serializers.CharField(read_only=True)
    auto_close_required = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = '__all__'

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

    def get_source_object(self, obj):
        if obj.source_object:
            return {
                "content_type": {
                    "app_label": obj.source_type.app_label,
                    "model": obj.source_type.model,
                    "model_verbose_name": obj.source_object._meta.verbose_name
                },
                "object_name": str(obj.source_object),
                "object_id": obj.source_object.id,
            }

    def get_content(self, obj):
        if obj.content_object:
            return {'name': obj.content_object.name, 'model': obj.content_type.model, 'id': obj.content_object.id,
                    'model_name': obj.content_object._meta.verbose_name}


class TaskField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        task = Task.objects.get(pk=value.pk)
        return TaskSerializer(task).data
