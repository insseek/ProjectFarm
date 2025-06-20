from rest_framework import serializers

from auth_top.models import TopUser


class TopUserField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        obj = TopUser.objects.filter(pk=value.pk).first()
        if obj:
            data = TopUserViewSerializer(obj).data
            return data


class TopUserSimpleViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopUser
        fields = ('id', 'username', 'avatar', 'avatar_color')


class TopUserViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopUser
        fields = (
            'id', 'user_type', 'user_id', 'developer_id', 'client_id', 'username', 'phone',
            'avatar', 'avatar_url', 'avatar_color',
            'is_active', 'is_superuser')
