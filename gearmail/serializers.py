from django.contrib.auth.models import User
from rest_framework import serializers

from farmbase.serializers import UserField
from gearmail.models import EmailRecord, EmailTemplate
from projects.models import Project
from projects.serializers import ProjectField
from files.models import File


class FileField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        file = File.objects.get(pk=value.pk)
        dict = {"id": value.pk, "url": file.file.url, "name": file.filename, 'suffix': file.suffix}
        return dict


class EmailTemplateField(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        if not value:
            return None
        email_template = EmailTemplate.objects.get(pk=value.pk)
        dict = {"id": value.pk, "subject": email_template.subject, "title": email_template.title}
        return dict


class EmailRecordSerializer(serializers.ModelSerializer):
    user = UserField(many=False, queryset=User.objects.all())
    project = ProjectField(many=False, queryset=Project.objects.all(), required=False)
    template = EmailTemplateField(many=False, queryset=EmailTemplate.objects.all(), required=False)
    files = FileField(many=True, read_only=True)

    class Meta:
        model = EmailRecord
        fields = '__all__'


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = '__all__'
