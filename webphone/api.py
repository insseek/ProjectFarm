from copy import deepcopy
import logging
import pprint
import re

from django.shortcuts import get_object_or_404, reverse
from django.conf import settings
from rest_framework.response import Response
from rest_framework.decorators import api_view
from pypinyin import pinyin, lazy_pinyin
from django.utils.http import urlquote, urlunquote
from rest_framework import status
from django.db.models import Sum, IntegerField, When, Case, Q
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from wsgiref.util import FileWrapper
from django.http import FileResponse, HttpResponseNotFound
from django.utils.encoding import escape_uri_path

from farmbase.permissions_utils import func_perm_required
from farmbase.decorators import csrf_ignore
from .models import HuaWeiVoiceCallAuth, CallRecord
from farmbase.serializers import UserSimpleSerializer, UserFilterSerializer
from .serializers import CallRecordSerializer, ProposalWithCallRecordSerializer
from webphone.huawei_viocecall import HuaWeiVoiceCall
from proposals.models import Proposal
from .utils import change_camel_case_data_to_under_score_case_data, get_valid_china_phone_number, \
    change_huawei_fee_info_case_and_set_time_filed
from .call_data import call_disconnect_code_data
from notifications.tasks import send_call_status_notice
from .tasks import download_call_record_file
from logs.models import Log

logger = logging.getLogger()


@api_view(['GET'])
def get_token(request):
    voice_call = HuaWeiVoiceCall()
    access_token = voice_call.get_access_token()
    if access_token:
        return Response(
            {'result': True, 'token': access_token, 'identity': request.user.username, 'result_desc': 'Succeed',
             'result_code': '0'})
    else:
        return Response({'result': False, 'result_desc': "获取不到有效的Token,请联系管理员"})


@api_view(['POST'])
def click2call(request):
    voice_call = HuaWeiVoiceCall()
    request_data = deepcopy(request.data)
    proposal = None
    record_flag = settings.HUAWEI_VOICE_RECORD_FLAG
    if request_data.get('proposal', None):
        proposal = get_object_or_404(Proposal, pk=request_data.get('proposal'))
    caller_number = request_data.get('caller_number', None)
    callee_number = request_data.get('callee_number', None)
    if all([caller_number, callee_number]):
        valid_callee_number = get_valid_china_phone_number(callee_number)
        valid_caller_number = get_valid_china_phone_number(caller_number)
        user_data = urlquote(request.user.username)
        # user_data = ''.join(lazy_pinyin(request.user.username))
        result = voice_call.click2call(caller_number=valid_caller_number, callee_number=valid_callee_number,
                                       record_flag=record_flag,
                                       user_data=user_data)
        logger.info("请求呼叫接口：{}".format(result))
        result_code = result.get('resultcode', None)
        result_desc = result.get('resultdesc')
        if result_code in {'1010003', '1010004', '1010005'}:
            voice_call.refresh_and_get_token_data()
            result = voice_call.click2call(caller_number=valid_caller_number, callee_number=valid_callee_number,
                                           record_flag=record_flag)
            result_code = result.get('resultcode', None)
            # voice_call.refresh_access_token()
            result_desc = result.get('resultdesc')
        if result_code == '0':
            session_id = result.get('sessionId')
            record_data = {}
            if proposal:
                record_data['proposal'] = proposal.id
            record_data['caller'] = request.user.id
            record_data['caller_number'] = caller_number
            record_data['callee_number'] = callee_number
            record_data['session_id'] = session_id
            record_data['record_date'] = timezone.now().date()
            serializer = CallRecordSerializer(data=record_data)
            if serializer.is_valid():
                call_record = serializer.save()
                Log.build_create_object_log(request.user, call_record, call_record.proposal, "拨打电话")
                return Response(
                    {'result': True, 'session_id': session_id, 'result_code': result_code, 'result_desc': result_desc})
            return Response({"result": False, "message": str(serializer.errors)})
        else:
            return Response({'result': False, 'message': result.get('resultdesc'), 'result_code': result_code,
                             'result_desc': result_desc})
    else:
        return Response({'result': False, 'result_desc': '请填写正确的主叫、被叫手机号', 'result_code': '1010002', })


