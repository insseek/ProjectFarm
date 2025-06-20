import logging
from copy import deepcopy

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.views import APIView

from files.models import File
from gearfarm.utils.farm_response import api_bad_request, api_success
from gearfarm.utils import farm_response
from gearmail.models import EmailRecord, EmailTemplate
from gearmail.serializers import EmailRecordSerializer, EmailTemplateSerializer
from gearmail.tasks import send_project_email
from logs.models import Log
from projects.models import Project


@api_view(['POST'])
def send_email_api(request):
    request.data['user'] = request.user.id
    data = request.data
    serializer = EmailRecordSerializer(data=data)

    # 来自草稿箱的邮件
    email_record_id = data.get('email_record', None)
    email_signature = data.get('email_signature', '')
    origin = None
    if email_record_id:
        email_record = get_object_or_404(EmailRecord, pk=email_record_id)
        if email_record.status == 1:
            return api_success("该邮件已经发送成功")
        origin = deepcopy(email_record)
        serializer = EmailRecordSerializer(email_record, data=data)

    if serializer.is_valid():
        email_record = serializer.save()
        message = "邮件已保存至草稿"
        email_record.status = 2
        files = File.objects.filter(id__in=request.data.get('files', []))
        for file in files:
            file.content_object = email_record
            file.save()
        if data.get('to_send', False):
            message = "邮件正在发送，发送成功后你会收到飞书和Farm消息中心通知【你的邮箱也会收到邮件】"
            if settings.DEVELOPMENT:
                send_project_email(request.user.id, email_record.id, email_signature)
            else:
                send_project_email.delay(request.user.id, email_record.id, email_signature)
        if origin:
            Log.build_update_object_log(request.user, origin, email_record, related_object=email_record.project,
                                        comment=message)
        else:
            Log.build_create_object_log(request.user, email_record, related_object=email_record.project,
                                        comment=message)

        serializer = EmailRecordSerializer(email_record)
        return farm_response.api_success(data=serializer.data, message=message)

    return farm_response.api_bad_request(message=str(serializer.errors))


class EmailRecordList(APIView):
    def get(self, request, format=None):
        email_records = EmailRecord.objects.filter(user=request.user)
        serializer = EmailRecordSerializer(email_records, many=True)
        return farm_response.api_success(serializer.data)


class EmailRecordDetail(APIView):
    def get(self, request, id, format=None):
        email_record = get_object_or_404(EmailRecord, pk=id)
        serializer = EmailRecordSerializer(email_record)
        return farm_response.api_success(serializer.data)


class EmailTemplateList(APIView):
    def get(self, request, format=None):
        email_templates = EmailTemplate.objects.all()
        serializer = EmailTemplateSerializer(email_templates, many=True)
        return farm_response.api_success(serializer.data)

    def post(self, request, format=None):
        serializer = EmailTemplateSerializer(data=request.data)
        if serializer.is_valid():
            template = serializer.save()
            Log.build_create_object_log(request.user, template, template)
            return farm_response.api_success(serializer.data)
        return farm_response.api_bad_request(serializer.errors)


class EmailTemplateDetail(APIView):
    def get(self, request, id, format=None):
        email_template = get_object_or_404(EmailTemplate, pk=id)
        serializer = EmailTemplateSerializer(email_template)
        return farm_response.api_success(serializer.data)

    def post(self, request, id, format=None):
        email_template = get_object_or_404(EmailTemplate, pk=id)
        origin = deepcopy(email_template)
        serializer = EmailTemplateSerializer(email_template, data=request.data)
        if serializer.is_valid():
            email_template = serializer.save()
            Log.build_update_object_log(request.user, origin, email_template)
        return farm_response.api_success(serializer.data)

    def delete(self, request, id):
        email_template = get_object_or_404(EmailTemplate, pk=id)
        title = email_template.title
        email_template.delete()
        logger = logging.getLogger()
        logger.info("{}删除了邮件模板{}".format(request.user, title))
        return farm_response.api_success()


class ProjectEmailRecordList(APIView):
    def get(self, request, id, format=None):
        project = get_object_or_404(Project, pk=id)
        email_records = project.email_records.order_by('-created_at')
        serializer = EmailRecordSerializer(email_records, many=True)
        return farm_response.api_success(serializer.data)
