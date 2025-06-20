import logging
import re
from copy import deepcopy
import six
from pprint import pprint

from django.shortcuts import get_object_or_404, reverse
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

from gearfarm.utils.farm_response import build_pagination_response, api_success, api_bad_request
from farmbase.permissions_utils import has_function_perm
from files.models import File
from prototypes.serializers import PrototypeReferenceSerializer, PrototypeReferenceDetailSerializer, PlatformSerializer, \
    CategorySerializer, CollectionSerializer, CollectionDetailSerializer
from prototypes.models import PrototypeReference, Platform, Category, Collection
from taggit.models import Tag
from logs.models import Log
from prototypes.tasks import get_prototype_reference_thumbnail

logger = logging.getLogger()


class PrototypeReferenceList(APIView):
    def get(self, request, format=None):
        if not has_function_perm(request.user, 'view_all_prototype_references'):
            return Response({"result": False, "message": "你没有权限查看项目原想参考列表"})
        prototype_collections = Collection.objects.all().order_by('-created_at')

        filtered_platforms = request.GET.get('platforms', None)
        filtered_categories = request.GET.get('categories', None)
        if filtered_platforms:
            filtered_platforms = re.sub(r'[;；,，]', ' ', filtered_platforms).split()
            prototype_collections = prototype_collections.filter(platforms__name__in=filtered_platforms).distinct()
        if filtered_categories:
            filtered_categories = re.sub(r'[;；,，]', ' ', filtered_categories).split()
            prototype_collections = prototype_collections.filter(categories__name__in=filtered_categories).distinct()

        return build_pagination_response(request, prototype_collections, CollectionSerializer)


class PrototypeReferenceDetail(APIView):
    def get(self, request, id, format=None):
        prototype_reference = get_object_or_404(PrototypeReference, pk=id)
        serializer = PrototypeReferenceDetailSerializer(prototype_reference, many=False)
        return api_success(serializer.data)

    def delete(self, request, id, format=None):
        prototype_reference = get_object_or_404(PrototypeReference, pk=id)
        origin = deepcopy(prototype_reference)
        if request.user.id == prototype_reference.submitter_id or has_function_perm(request.user,
                                                                                    'delete_prototype_references') or request.user.is_superuser:
            prototype_reference.delete()
            if origin.collection:
                Log.build_delete_object_log(request.user, origin, related_object=origin.collection)
                if not origin.collection.prototype_references.exists():
                    origin_collection = deepcopy(origin.collection)
                    origin.collection.delete()
                    if origin_collection.categories.exists():
                        Log.build_delete_object_log(request.user, origin_collection,
                                                    related_object=origin_collection.categories.first())
            return api_success(message='文件删除成功')
        return api_bad_request('你没有权限删除该图片，请联系图片提交人或管理员')


class PrototypeCollectionDetail(APIView):
    def get(self, request, id, format=None):
        prototype_collection = get_object_or_404(Collection, pk=id)
        serializer = CollectionDetailSerializer(prototype_collection, many=False)
        return api_success(serializer.data)


@api_view(['POST'])
@transaction.atomic
def batch_upload_prototype_references(request, collection_id=None):
    if 'file' not in request.data:
        return Response({'result': False, 'message': '缺少有效文件'})
    files = request.data.getlist('file')
    platforms = request.data.get('platforms', [])
    categories = request.data.get('categories', [])
    if isinstance(platforms, six.string_types):
        platforms = re.sub(r'[;；,，]', ' ', platforms).split()
    if isinstance(categories, six.string_types):
        categories = re.sub(r'[;；,，]', ' ', categories).split()
    cover_picture = request.data.get('cover_picture', '')
    old_cover = None
    savepoint = transaction.savepoint()
    if collection_id:
        collection = get_object_or_404(Collection, pk=collection_id)
        old_cover = deepcopy(collection.cover_picture)
    else:
        collection_data = {}
        collection_data['submitter'] = request.user.id
        collection_serializer = CollectionSerializer(data=collection_data)
        if collection_serializer.is_valid():
            collection = collection_serializer.save()
            add_platforms_and_categories(collection, platforms, categories)
        else:
            return api_bad_request(message=collection_serializer.errors)

    new_cover = False
    for file in files:
        reference_data = {}
        reference_data['file'] = file
        reference_data['filename'] = file.name
        reference_data['submitter'] = request.user.id
        reference_data['collection'] = collection.id
        serializer = PrototypeReferenceSerializer(data=reference_data)
        if serializer.is_valid():
            prototype_reference = serializer.save()
            if not new_cover and cover_picture and cover_picture == file.name:
                prototype_reference.is_cover = True
                prototype_reference.save()
                new_cover = True
            if collection_id:
                prototype_reference.categories.add(*collection.categories.all())
                prototype_reference.platforms.add(*collection.platforms.all())
            else:
                add_platforms_and_categories(prototype_reference, platforms, categories)
            get_prototype_reference_thumbnail.delay(prototype_reference.id)
        else:
            logger.error(serializer.errors)
            transaction.savepoint_rollback(savepoint)
            return Response({'result': False, 'message': str(serializer.errors)},
                            status=status.HTTP_400_BAD_REQUEST)
    if new_cover and old_cover:
        old_cover.is_cover = False
        old_cover.save()
    return api_success()


def add_platforms_and_categories(prototype_reference, platforms: list, categories: list):
    for platform in platforms:
        if not Platform.objects.filter(name=platform).exists():
            Platform.objects.create(name=platform)
    for category in categories:
        if not Category.objects.filter(name=category).exists():
            Category.objects.create(name=category)
    platform_list = Platform.objects.filter(name__in=platforms)
    prototype_reference.platforms.add(*platform_list)
    category_list = Category.objects.filter(name__in=categories)
    prototype_reference.categories.add(*category_list)


@api_view(['GET'])
def prototype_reference_filter_data(request):
    platforms = Platform.objects.all()
    platforms_data = PlatformSerializer(platforms, many=True).data

    categories = Category.objects.all()
    categories_data = CategorySerializer(categories, many=True).data
    return api_success({'platforms': platforms_data, 'categories': categories_data})


@api_view(['POST'])
def prototype_reference_tags(request, id, format=None):
    prototype_reference = get_object_or_404(PrototypeReference, pk=id)
    tags = request.data.get('tags', [])
    if 'tags' in request.data:
        prototype_reference.tags.clear()
    if isinstance(tags, six.string_types):
        tags = re.sub(r'[;；,，]', ' ', tags).split()
    if tags:
        prototype_reference.tags.add(*tags)
    serializer = PrototypeReferenceDetailSerializer(prototype_reference, many=False)
    return api_success(serializer.data)


@api_view(['GET'])
def prototype_reference_siblings(request, id, format=None):
    prototype_reference = get_object_or_404(PrototypeReference, pk=id)
    filtered_platform = prototype_reference.platforms.all().values_list('id', flat=True)
    filtered_categories = prototype_reference.categories.all().values_list('id', flat=True)
    prototype_references = PrototypeReference.objects.all().distinct()
    if filtered_platform:
        prototype_references = prototype_references.filter(platforms__id__in=filtered_platform).distinct()
    if filtered_categories:
        prototype_references = prototype_references.filter(categories__id__in=filtered_categories).distinct()
    siblings = prototype_references.exclude(pk=id)
    siblings_data = PrototypeReferenceSerializer(siblings, many=True).data
    own_data = PrototypeReferenceSerializer(prototype_reference).data
    siblings_data.insert(0, own_data)
    return api_success(siblings_data)
