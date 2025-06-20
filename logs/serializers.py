import json

from django.contrib.auth.models import User
from rest_framework import serializers

from developers.models import Developer
from logs.models import Log, BrowsingHistory
from auth_top.serializers import TopUserField, TopUserViewSerializer


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
        dict = {"id": value.pk, "username": user.username, "avatar_url": avatar_url, 'avatar_color': avatar_color, 'is_active': user.is_active}
        return dict


class UserBasicSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'avatar_url', 'avatar_color', 'avatar', 'is_active')

    def get_avatar_url(self, obj):
        if obj.profile.avatar:
            return obj.profile.avatar.url

    def get_avatar(self, obj):
        if obj.profile.avatar:
            return obj.profile.avatar.url

    def get_avatar_color(self, obj):
        return obj.profile.avatar_color


class DeveloperBasicSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Developer
        fields = ('id', 'name', 'username', 'email', 'avatar_url', 'avatar', 'phone')

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url

    def get_username(self, obj):
        return "工程师-{}".format(obj.name)


class LogSerializer(serializers.ModelSerializer):
    operator = serializers.SerializerMethodField(read_only=True)
    operator_developer = serializers.SerializerMethodField(read_only=True)
    content_data = serializers.SerializerMethodField(read_only=True)
    creator = TopUserField(many=False, read_only=True)

    class Meta:
        model = Log
        exclude = ['content_type', 'object_id']

    def get_content_data(self, obj):
        if obj.content_data:
            return json.loads(obj.content_data, encoding='utf-8')

    def get_operator_developer(self, obj):
        if obj.operator_developer:
            return DeveloperBasicSerializer(obj.operator_developer, many=False).data

    def get_operator(self, obj):
        if obj.operator:
            return UserBasicSerializer(obj.operator, many=False).data
        elif obj.operator_developer:
            return DeveloperBasicSerializer(obj.operator_developer, many=False).data


class BrowsingHistorySerializer(serializers.ModelSerializer):
    visitor = serializers.SerializerMethodField(read_only=True)
    browsing_time = serializers.CharField(read_only=True)
    address = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BrowsingHistory
        fields = '__all__'

    def get_address(self, obj):
        return obj.address

    def get_visitor(self, obj):
        if obj.visitor:
            return UserBasicSerializer(obj.visitor).data
        elif obj.user:
            return TopUserViewSerializer(obj.user).data
