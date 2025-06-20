from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from files.models import File, PublicFile
from files.serializers import FileSerializer, PublicFileSerializer
from gearfarm.utils import farm_response, simple_responses


class FileList(APIView):
    def get(self, request, format=None):
        response_choices = farm_response
        is_testing_app = request.path.startswith('/api/v1/testing')
        if is_testing_app:
            response_choices = simple_responses

        params = request.GET
        if not {"app_label", 'model', 'object_id'}.issubset(set(params.keys())):
            return response_choices.api_bad_request(
                "参数为必填 [app_label, model, object_id]")

        content_type = ContentType.objects.filter(app_label=params['app_label'], model=params['model'])
        if not content_type.exists():
            return response_choices.api_not_found("model不存在")
        content_type = content_type.first()
        object_id = int(params['object_id'])

        order_by = params.get('order_by', 'created_at')
        order_dir = params.get('order_dir', 'desc')
        if order_dir == 'desc':
            order_by = '-' + order_by

        files = File.objects.filter(content_type_id=content_type.id, object_id=object_id, is_deleted=False).order_by(
            order_by)
        serializer = FileSerializer(files, many=True)
        return response_choices.api_success(data=serializer.data)

    def post(self, request, format=None):
        response_choices = farm_response
        is_testing_app = request.path.startswith('/api/v1/testing')
        if is_testing_app:
            response_choices = simple_responses
        request_data = request.data

        if {"app_label", 'model', 'object_id'}.issubset(set(request_data.keys())):
            content_type = ContentType.objects.filter(app_label=request_data['app_label'], model=request_data['model'])
            if not content_type.exists():
                return response_choices.api_not_found("被评论的model不存在")
            content_type = content_type.first()
            request_data['content_type'] = content_type.id

        serializer = FileSerializer(data=request_data)
        if serializer.is_valid():
            file = serializer.save()
            file.filename = request.data['file'].name
            file.save()
            return response_choices.api_success(data=serializer.data)
        return response_choices.api_bad_request(serializer.errors)


class FileDetail(APIView):
    def get(self, request, id, format=None):
        response_choices = farm_response
        is_testing_app = request.path.startswith('/api/v1/testing')
        if is_testing_app:
            response_choices = simple_responses
        file = get_object_or_404(File, pk=id)
        serializer = FileSerializer(file, many=False)
        return response_choices.api_success(data=serializer.data)

    def delete(self, request, id, format=None):
        response_choices = farm_response
        is_testing_app = request.path.startswith('/api/v1/testing')
        if is_testing_app:
            response_choices = simple_responses
        file = get_object_or_404(File, pk=id)
        file.is_deleted = True
        file.save()
        return response_choices.api_success()


class PublicFileList(APIView):
    def post(self, request, format=None):
        response_choices = farm_response
        is_testing_app = request.path.startswith('/api/v1/testing')
        if is_testing_app:
            response_choices = simple_responses
        serializer = PublicFileSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.save()
            file.filename = request.data['file'].name
            file.save()
            return response_choices.api_success(data=serializer.data)
        return response_choices.api_bad_request(serializer.errors)


class PublicFileDetail(APIView):
    def get(self, request, id, format=None):
        response_choices = farm_response
        is_testing_app = request.path.startswith('/api/v1/testing')
        if is_testing_app:
            response_choices = simple_responses
        file = get_object_or_404(PublicFile, pk=id)
        serializer = PublicFileSerializer(file, many=False)
        return response_choices.api_success(data=serializer.data)
