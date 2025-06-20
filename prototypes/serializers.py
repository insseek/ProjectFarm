from django.contrib.auth.models import User
from django.conf import settings

from farmbase.serializers import UserField
from rest_framework import serializers
from taggit.models import Tag
from prototypes.models import PrototypeReference, Platform, Category, Collection
from comments.serializers import CommentSerializer
from prototypes.tasks import get_prototype_reference_thumbnail


class PlatformField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        technology_type = Platform.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": technology_type.name}
        return dict


class CategoryField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        industry_classification = Category.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": industry_classification.name}
        return dict


class TagField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        tag = Tag.objects.get(pk=value.pk)
        dict = {"id": value.pk, "name": tag.name}
        return dict


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class PrototypeReferenceSerializer(serializers.ModelSerializer):
    platforms = PlatformSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagField(many=True, read_only=True)
    submitter = UserField(many=False, queryset=User.objects.all())
    filename = serializers.CharField(required=False)
    thumbnails = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PrototypeReference
        fields = '__all__'

    def get_thumbnails(self, obj):
        file_url = obj.file.url
        thumbnails = {'small': file_url, 'middle': file_url, 'large': file_url}
        if obj.thumbnail:
            thumbnails['small'] = obj.thumbnail['small'].url
            thumbnails['middle'] = obj.thumbnail['middle'].url
            thumbnails['large'] = obj.thumbnail['large'].url
        else:
            get_prototype_reference_thumbnail.delay(obj.id)

        return thumbnails


class PrototypeReferenceDetailSerializer(serializers.ModelSerializer):
    platforms = PlatformSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    tags = TagField(many=True, queryset=Tag.objects.all())
    comments = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.DateTimeField(format=settings.DATE_FORMAT, required=False)
    thumbnails = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PrototypeReference
        fields = '__all__'

    def get_comments(self, obj):
        comments = obj.comments.order_by('-is_sticky', 'created_at')
        return CommentSerializer(comments, many=True).data

    def get_thumbnails(self, obj):
        file_url = obj.file.url
        thumbnails = {'small': file_url, 'middle': file_url, 'large': file_url}
        if obj.thumbnail:
            thumbnails['small'] = obj.thumbnail['small'].url
            thumbnails['middle'] = obj.thumbnail['middle'].url
            thumbnails['large'] = obj.thumbnail['large'].url
        else:
            get_prototype_reference_thumbnail.delay(obj.id)

        return thumbnails


class CollectionSerializer(serializers.ModelSerializer):
    platforms = PlatformSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    created_at = serializers.DateTimeField(format=settings.DATE_FORMAT, required=False)
    cover_picture = PrototypeReferenceSerializer(read_only=True)

    class Meta:
        model = Collection
        fields = '__all__'


class CollectionDetailSerializer(serializers.ModelSerializer):
    platforms = PlatformSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    submitter = UserField(many=False, queryset=User.objects.all(), required=False)
    created_at = serializers.DateTimeField(format=settings.DATE_FORMAT, required=False)
    prototype_references = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Collection
        fields = '__all__'

    def get_prototype_references(self, obj):
        references = obj.prototype_references.all().order_by('-is_cover', '-created_at')
        data = PrototypeReferenceDetailSerializer(references, many=True).data
        return data