@api_view(['POST'])
def stop_call(request):
    voice_call = HuaWeiVoiceCall()
    request_data = deepcopy(request.data)
    session_id = request_data.get('session_id', None)
    if session_id:
        result = voice_call.stop_call(session_id=session_id)
        result_code = result.get('resultcode', None)
        result_desc = result.get('resultdesc')
        if result_code == '1010004' or result_code == '1010005':
            voice_call.login_and_update_authorization()
            result = voice_call.stop_call(session_id=session_id)
            result_code = result.get('resultcode', None)
            result_desc = result.get('resultdesc')
        if result_code == '0':
            return Response({'result': True, 'result_code': result_code, 'result_desc': result_desc})
        elif result_code == '1020152' or result_code == '1010002':
            return Response({'result': True, 'result_code': result_code, 'result_desc': "当前呼叫已结束"})
        else:
            return Response({'result': False, 'result_code': result_code, 'result_desc': result_desc})
    else:
        return Response({'result': False, 'result_code': '1020152', 'result_desc': 'Invalid Call SessionId'})


@csrf_ignore
@api_view(['POST'])
def call_status_notice(request):
    request_data = deepcopy(request.data)
    event_type = request_data['eventType']
    session_id = request_data['statusInfo']['sessionId']
    called = request_data['statusInfo']['called']
    logger.info("获得呼叫状态通知:{}".format(request_data))
    if request_data.get('userData', ''):
        request_data['userData'] = urlunquote(request_data['userData'])
    call_record = CallRecord.objects.filter(session_id=session_id)
    if call_record.exists():
        notice_data = {"eventType": event_type}
        if event_type == 'callout':
            notice_data["message"] = "已向号码{}发出呼叫".format(called)
        if event_type == 'alerting':
            notice_data["message"] = "号码{}已响铃".format(called)
        if event_type == 'answer':
            notice_data["message"] = "号码{}已接听".format(called)
        if event_type == 'disconnect':
            state_desc = request_data['statusInfo']['stateDesc']
            state_code = request_data['statusInfo']['stateCode']
            state_code_desc = call_disconnect_code_data.get(state_code, "")
            if state_code_desc:
                state_desc = state_code_desc + ", " + state_desc
            notice_data["message"] = "当前通话已结束：{}".format(state_desc)
        try:
            send_call_status_notice(notice_data, session_id)
        except Exception as e:
            logger.error(e)
    return Response({'result': True, 'result_code': 0, 'result_desc': "Succeed"})


@csrf_ignore
@api_view(['POST'])
def call_fee_notice(request):
    request_data = deepcopy(request.data)
    event_type = request_data['eventType']
    fee_list = request_data['feeLst']
    logger.info("获得话单通知:{}".format(request_data))
    for fee_info in fee_list:
        if fee_info.get('userData', None):
            fee_info['userData'] = urlunquote(fee_info['userData'])
        fee_info_data = change_huawei_fee_info_case_and_set_time_filed(fee_info)
        session_id = fee_info_data['session_id']
        records = CallRecord.objects.filter(session_id=session_id)
        if records.exists():
            call_record = records.first()
            if call_record.proposal_id:
                fee_info_data['proposal'] = call_record.proposal_id
            if call_record.proposal_id:
                fee_info_data['caller'] = call_record.caller_id
            if call_record.caller_number:
                fee_info_data['caller_number'] = call_record.caller_number
            if call_record.callee_number:
                fee_info_data['callee_number'] = call_record.callee_number
        if call_records.filter(icid=fee_info_data.get('icid')).exists():
            call_record = call_records.filter(icid=fee_info_data.get('icid')).first()
            serializer = CallRecordSerializer(call_record, data=fee_info_data)
        elif call_records.filter(icid__isnull=True).exists():
            call_record = call_records.filter(icid__isnull=True).first()
            serializer = CallRecordSerializer(call_record, data=fee_info_data)
        else:
            serializer = CallRecordSerializer(data=fee_info_data)

        if serializer.is_valid():
            call_fee_record = serializer.save()
            if call_fee_record.record_file_download_url and not call_fee_record.record_file:
                download_call_record_file.delay(call_fee_record.id)
        else:
            raise Exception("生成话单失败" + str(serializer.errors))
        notice_data = {"eventType": event_type, 'message': "当前通话结束，并记录，可重新拨打电话"}

        try:
            send_call_status_notice(notice_data, session_id)
        except Exception as e:
            logger.error(e)
        # VoiceCallFeeRecord.objects.update_or_create(
        #     defaults={'session_id': session_id, 'icid': fee_info_data.get('icid', None)}, **fee_info_data)
    return Response({'result': True, 'result_code': 0, 'result_desc': "Succeed"})


