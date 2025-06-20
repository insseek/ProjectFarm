from farmbase.serializers import UserField
from rest_framework import serializers

from .models import File, PublicFile


class FileField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        file = File.objects.get(pk=value.pk)
        dict = {"id": value.pk, "url": file.file.url, "filename": file.filename, 'suffix': file.suffix,
                'is_deleted': file.is_deleted}
        return dict


class FileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = File
        fields = '__all__'

    def get_url(self, obj):
        return obj.file.url

    def get_name(self, obj):
        return obj.filename


class PublicFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PublicFile
        fields = '__all__'

    def get_url(self, obj):
        url = obj.file.url
        clean_url = url.rsplit('?')[0]
        return clean_url
