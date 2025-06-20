from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import serializers

from webphone.models import CallRecord
from farmbase.serializers import UserField
from farmbase.utils import gen_uuid
from proposals.serializers import ProposalField, Proposal
from webphone.tasks import download_call_record_file
from comments.serializers import CommentSerializer


class CallRecordSerializer(serializers.ModelSerializer):
    proposal = ProposalField(queryset=Proposal.objects.all(), required=False, many=False)
    record_start_time = serializers.DateTimeField(format=settings.SAMPLE_DATE_FORMAT, required=False)
    record_date = serializers.DateField(format=settings.SAMPLE_DATE_FORMAT, required=False)
    call_duration = serializers.SerializerMethodField(read_only=True)
    fwd_answer_time = serializers.DateTimeField(format=settings.TIME_FORMAT, required=False)
    call_end_time = serializers.DateTimeField(format=settings.TIME_FORMAT, required=False)
    caller = UserField(many=False, queryset=User.objects.all(), required=False)
    uid = serializers.SerializerMethodField(read_only=True)
    record_file = serializers.SerializerMethodField(read_only=True)
    comments = serializers.SerializerMethodField(read_only=True)
    record_file_size = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CallRecord
        fields = '__all__'

    def get_uid(self, obj):
        if not obj.uid:
            obj.uid = gen_uuid()
            obj.save()
        return obj.uid

    def get_record_file(self, obj):
        if not obj.file and obj.record_domain and obj.record_object_name:
            if obj.record_flag:
                obj.record_flag = 0
                obj.save()
            download_call_record_file.delay(obj.id)
        if obj.file:
            return obj.file.url

    def get_comments(self, obj):
        comments = obj.comments.order_by('created_at')
        return CommentSerializer(comments, many=True).data

    def get_record_file_size(self, obj):
        if obj.file_size:
            return bytes_2_human_readable(int(obj.file_size))

    def get_call_duration(self, obj):
        return obj.get_call_duration()


class ProposalWithCallRecordSerializer(serializers.ModelSerializer):
    call_records = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = '__all__'

    def get_call_records(self, obj):
        call_records = obj.call_records.filter(record_flag=1)
        return CallRecordSerializer(call_records, many=True).data


def bytes_2_human_readable(number_of_bytes):
    if number_of_bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")

    step_to_greater_unit = 1024.

    number_of_bytes = float(number_of_bytes)
    unit = 'bytes'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'KB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'MB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'GB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'TB'

    precision = 1
    number_of_bytes = round(number_of_bytes, precision)

    return str(number_of_bytes) + ' ' + unit