@api_view(['GET'])
def call_records(request):
    if not {'page', 'page_size'}.issubset(request.GET.keys()):
        return Response({"result": False}, status=status.HTTP_400_BAD_REQUEST)
    search_value = request.GET.get('search_value', None)
    page = int(request.GET.get('page'))
    page_size = int(request.GET.get('page_size'))
    submitters = request.GET.get('submitters', None)
    callers = request.GET.get('callers', None)

    records = CallRecord.objects.filter(record_flag=1).order_by('number')
    if submitters:
        submitter_list = re.sub(r'[;；,，]', ' ', submitters).split()
        records = records.filter(submitter_id__in=submitter_list).distinct()
    if callers:
        caller_list = re.sub(r'[;；,，]', ' ', callers).split()
        records = records.filter(caller_id__in=caller_list).distinct()
    if search_value:
        records = records.filter(

            (Q(proposal__name__isnull=False) & Q(proposal__name__icontains=search_value)) | (
                (Q(proposal__name__isnull=True) & Q(proposal__description__icontains=search_value))) | Q(
                filename__icontains=search_value) | Q(caller__username__icontains=search_value)).distinct()
    count = records.count()
    call_records_data = CallRecordSerializer(records, many=True).data
    group_data = {}
    for call_record in call_records_data:
        proposal_id = call_record['proposal']['id'] if call_record['proposal'] else 0
        if proposal_id:
            group_key = (proposal_id, 0)
        else:
            group_key = (0, call_record['id'])
        if group_key in group_data:
            group_data[group_key]['call_records'].append(call_record)
            if call_record['created_at'] > group_data[group_key]['created_at']:
                group_data[group_key]['created_at'] = call_record['created_at']
        else:
            group_data[group_key] = {}
            group_data[group_key]['proposal'] = call_record['proposal']
            group_data[group_key]['call_records'] = [call_record, ]
            group_data[group_key]['created_at'] = call_record['created_at']
    sorted_record_data = sorted(group_data.values(), key=lambda record_data: record_data['created_at'], reverse=True)
    group_count = len(sorted_record_data)
    # 获取分页 起始 和 结束位置
    record_group_start = int(page - 1) * int(page_size)
    record_group_end = int(page) * int(page_size)
    if record_group_start < 0:
        record_group_start = 0
    if record_group_end < 0:
        record_group_end = 0
    page_records = sorted_record_data[record_group_start:record_group_end]
    return Response(
        {'result': True, 'group_count': group_count, 'page': page, 'page_size': page_size, 'count': count,
         'data': page_records})


@api_view(['GET'])
def my_call_records(request):
    current_login_user = request.user
    records = current_login_user.call_records.all()
    record_flag = request.GET.get('record_flag', 0)
    if int(record_flag) == 1:
        records = records.filter(record_flag=1).distinct()
    data = CallRecordSerializer(records, many=True).data
    return Response({"result": True, "data": data})


@api_view(['GET'])
def call_record_users(request):
    records = CallRecord.objects.all()

    submitter_id_list = [pm for pm in set(records.values_list('submitter_id', flat=True)) if pm]
    caller_id_list = [bd for bd in set(records.values_list('caller_id', flat=True)) if bd]
    submitters = User.objects.filter(id__in=submitter_id_list).order_by('-is_active', 'date_joined')
    callers = User.objects.filter(id__in=caller_id_list).order_by('-is_active', 'date_joined')
    submitter_list = UserFilterSerializer(submitters, many=True).data
    caller_list = UserFilterSerializer(callers, many=True).data

    return Response({"result": True, 'submitters': submitter_list, 'callers': caller_list})


@api_view(['GET'])
def call_record_detail(request, id):
    call_record = get_object_or_404(CallRecord, pk=id)
    serializer = CallRecordSerializer(call_record)
    return Response({"result": True, 'data': serializer.data})


@api_view(['GET'])
@func_perm_required('download_call_records')
def download_call_record(request, uid):
    call_record = get_object_or_404(CallRecord, uid=uid)
    if call_record.file:
        wrapper = FileWrapper(call_record.file.file)
        response = FileResponse(wrapper, content_type='application/{}'.format(call_record.file_suffix))
        response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(
            escape_uri_path(call_record.filename))
        return response
    else:
        return HttpResponseNotFound
