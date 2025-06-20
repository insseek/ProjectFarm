from django.contrib.auth.models import User, Group
from rest_framework import serializers

from comments.models import Comment
from farmbase.serializers import UserField
from developers.models import Developer

from auth_top.models import TopUser
from auth_top.serializers import TopUserField
from files.serializers import FileField


class DeveloperField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        developer = Developer.objects.get(pk=value.pk)
        avatar = None
        if developer.avatar:
            avatar = developer.avatar.url

        dict = {"id": value.pk, "name": developer.name, 'username': developer.name,
                'avatar': avatar, 'avatar_url': avatar}
        return dict


class CommentSerializer(serializers.ModelSerializer):
    author = UserField(many=False, queryset=User.objects.all(), required=False, allow_null=True)
    developer = DeveloperField(many=False, queryset=Developer.objects.all(), required=False, allow_null=True)
    creator = TopUserField(many=False, queryset=TopUser.objects.all(), required=False, allow_null=True)
    clean_content = serializers.CharField(read_only=True)
    child_comments = serializers.SerializerMethodField(read_only=True)
    files = FileField(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = '__all__'

    def get_child_comments(self, obj):
        return CommentSerializer(obj.child_comments.order_by('-is_sticky', 'created_at'), many=True).data
