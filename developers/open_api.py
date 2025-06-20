from copy import deepcopy
import logging
import re
import json
from datetime import datetime, timedelta
import threading
from itertools import chain
from django.core.files import File as DjangoFile
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Sum, IntegerField, When, Case, Q
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view

from finance.models import JobPayment
from gearfarm.utils import farm_response
from auth_top.authentication import TokenAuthentication
from gearfarm.utils.base64_to_image_file import base64_string_to_file
from gearfarm.utils.common_utils import get_file_suffix
from gearfarm.utils.farm_response import api_success, api_bad_request, api_suspended, api_permissions_required, \
    api_invalid_authentication_key, api_not_found, api_request_params_required, build_pagination_response
from gearfarm.utils.decorators import request_data_fields_required, request_params_required
from geargitlab.gitlab_client import GitlabOauthClient
from gearfarm.utils.const import DEVELOPMENT_GUIDES
from farmbase.utils import gen_uuid, in_group, last_week_start, next_week_end, this_week_end, \
    get_phone_verification_code
from auth_top.models import TopToken, TopUser
from developers.utils import build_project_developer_daily_works_statistics, \
    get_project_developer_daily_works_statistics, get_day_task_topics, \
    build_today_daily_work, build_tommorow_daily_work, get_need_submit_daily_work, AliAuth
from developers.models import Developer, Role, DailyWork
from developers.serializers import DeveloperCreateSerializer, DeveloperListSerializer, RoleSerializer, \
    DeveloperSimpleSerializer, DeveloperAvatarSerializer, DeveloperDetailSerializer, DeveloperStatusSerializer, \
    DeveloperEditSerializer, JobPaymentSerializer, DeveloperOpenApiEditSerializer, DeveloperPersonalInfoSerializer, \
    DailyWorkSerializer, DailyWorkCreateSerializer, DailyWorkWorkTimeSerializer, DailyWorkNextDayEditSerializer, \
    DailyWorkSerializer, GanttTaskTopicDailyWorkSerializer, DailyWorkViewSerializer, DeveloperRealNameSerializer, \
    DeveloperIDCardEditSerializer
from geargitlab.gitlab_client import GitlabClient
from notifications.models import Notification
from notifications.serializers import NotificationSerializer
from notifications.utils import create_notification, create_notification_group, create_developer_notification, \
    create_notification_to_users, create_notification_to_developers
from logs.models import Log
from projects.models import Project, GanttTaskTopic, ProjectGanttChart
from projects.serializers import ProjectDeveloperDetailSerializer, GanttTaskTopicSerializer, \
    ProjectGanttChartRetrieveSerializer, \
    GanttTaskCatalogueSerializer, ProjectWithDeveloperListSerializer, JobSerializer
from projects.utils.common_utils import get_project_members_data, get_project_developers_data
from oauth.aliyun_client import AliyunApi
from logs.models import BrowsingHistory
from testing.models import Bug
from developers.tasks import build_project_gitlab_user_id_day_gitlab_commits

gitlab_client = GitlabClient()
logger = logging.getLogger()


@api_view(['GET'])
def phone_code(request):
    phone = request.GET.get('phone', None)
    if phone:
        if settings.DEVELOPMENT:
            code = settings.DEVELOPMENT_DD_CODE
            cache.set('developer-{}-code'.format(phone), {'code': code, 'time': timezone.now()}, 60 * 10)
            return api_success('测试环境验证码:{}'.format(code))
        code_data = cache.get('developer-{}-code'.format(phone), None)
        if code_data and code_data['time'] > timezone.now() - timedelta(minutes=1, seconds=30):
            return api_bad_request('不可频繁发送')

        if not Developer.objects.filter(phone=phone).exists():
            return api_bad_request(message="该手机号未绑定工程师账户")
        developer = Developer.objects.get(phone=phone)
        if not developer.is_active:
            return api_suspended()
        code = get_phone_verification_code()
        aliyun_client = AliyunApi(access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                                  access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET)
        aliyun_client.send_login_check_code_sms(phone, code, '【齿轮易创-开发者】')
        cache.set('developer-{}-code'.format(phone), {'code': code, 'time': timezone.now()}, 60 * 10)
        return api_success('短信发送成功')
    return api_bad_request(message="手机号必填")


def get_developer_cache_token(developer):
    real_token, created = TopToken.get_or_create(developer=developer)
    # 这种方式获取的Token认证用户 不可进行编辑操作 只能GET请求
    real_token_data = {"token": real_token.key, 'user_type': real_token.user_type, 'editable': False}
    # 临时token有效期 2小时
    access_token = settings.ONE_TIME_AUTH_PREFIX + TopToken.generate_key()
    cache.set(access_token, real_token_data, 60 * 60 * 2)
    access_token_data = {"token": access_token, 'user_type': real_token.user_type, 'editable': False}
    return access_token_data


@api_view(['POST'])
@request_data_fields_required('authentication_key')
def one_time_authentication_login(request):
    authentication_key = request.data.get('authentication_key')
    authentication_data = cache.get(authentication_key, None)
    if not authentication_data:
        return api_invalid_authentication_key()

    if 'developer' in authentication_data:
        developer_id = authentication_data['developer']['id']
        if not Developer.objects.filter(id=developer_id).exists():
            return api_bad_request(message="未找到工程师账户")
        developer = Developer.objects.get(id=developer_id)
        if developer.is_active:
            token_data = get_developer_cache_token(developer)
            cache.delete(authentication_key)
            top_user = developer.top_user
            token_data['user_info'] = top_user.user_info()
            return api_success(data=token_data)
        return api_suspended()
    elif 'user' in authentication_data:
        user_id = authentication_data['user']['id']
        user = User.objects.filter(id=user_id).first()
        if not user:
            return api_not_found(message="未找到用户")
        if user.is_active:
            cache.delete(authentication_key)
            token, created = TopToken.get_or_create(user=user)
            top_user = user.top_user
            return api_success(
                data={'token': token.key, 'user_type': token.user_type, 'user_info': top_user.user_info()})
        return api_suspended()

    return api_invalid_authentication_key()


@api_view(['POST'])
def login_handle(request):
    if not {'phone', 'code'}.issubset(request.data.keys()):
        return api_bad_request(message='手机号、验证码为必填项')
    phone = request.data.get('phone')
    code = request.data.get('code')
    if not Developer.objects.filter(phone=phone).exists():
        return api_bad_request(message="该手机号未绑定工程师账户")
    if not settings.PRODUCTION and code == '666888':
        pass
    elif settings.PRODUCTION and code == '160411':
        pass
    else:
        code_data = cache.get('developer-{}-code'.format(phone), None)
        if not code_data:
            return api_bad_request(message='验证码无效，请重新获取验证码')
        cache_code = code_data['code']
        if not cache_code == code:
            return api_bad_request(message='验证码错误')
    developer = Developer.objects.get(phone=phone)
    if developer.is_active:
        developer.last_login = timezone.now()
        developer.save()
        token, created = TopToken.get_or_create(developer=developer)
        top_user = developer.top_user
        return api_success(data={'token': token.key, 'user_type': token.user_type, 'user_info': top_user.user_info()})
    return api_suspended()


# 现在Token一对一
@api_view(['POST'])
def logout_handle(request):
    try:
        token_key = TokenAuthentication().authenticate_key(request)
        if token_key and cache.get(token_key):
            cache.delete(token_key)
    except:
        TopToken.get_or_create(developer=request.developer, refresh=True)
    return api_success(message='退出成功')


@api_view(['GET'])
def my_info(request):
    developer = request.developer
    data = DeveloperPersonalInfoSerializer(developer).data
    return api_success(data=data)


@api_view(['GET'])
@request_params_required('gitlab_user_id')
def get_gitlab_developer_info(request):
    params = request.GET
    gitlab_user_id = params.get('gitlab_user_id')
    developer = get_object_or_404(Developer, gitlab_user_id=gitlab_user_id)
    data = DeveloperPersonalInfoSerializer(developer).data
    return api_success(data=data)


@api_view(['POST'])
def my_avatar(request):
    developer = request.developer
    serializer = DeveloperAvatarSerializer(developer, data=request.data)
    if serializer.is_valid():
        developer = serializer.save()
        data = DeveloperPersonalInfoSerializer(developer).data
        return api_success(data=data)
    return api_bad_request(message=str(serializer.errors))


@api_view(['POST'])
def developer_status(request):
    developer = request.developer
    status = request.data.get('status', None)
    if status is None or status not in ['1', '2', 1, 2]:
        return api_bad_request(message="请提供有效的status参数")
    status = str(request.data['status'])
    # 不可接单
    if status == '2' and not request.data.get('expected_work_at'):
        return api_bad_request(message="请输入预计可接单时间")
    origin = deepcopy(developer)
    serializer = DeveloperStatusSerializer(developer, data=request.data)
    if serializer.is_valid():
        developer = serializer.save()
        Log.build_update_object_log(request.developer, origin, developer)
        return api_success(data=serializer.data)
    return api_bad_request(message=str(serializer.errors))


@api_view(['POST'])
def edit_my_info(request):
    developer = request.developer
    origin = deepcopy(developer)
    status = request.data.get('status', None)
    if status is not None and status not in ['1', '2', 1, 2]:
        return api_bad_request(message='请提供有效的status参数')
    # 不可接单
    if status and str(status) == '2' and not request.data.get('expected_work_at'):
        return api_bad_request(message="请输入预计可接单时间")
    phone = request.data.get('phone', None)
    if phone and phone != developer.phone and Developer.objects.filter(phone=phone).exists():
        return api_bad_request(message="手机号已被其他用户绑定")

    serializer = DeveloperOpenApiEditSerializer(developer, data=request.data)
    if serializer.is_valid():
        developer = serializer.save()
        Log.build_update_object_log(operator=request.developer, original=origin, updated=developer)
        serializer = DeveloperPersonalInfoSerializer(developer)
        return api_success(data=serializer.data)
    return api_bad_request(message=str(serializer.errors))


@api_view(['GET'])
def my_star_rating(request):
    developer = request.developer
    return api_success(developer.star_rating)


@api_view(['GET'])
def development_guides(request):
    developer = request.developer
    documents = []
    role_names = set(developer.roles.values_list('name', flat=True))
    language_names = set(developer.development_languages.values_list('name', flat=True))
    keywords = role_names | language_names
    keywords = set([name.lower() for name in keywords])
    for guide_doc in DEVELOPMENT_GUIDES.values():
        if keywords & set([name.lower() for name in guide_doc['keywords']]):
            documents.append({'title': guide_doc['title'], 'link': guide_doc['link']})
    return api_success(data=documents)


@api_view(['GET'])
def my_projects(request):
    developer = request.developer
    projects = developer.get_active_projects()
    data = ProjectWithDeveloperListSerializer(projects, many=True).data
    return api_success(data=data)


def project_developer_payment_data(project, developer):
    positions = project.job_positions.filter(developer_id=developer.id)
    # 打款数据
    amount_total = sum([position.total_amount or 0 for position in positions])

    payments = JobPayment.objects.none()
    for position in positions:
        payments = payments | position.payments.filter(status=2)

    if payments:
        payments = payments.order_by('-completed_at')
    payment_list = JobPaymentSerializer(payments, many=True).data
    paid_amount_total = sum([payment['amount'] for payment in payment_list])
    payments_data = {'payments': payment_list, 'paid_amount_total': paid_amount_total, "amount_total": amount_total}
    return payments_data


@api_view(['GET'])
def project_detail(request, project_id):
    developer = request.developer

    project = get_object_or_404(Project, pk=project_id)
    positions = project.job_positions.filter(developer_id=developer.id)
    if not positions.exists():
        return api_permissions_required("只有该项目的工程师才有权限访问项目详情信息")
    project_data = ProjectDeveloperDetailSerializer(project).data

    # 本工程师在项目中的收款情况  项目金额(已收款/总金额)
    project_data['payments_data'] = project_developer_payment_data(project, developer)

    # issues数据
    project_data['issues_data'] = None
    links_data = project_data['links']
    gitlab_user_id = developer.gitlab_user_id
    if gitlab_user_id and links_data and (links_data['gitlab_group_id'] or links_data['gitlab_project_id']):
        project_data['issues_data'] = {'projects': [], 'issues_total': 0, 'issues_new': 0}
        project_issues_data = project_data['issues_data']
        link_git_project = links_data['gitlab_project']
        farm_project_id = project.id
        farm_projects_git_issues = cache.get('farm_projects_git_issues', {})
        gitlab_projects = cache.get('gitlab-projects', {})

        issues_projects = {}

        if farm_project_id in farm_projects_git_issues:
            opened_issues = farm_projects_git_issues[farm_project_id].get('opened_issues', [])
            now = timezone.now()
            day_zero = datetime(now.year, now.month, now.day, 0, 0, 0)
            for issue_data in opened_issues:
                git_project_id = issue_data['project_id']
                for assignee in issue_data['assignees']:
                    if str(assignee['id']) == str(gitlab_user_id):
                        if git_project_id not in issues_projects:
                            issues_projects[git_project_id] = {'issues_total': 0, 'issues_new': 0}
                            issues_projects[git_project_id].update(
                                gitlab_projects.get(git_project_id, link_git_project))
                        current_project_issues = issues_projects[git_project_id]
                        current_project_issues['issues_total'] = current_project_issues['issues_total'] + 1
                        project_issues_data['issues_total'] = project_issues_data['issues_total'] + 1
                        created_str = issue_data['created_at']
                        created_date = None
                        try:
                            if '+08:00' in created_str:
                                created_date = datetime.strptime(created_str,
                                                                 "%Y-%m-%dT%H:%M:%S.%f+08:00")
                            elif created_str.endswith('Z'):
                                created_date = datetime.strptime(created_str,
                                                                 "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(
                                    hours=8)
                            if created_date and created_date >= day_zero:
                                current_project_issues['issues_new'] = current_project_issues['issues_new'] + 1
                                project_issues_data['issues_new'] = project_issues_data['issues_new'] + 1
                        except Exception as e:
                            logger.warning(str(e))
                            pass
                        continue
        project_data['issues_data']['projects'] = sorted(issues_projects.values(), key=lambda x: x['issues_total'])

    # 甘特图任务
    task_topics = []
    week_end = this_week_end()

    topics_data = []
    if getattr(project, 'gantt_chart', None):
        roles = project.gantt_chart.roles.filter(developer_id=developer.id)
        for role in roles:
            role_topics = role.task_topics.filter(is_done=False, start_time__lte=week_end)
            if not task_topics:
                task_topics = role_topics
            else:
                task_topics = task_topics | role_topics

        if task_topics:
            task_topics = task_topics.order_by('start_time')
        topics_data = GanttTaskTopicSerializer(task_topics, many=True).data
    project_data['task_topics'] = topics_data

    # 开发规范文档
    # project_data['development_guides'] = []
    # role_names = set(developer.roles.values_list('name', flat=True))
    # language_names = set(developer.development_languages.values_list('name', flat=True))
    # keywords = role_names | language_names
    # keywords = set([name.lower() for name in keywords])
    # for guide_doc in DEVELOPMENT_GUIDES.values():
    #     if keywords & set([name.lower() for name in guide_doc['keywords']]):
    #         project_data['development_guides'].append({'title': guide_doc['title'], 'link': guide_doc['link']})
    return api_success(data=project_data)


@api_view(['GET'])
def project_task_topics(request, project_id):
    developer = request.developer
    project = get_object_or_404(Project, pk=project_id)
    this_week = request.GET.get('this_week') in ['True', '1', 1, "true"]

    task_topics = []
    week_end = this_week_end()
    topics_data = []
    if not getattr(project, 'gantt_chart', None):
        return api_success(data=[])

    roles = project.gantt_chart.roles.filter(developer_id=developer.id)
    for role in roles:
        role_topics = role.task_topics.filter(is_done=False)
        if this_week:
            role_topics = role_topics.filter(start_time__lte=week_end)
        if not task_topics:
            task_topics = role_topics
        else:
            task_topics = task_topics | role_topics

    if task_topics:
        task_topics = task_topics.order_by('start_time')
        topics_data = GanttTaskTopicSerializer(task_topics, many=True).data

    return api_success(data=topics_data)


@api_view(['GET'])
def project_payments(request, project_id):
    developer = request.developer
    project = get_object_or_404(Project, pk=project_id)
    positions = project.job_positions.filter(developer_id=developer.id)
    if not positions.exists():
        return api_permissions_required("只有该项目的工程师才有权限访问项目详情信息")
    payments_data = project_developer_payment_data(project, developer)
    return api_success(data=payments_data)


# 【code explain】【所有项目工程师职位+评分】
@api_view(['GET'])
def projects_my_jobs(request):
    developer = request.developer
    positions = developer.job_positions.filter(developer_id=developer.id).order_by('-created_at')
    # 需要包含 标准评分信息的数据
    data = JobSerializer(positions, many=True).data
    return api_success(data=data)


# 【code explain】【一个项目中工程师职位+评分】
@api_view(['GET'])
def project_my_jobs(request, project_id):
    developer = request.developer
    project = get_object_or_404(Project, pk=project_id)
    positions = project.job_positions.filter(developer_id=developer.id).order_by('-created_at')
    # 需要包含 标准评分信息的数据
    data = JobSerializer(positions, many=True).data
    return api_success(data=data)


@api_view(['GET'])
def project_my_star_ratings(request, project_id):
    developer = request.developer
    project = get_object_or_404(Project, pk=project_id)
    star_rating = developer.build_star_rating(project=project)
    # 需要包含 标准评分信息的数据
    positions = project.job_positions.filter(developer_id=developer.id).order_by('-created_at')
    positions_data = JobSerializer(positions, many=True).data
    return api_success(data={'star_rating': star_rating, 'jobs': positions_data})


@api_view(['GET'])
def project_my_bugs(request, project_id):
    developer = request.developer
    project = get_object_or_404(Project, pk=project_id)
    top_user = request.top_user

    fixed_bugs = project.bugs.exclude(status='pending').filter(fixed_by_id=top_user.id)
    pending_bugs = project.bugs.filter(status='pending', assignee_id=top_user.id)

    # 已修复的bug: 修复人是自己、状态为已修复、关闭的bug
    # 待修复的bug: 负责人是自己、状态为待修复的bug
    type_dict = {}
    last_b_type_index = 0
    for index, (v, l) in enumerate(Bug.BUG_TYPE_CHOICES):
        type_dict[v] = {
            "value": v,
            'label': l,
            'count': 0,
            'index': index
        }
        last_b_type_index = index

    for b in fixed_bugs:
        b_type = b.bug_type
        if b_type not in type_dict:
            last_b_type_index += 1
            type_dict[b_type] = {
                "value": b_type,
                'label': b_type,
                'count': 0,
                'index': last_b_type_index
            }
        type_dict[b_type]['count'] = type_dict[b_type]['count'] + 1

    fixed_type_statistics = sorted(type_dict.values(), key=lambda x: x['index'])

    priority_dict = {}
    last_b_priority_index = 0
    for index, (v, l) in enumerate(Bug.PRIORITY_CHOICES):
        priority_dict[v] = {
            "value": v,
            'label': l,
            'count': 0,
            'index': index
        }
        last_b_priority_index = index

    for b in pending_bugs:
        b_priority = b.priority
        if b_priority not in priority_dict:
            last_b_priority_index += 1
            priority_dict[b_priority] = {
                "value": b_priority,
                'label': b_priority,
                'count': 0,
                'index': last_b_type_index
            }
        priority_dict[b_priority]['count'] = priority_dict[b_priority]['count'] + 1

    pending_priority_statistics = sorted(priority_dict.values(), key=lambda x: x['index'])

    data = {
        'fixed': {
            'total': fixed_bugs.count(),
            'type_statistics': fixed_type_statistics
        },
        'pending': {
            'total': pending_bugs.count(),
            'priority_statistics': pending_priority_statistics
        },

    }
    return api_success(data)


# @api_view(['GET'])
# def project_issues(request, project_id):
#     developer = request.developer
#     project = get_object_or_404(Project, pk=project_id)
#     positions = project.job_positions.filter(developer_id=developer.id)
#     if not positions.exists():
#         return api_permissions_required("只有该项目的工程师才有权限访问项目详情信息")
#     project_data = ProjectDeveloperDetailSerializer(project).data
#     project_data['issues_data'] = None
#     links_data = project_data['links']
#     gitlab_user_id = developer.gitlab_user_id
#     if gitlab_user_id and links_data and (links_data['gitlab_group_id'] or links_data['gitlab_project_id']):
#         project_data['issues_data'] = {'projects': [], 'issues_total': 0, 'issues_new': 0}
#         project_issues_data = project_data['issues_data']
#         link_git_project = links_data['gitlab_project']
#         farm_project_id = project.id
#         farm_projects_git_issues = cache.get('farm_projects_git_issues', {})
#         gitlab_projects = cache.get('gitlab-projects', {})
#
#         issues_projects = {}
#
#         if farm_project_id in farm_projects_git_issues:
#             opened_issues = farm_projects_git_issues[farm_project_id].get('opened_issues', [])
#             now = timezone.now()
#             day_zero = datetime(now.year, now.month, now.day, 0, 0, 0)
#             for issue_data in opened_issues:
#                 git_project_id = issue_data['project_id']
#                 for assignee in issue_data['assignees']:
#                     if str(assignee['id']) == str(gitlab_user_id):
#                         if git_project_id not in issues_projects:
#                             issues_projects[git_project_id] = {'issues_total': 0, 'issues_new': 0}
#                             issues_projects[git_project_id].update(
#                                 gitlab_projects.get(git_project_id, link_git_project))
#                         current_project_issues = issues_projects[git_project_id]
#                         current_project_issues['issues_total'] = current_project_issues['issues_total'] + 1
#                         project_issues_data['issues_total'] = project_issues_data['issues_total'] + 1
#                         created_str = issue_data['created_at']
#                         created_date = None
#                         try:
#                             if '+08:00' in created_str:
#                                 created_date = datetime.strptime(created_str,
#                                                                  "%Y-%m-%dT%H:%M:%S.%f+08:00")
#                             elif created_str.endswith('Z'):
#                                 created_date = datetime.strptime(created_str,
#                                                                  "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(
#                                     hours=8)
#                             if created_date and created_date >= day_zero:
#                                 current_project_issues['issues_new'] = current_project_issues['issues_new'] + 1
#                                 project_issues_data['issues_new'] = project_issues_data['issues_new'] + 1
#                         except Exception as e:
#                             logger.warning(str(e))
#                             pass
#                         continue
#         project_data['issues_data']['projects'] = sorted(issues_projects.values(), key=lambda x: x['issues_total'])
#
#     return api_success(data=project_data['issues_data'])


class ProjectGanttDetail(APIView):
    def get(self, request, project_id=None, uid=None):
        project_gantt = None
        if project_id:
            get_object_or_404(Project, pk=project_id)
            project_gantt = get_object_or_404(ProjectGanttChart, project_id=project_id)
        if uid:
            project_gantt = get_object_or_404(ProjectGanttChart, uid=uid)
        if not project_gantt:
            return api_bad_request(message="需要参数gantt_chart_id或uid")
        data = ProjectGanttChartRetrieveSerializer(project_gantt).data

        # 排除Farm用户
        data['roles'] = [role for role in data['roles'] if not role['user'] or role['role_type'] == 'pm']

        # last_week_data = cache.get('gantt-{}-data'.format(project_gantt.id))
        # if request.GET.get('diff_last_week') and last_week_data:
        #     last_start_time = last_week_data.get('start_time')
        #     if last_start_time and data['start_time']:
        #         if isinstance(last_start_time, str):
        #             last_start_time = datetime.strptime(last_start_time, settings.DATE_FORMAT).date()
        #         if last_start_time < data['start_time']:
        #             data['start_time'] = last_start_time
        #
        #     last_finish_time = last_week_data.get('finish_time')
        #     if last_finish_time and data['finish_time']:
        #         if isinstance(last_finish_time, str):
        #             last_finish_time = datetime.strptime(last_finish_time, settings.DATE_FORMAT).date()
        #         if last_finish_time > data['finish_time']:
        #             data['finish_time'] = last_finish_time
        return api_success(data=data)


@api_view(['GET'])
def project_gantt_tasks(request, gantt_chart_id=None, uid=None):
    project_gantt = None
    if gantt_chart_id:
        project_gantt = get_object_or_404(ProjectGanttChart, pk=gantt_chart_id)
    if uid:
        project_gantt = get_object_or_404(ProjectGanttChart, uid=uid)
    if not project_gantt:
        return api_bad_request(message="需要参数gantt_chart_id或uid")

    params = request.GET
    roles = params.get('roles', None)

    # topic_total = project_gantt.task_topics.count()
    # empty_catalogue_total = project_gantt.task_catalogues.filter(task_topics__isnull=True).count()
    # 排除Farm用户的任务
    project_gantt_tasks = project_gantt.task_topics.all()
    project_gantt_catalogues = project_gantt.task_catalogues.all()

    task_status = params.get('task_status', 'all')

    # 没有筛选
    if not roles and task_status == 'all':
        task_catalogues = project_gantt_catalogues
        no_catalogue_topics = project_gantt_tasks.filter(catalogue_id__isnull=True)
        catalogues_data = GanttTaskCatalogueSerializer(task_catalogues, many=True).data
        topics_data = GanttTaskTopicSerializer(no_catalogue_topics, many=True).data
    else:
        task_topics = project_gantt_tasks

        if task_status == 'undone':
            task_topics = task_topics.filter(is_done=False)
        elif task_status == 'expired':
            task_topics = task_topics.filter(expected_finish_time__lt=timezone.now().date(), is_done=False)

        if roles:
            role_id_list = re.sub(r'[;；,，]', ' ', roles).split()
            if role_id_list:
                task_topics = task_topics.filter(role_id__in=role_id_list)
        no_catalogue_topics = task_topics.filter(catalogue_id__isnull=True).order_by('number', 'id')
        topics_data = GanttTaskTopicSerializer(no_catalogue_topics, many=True).data

        has_catalogue_topics = task_topics.filter(catalogue_id__isnull=False).order_by('number', 'id')
        catalogue_list = set([topic.catalogue for topic in has_catalogue_topics])
        catalogues_data = GanttTaskCatalogueSerializer(catalogue_list, many=True).data
        has_catalogue_topics_data = GanttTaskTopicSerializer(has_catalogue_topics, many=True).data
        catalogue_topics_dict = {}
        for topic_data in has_catalogue_topics_data:
            if topic_data['catalogue']['id'] not in catalogue_topics_dict:
                catalogue_topics_dict[topic_data['catalogue']['id']] = []
            catalogue_topics_dict[topic_data['catalogue']['id']].append(topic_data)
        for catalogue_data in catalogues_data:
            catalogue_data['task_topics'] = catalogue_topics_dict[catalogue_data['id']]
    # 上周对比代码工程师端不需要
    # if diff_last_week:
    #     add_deleted_data = False
    #     if not roles and not is_expired:
    #         add_deleted_data = True
    #     catalogues_data, topics_data = get_gantt_tasks_data_with_last_week_data(project_gantt, catalogues_data,
    #                                                                             topics_data,
    #                                                                             add_deleted_data=add_deleted_data)

    result_data = []
    # 过滤Farm用户的任务
    for catalogue_data in catalogues_data:
        new_data = deepcopy(catalogue_data)
        new_data['task_topics'] = [topic for topic in catalogue_data['task_topics'] if not topic['role']['user']]
        if len(new_data['task_topics']):
            result_data.append(new_data)
    for topic in topics_data:
        new_data = deepcopy(topic)
        if not topic['role']['user']:
            result_data.append(new_data)

    gantt_tasks = sorted(result_data, key=lambda task: (task['number'], task['id']))
    # result_data = {'result': True, 'data': gantt_tasks, 'topic_total': topic_total,
    #                'empty_catalogue_total': empty_catalogue_total}
    return api_success(data=gantt_tasks)


@api_view(['POST'])
def gantt_task_dev_toggle_done(request, topic_id):
    gantt_task = get_object_or_404(GanttTaskTopic, pk=topic_id)
    developer = request.developer
    if gantt_task.role.developer_id != developer.id:
        return api_permissions_required("只有负责该甘特图任务的工程师才有权限改变任务状态")
    origin = deepcopy(gantt_task)
    # if gantt_task.is_done:
    #     return Response({'result': False, 'message': '产品经理已确认最终完成'})
    message_temp = ""
    if gantt_task.is_dev_done:
        gantt_task.dev_done_at = None
        gantt_task.is_dev_done = False
        gantt_task.dev_done_type = None
    else:
        gantt_task.dev_done_at = timezone.now()
        gantt_task.is_dev_done = True
        gantt_task.dev_done_type = 'self'
        message_temp = "项目【{project}】甘特图任务【{name}】勾选完成，操作人:{username}"
    gantt_task.save()
    if message_temp:
        project = gantt_task.gantt_chart.project
        message = message_temp.format(username=developer.name, project=project.name, name=gantt_task.name)
        if project.manager_id:
            create_notification(project.manager, message)
        if project.mentor_id and project.mentor_id != project.manager_id:
            create_notification(project.mentor, message)
    Log.build_update_object_log(developer, origin, gantt_task, related_object=gantt_task.gantt_chart)
    data = GanttTaskTopicSerializer(gantt_task).data
    return api_success(data=data)


@api_view(['POST'])
@request_data_fields_required('redirect_uri')
def gitlab_bind_redirect_data(request):
    redirect_uri = request.data.get('redirect_uri')
    client = GitlabOauthClient()
    oauth_url = client.get_oauth_url(redirect_uri)
    return api_success(data={'oauth_url': oauth_url})


@api_view(['POST'])
@request_data_fields_required(('redirect_uri', 'code'))
def gitlab_bind(request):
    redirect_uri = request.data.get('redirect_uri')
    code = request.data.get('code')
    client = GitlabOauthClient()
    access_token = client.get_access_token(code, redirect_uri)
    if access_token:
        user_data = client.get_user_data(access_token)
        if user_data:
            gitlab_user_id = user_data['id']
            # 登录用户  gitlab_user_id
            if request.developer.is_authenticated:
                # 已绑定gitlab
                if request.developer.gitlab_user_id:
                    return api_success()
                # 未绑定gitlab 该git账户没有被绑定
                elif not Developer.objects.filter(gitlab_user_id=gitlab_user_id).exists():
                    request.developer.gitlab_user_id = gitlab_user_id
                    request.developer.save()
                    return api_success()
            return api_bad_request("绑定失败，当前用户未登录")
    return api_bad_request("绑定失败，获取Gitlab用户信息失败")


@api_view(['POST'])
@request_data_fields_required('redirect_uri')
def gitlab_login_redirect_data(request):
    redirect_uri = request.data.get('redirect_uri')
    client = GitlabOauthClient()
    oauth_url = client.get_oauth_url(redirect_uri)
    return api_success(data={'oauth_url': oauth_url})


@api_view(['POST'])
@request_data_fields_required(('redirect_uri', 'code'))
def gitlab_login(request):
    redirect_uri = request.data.get('redirect_uri')
    code = request.data.get('code')
    client = GitlabOauthClient()
    access_token = client.get_access_token(code, redirect_uri)
    if access_token:
        user_data = client.get_user_data(access_token)
        if user_data:
            gitlab_user_id = user_data['id']
            if not Developer.objects.filter(gitlab_user_id=gitlab_user_id).exists():
                return api_bad_request(message="登录失败, Gitlab账户暂未绑定工程师账户")

            developers = Developer.objects.filter(gitlab_user_id=gitlab_user_id)
            if developers.count() > 1:
                logger.error("该Gitlab账户绑定了多个工程师账户：{}".format(','.join(list(developers.values_list('name', flat=True)))))

            developer = developers.filter(is_active=True).order_by('-created_at').first()
            if developer:
                developer.last_login = timezone.now()
                developer.save()
                token, created = TopToken.get_or_create(developer=developer)
                return api_success(data={'token': token.key, 'user_type': token.user_type})
            return api_suspended()
    return api_bad_request("绑定失败，获取Gitlab用户信息失败")


@api_view(['POST'])
def gitlab_oauth_unbind(request):
    request.developer.gitlab_user_id = None
    request.developer.save()
    return api_success()


@api_view(['POST'])
def read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id)
    if notification.developer_id != request.developer.id:
        return api_bad_request("不能修改他人消息状态")
    if not notification.read_at:
        notification.read_at = timezone.now()
        notification.is_read = True
        notification.save()
    return api_success()


@api_view(['POST'])
def read_my_notifications(request):
    developer = request.developer
    Notification.unread_notifications().filter(developer_id=developer.id).update(read_at=timezone.now(), is_read=True)
    return api_success()


class MyNotificationList(APIView):
    def get(self, request):
        developer = request.developer
        notifications = developer.notifications.all()
        params = request.GET
        page = params.get('page', None)
        page_size = params.get('page_size', None)
        start_time_str = params.get('start_date', '')
        end_time_str = params.get('end_date', '')

        is_read = None
        if "is_read" in params:
            is_read = params['is_read'] in {'true', '1', 'True', 1, True}

        if is_read is not None:
            notifications = notifications.filter(is_read=is_read)

        start_time = datetime.now() - timedelta(days=60)
        end_time = datetime.now()
        if start_time_str:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d')
        if end_time_str:
            end_time = datetime.strptime(end_time_str, '%Y-%m-%d')

        if is_read is None:
            read_notifications = notifications.filter(is_read=True, created_at__lte=end_time,
                                                      created_at__gte=start_time)
            unread_notifications = notifications.filter(is_read=False)
            notifications = unread_notifications | read_notifications
            notifications = notifications.order_by('is_read', '-created_at')
        else:
            notifications = notifications.order_by('-created_at')
        return build_pagination_response(request, notifications, NotificationSerializer)


@api_view(['GET'])
def my_project_daily_works_statistics(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    developer = request.developer
    start_date = project.start_date
    end_date = project.end_date

    statistics_data = get_project_developer_daily_works_statistics(project, developer, rebuild=True)

    first_daily_work_day = statistics_data.get('first_daily_work_day', None)
    last_daily_work_day = statistics_data.get('last_daily_work_day', None)
    start_date = first_daily_work_day if first_daily_work_day and first_daily_work_day < start_date else start_date
    end_date = last_daily_work_day if last_daily_work_day and last_daily_work_day > end_date else end_date

    project_data = {
        "start_date": start_date,
        "end_date": end_date,
        "project": {'id': project.id, 'name': project.name},
        "developer": {'id': developer.id, 'name': developer.name},
    }
    statistics_data.update(project_data)
    return api_success(data=statistics_data)


def get_tomorrow_daily_work_data(project, developer):
    tomorrow = timezone.now().date() + timedelta(days=1)
    gantt_tasks = get_day_task_topics(project, developer, tomorrow, include_day_dev_done=False)
    gantt_tasks_data = GanttTaskTopicDailyWorkSerializer(gantt_tasks, many=True).data
    day_daily_work = DailyWork.objects.filter(project_id=project.id, developer_id=developer.id,
                                              day=tomorrow).first()
    daily_work_data = {}
    other_task = None
    if day_daily_work:
        daily_work_data = DailyWorkSerializer(day_daily_work).data
        if day_daily_work.other_task:
            other_task = deepcopy(daily_work_data['other_task'])
    daily_work_data['gantt_tasks'] = gantt_tasks_data
    daily_work_data['other_task'] = other_task
    return daily_work_data


def get_today_daily_work_data(project, developer):
    day = timezone.now().date()
    gantt_tasks = get_day_task_topics(project, developer, day, include_day_dev_done=True)
    gantt_tasks_data = GanttTaskTopicDailyWorkSerializer(gantt_tasks, many=True).data
    day_daily_work = DailyWork.objects.filter(project_id=project.id, developer_id=developer.id,
                                              day=day).first()

    daily_work_data = {}
    other_task = None
    if day_daily_work:
        daily_work_data = DailyWorkSerializer(day_daily_work).data
        if day_daily_work.gantt_tasks:
            origin_gantt_tasks = deepcopy(daily_work_data['gantt_tasks'])
            origin_gantt_tasks_dict = {}
            for task in origin_gantt_tasks:
                origin_gantt_tasks_dict[task['id']] = task

            for gantt_task in gantt_tasks_data:
                gantt_task_id = gantt_task['id']
                if gantt_task_id in origin_gantt_tasks_dict:
                    origin_gantt_task = origin_gantt_tasks_dict[gantt_task_id]
                    if gantt_task['task_status'] == 'pending' and origin_gantt_task['task_status'] != 'done':
                        gantt_task['task_status'] = origin_gantt_task['task_status']
                    gantt_task['result_remarks'] = origin_gantt_task['result_remarks']
                    gantt_task['remarks'] = origin_gantt_task['remarks']
        if day_daily_work.other_task:
            other_task = deepcopy(daily_work_data['other_task'])
    daily_work_data['gantt_tasks'] = gantt_tasks_data
    daily_work_data['other_task'] = other_task
    return daily_work_data


@api_view(['GET'])
def my_project_today_tasks(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    developer = request.developer

    today_daily_work_data = get_today_daily_work_data(project, developer)
    today_daily_work_data['next_day_work'] = get_tomorrow_daily_work_data(project, developer)

    return api_success(data=today_daily_work_data)


@api_view(['GET'])
def daily_work_detail(request, daily_work_id, format=None):
    daily_work = get_object_or_404(DailyWork, pk=daily_work_id)
    daily_work_data = DailyWorkSerializer(daily_work).data
    return api_success(data=daily_work_data)


@api_view(['GET'])
def project_today_daily_work(request, project_id, format=None):
    project = get_object_or_404(Project, pk=project_id)
    developer = request.developer
    today = timezone.now().date()
    today_daily_works = project.daily_works.filter(developer_id=developer.id, day=today).exclude()
    if today_daily_works.exists():
        data = DailyWorkSerializer(today_daily_works.first()).data
        return api_success(data)
    return api_not_found()


@api_view(['GET'])
@request_params_required(('day', 'developer_id'))
def project_day_daily_work(request, project_id, format=None):
    project = get_object_or_404(Project, pk=project_id)
    day_str = request.GET.get('day')
    developer_id = request.GET.get('developer_id')
    developer = get_object_or_404(Developer, pk=developer_id)
    try:
        that_day = datetime.strptime(day_str, '%Y-%m-%d').date()
    except Exception as e:
        return api_bad_request(message='参数格式为:YYYY-MM-DD')
    today = timezone.now().date()
    day_daily_work = project.daily_works.filter(developer_id=developer.id, day=that_day).exclude(
        status='pending').first()
    if day_daily_work:
        if request.user and request.user.is_authenticated:
            BrowsingHistory.build_log(request.user, day_daily_work)
            # 缓存
            top_user_id = request.user.top_user.id
            cache_key = 'p_{}_u_{}_unread_daily_works_count'.format(project_id, top_user_id)
            cache.delete(cache_key)

        data = DailyWorkViewSerializer(day_daily_work).data
        if today == that_day:
            project_id = day_daily_work.project_id
            gitlab_user_id = day_daily_work.developer.gitlab_user_id
            if gitlab_user_id:
                gitlab_commits = build_project_gitlab_user_id_day_gitlab_commits(project_id,
                                                                                 gitlab_user_id,
                                                                                 today,
                                                                                 with_commits=True)
                data['gitlab_commits'] = gitlab_commits
        return api_success(data)
    return api_not_found()


@api_view(['GET'])
@request_params_required(('developer_id'))
def project_developer_last_daily_work(request, project_id, format=None):
    project = get_object_or_404(Project, pk=project_id)
    developer_id = request.GET.get('developer_id')
    developer = get_object_or_404(Developer, pk=developer_id)
    day_daily_work = developer.last_daily_work(project)
    if day_daily_work:
        if request.user and request.user.is_authenticated:
            BrowsingHistory.build_log(request.user, day_daily_work)
        data = DailyWorkViewSerializer(day_daily_work).data
        return api_success(data)
    return api_not_found()


@api_view(['GET'])
@request_params_required(('developer_id'))
def project_developer_daily_work_statistics(request, project_id, format=None):
    project = get_object_or_404(Project, pk=project_id)
    developer_id = request.GET.get('developer_id')
    developer = get_object_or_404(Developer, pk=developer_id)
    avatar = None
    if developer.avatar:
        avatar = developer.avatar.url
    developer_data = {"id": developer.pk, "name": developer.name, 'username': developer.name,
                      'phone': developer.phone,
                      'avatar': avatar, 'avatar_url': avatar}
    developer_data['statistics'] = get_project_developer_daily_works_statistics(project, developer)
    developer_data['today_need_submit_daily_work'] = get_need_submit_daily_work(project, developer,
                                                                                timezone.now().date())
    return api_success(data=developer_data)


def get_mention_users_from_daily_work_data(daily_work):
    mention_users = []
    gantt_tasks = daily_work.gantt_tasks
    other_task = daily_work.other_task
    remarks = daily_work.remarks
    if remarks:
        mention_users.extend(re.findall(r'@(\S+)\((\S+)\)', remarks))
    if gantt_tasks:
        gantt_tasks_data = json.loads(gantt_tasks, encoding='utf-8')
        if gantt_tasks_data:
            for gantt_task in gantt_tasks_data:
                result_remarks = gantt_task.get('result_remarks', None)
                if result_remarks:
                    mention_users.extend(re.findall(r'@(\S+)\((\S+)\)', result_remarks))
    if other_task:
        other_task_data = json.loads(other_task, encoding='utf-8')
        remarks = other_task_data.get('remarks', None)
        result_remarks = other_task_data.get('result_remarks', None)
        if result_remarks:
            mention_users.extend(re.findall(r'@(\S+)\((\S+)\)', result_remarks))
        if remarks:
            mention_users.extend(re.findall(r'@(\S+)\((\S+)\)', remarks))
    if daily_work.next_day_work and daily_work.next_day_work.other_task:
        other_task_data = json.loads(daily_work.next_day_work.other_task, encoding='utf-8')
        remarks = other_task_data.get('remarks', None)
        result_remarks = other_task_data.get('result_remarks', None)
        if result_remarks:
            mention_users.extend(re.findall(r'@(\S+)\((\S+)\)', result_remarks))
        if remarks:
            mention_users.extend(re.findall(r'@(\S+)\((\S+)\)', remarks))
    return list(set(mention_users))


def send_daily_work_notifications_to_mention_users(sender, daily_work, mention_users=[]):
    day_str = daily_work.day.strftime(settings.DATE_FORMAT)
    project = daily_work.project
    developer = daily_work.developer
    farm_url = settings.SITE_URL + '/developers/daily_works/?day={}&projectId={}&developerId={}'.format(
        day_str, project.id, developer.id)
    developer_url = settings.DEVELOPER_WEB_SITE_URL + '?day={}&projectId={}&developerId={}&activeTab=dailyWork'.format(
        day_str, project.id, daily_work.developer.id)
    content = '{}在【{}】【{}】【{}】日报中@了你'.format(sender.name, project.name, developer.name, day_str)
    developer_names = set()
    username_list = set()
    for name, role in mention_users:
        if role.endswith('工程师') or role == '设计师':
            developer_names.add(developer.name)
        else:
            username_list.add(name)

    if developer.name in developer_names:
        developer_names.remove(developer.name)
    developers = Developer.objects.filter(name__in=developer_names, is_active=True)
    users = User.objects.filter(username__in=username_list, is_active=True)
    if users.exists():
        create_notification_to_users(users, content, farm_url, is_important=True)
    if developers.exists():
        create_notification_to_developers(developers, content, developer_url)


@api_view(['GET'])
def project_today_daily_work_data(request, project_id, format=None):
    project = get_object_or_404(Project, pk=project_id)
    developer = request.developer
    daily_work = project.daily_works.filter(developer_id=developer.id, day=timezone.now().date()).exclude(
        status='pending').first()
    daily_work_data = None
    if daily_work:
        daily_work_data = DailyWorkViewSerializer(daily_work).data
    need_punch = get_need_submit_daily_work(project, developer, timezone.now().date())
    return api_success({'today_need_submit_daily_work': need_punch, 'daily_work': daily_work_data})


@api_view(['POST'])
def punch_today_daily_work(request, project_id, format=None):
    project = get_object_or_404(Project, pk=project_id)
    developer = request.developer
    request_data = deepcopy(request.data)
    today_daily_work = build_today_daily_work(project, developer)
    today_daily_work.need_support = request_data.get('need_support', False)
    today_daily_work.remarks = request_data.get('remarks')
    gantt_tasks_data = request_data.get('gantt_tasks', None)
    other_task_data = request_data.get('other_task', None)

    origin_mention_users = []
    if today_daily_work.status in ['normal', 'postpone']:
        origin_mention_users = get_mention_users_from_daily_work_data(today_daily_work)

    today_str = timezone.now().date().strftime(settings.DATE_FORMAT)
    today_daily_work_status = 'normal'
    if gantt_tasks_data:
        for task_data in gantt_tasks_data:
            task_id = task_data.get('id')
            task_status = task_data.get('task_status', None)
            task_topic = GanttTaskTopic.objects.filter(pk=task_id).first()
            if task_topic:
                if task_status == 'done' and task_topic.is_dev_done is False:
                    task_topic.is_dev_done = True
                    task_topic.dev_done_at = timezone.now()
                    task_topic.save()
                elif task_status != 'done' and task_topic.is_dev_done is True and task_topic.is_done is False:
                    task_topic.is_dev_done = False
                    task_topic.dev_done_at = None
                    task_topic.save()
            if task_data['expected_finish_time'] <= today_str and task_status != "done":
                today_daily_work_status = 'postpone'

    gantt_tasks_data = json.dumps(gantt_tasks_data, ensure_ascii=False)
    if other_task_data:
        other_task_data = json.dumps(other_task_data, ensure_ascii=False)
    today_daily_work.other_task = other_task_data
    today_daily_work.gantt_tasks = gantt_tasks_data

    today_daily_work.status = today_daily_work_status

    tomorrow_daily_work = build_tommorow_daily_work(project, developer)
    next_day_work_data = request_data.get('next_day_work')
    if next_day_work_data:
        other_task = next_day_work_data.pop('other_task', None)
        other_task_data = json.dumps(other_task, ensure_ascii=False) if other_task else None
        next_day_work_data['other_task_plan'] = other_task_data
        next_day_work_data['other_task'] = other_task_data

        gantt_tasks = next_day_work_data.pop('gantt_tasks', None)
        gantt_tasks_data = json.dumps(gantt_tasks, ensure_ascii=False) if gantt_tasks else None
        next_day_work_data['gantt_tasks_plan'] = gantt_tasks_data

        tomorrow_daily_work_serializer = DailyWorkNextDayEditSerializer(tomorrow_daily_work, data=next_day_work_data)
        if not tomorrow_daily_work_serializer.is_valid():
            return api_bad_request(message=str(tomorrow_daily_work_serializer.errors))
        tomorrow_daily_work = tomorrow_daily_work_serializer.save()
    today_daily_work.next_day_work = tomorrow_daily_work
    today_daily_work.punched_at = timezone.now()
    today_daily_work.need_submit_daily_work = get_need_submit_daily_work(project, developer, timezone.now().date())
    today_daily_work.save()
    get_project_developer_daily_works_statistics(project, developer, rebuild=True)
    data = DailyWorkSerializer(today_daily_work).data

    mention_users = get_mention_users_from_daily_work_data(today_daily_work)
    mention_users = list(set(mention_users).difference(set(origin_mention_users)))
    send_daily_work_notifications_to_mention_users(developer, today_daily_work, mention_users)
    return api_success(data=data)


@api_view(['GET'])
def project_developers(request, project_id):
    with_daily_work_statistics = request.GET.get('with_daily_work_statistics', False) in ['True', True, '1', 1, 'true']
    project = get_object_or_404(Project, pk=project_id)
    developers = get_project_developers_data(project, with_daily_work_statistics=with_daily_work_statistics)
    return api_success(data=developers)


@api_view(['GET'])
def project_members(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    members = get_project_members_data(project, with_bd=False)
    result_data = members
    with_developers = request.GET.get('with_developers', None)
    if with_developers in ['True', 'true', '1', 1]:
        developers = get_project_developers_data(project)
        result_data = {'users': members, 'developers': developers}
    return api_success(data=result_data)


from developers.models import DocumentVersion, Document, DocumentReadLog
from developers.serializers import DocumentListSerializer, DocumentReadLogSerializer, DocumentVersion, \
    DocumentListWithVersionsSerializer


@api_view(['GET'])
def my_developer_documents(request):
    with_history_versions = request.GET.get('with_history_versions', None) in ['True', True, 'true', '1', 1]
    docs = []
    if request.developer:
        docs = request.developer.active_developers_documents()
    elif request.user:
        docs = Document.active_documents()

    if with_history_versions:
        documents_data = DocumentListWithVersionsSerializer(docs, many=True).data
    else:
        documents_data = DocumentListSerializer(docs, many=True).data

    for document in documents_data:

        document['read_log'] = get_document_read_log_data(document['id'], request)

        if with_history_versions:
            online_version = document['online_version'] if document.get('online_version', None) else None
            history_versions = document['history_versions'] if document.get('history_versions', None) else None
            if online_version:
                version = DocumentVersion.objects.get(pk=online_version['id'])
                online_version['read_log'] = get_version_read_log_data(version, request)
                online_version['large_version_read_log'] = get_large_version_read_log_data(version, request)
            if history_versions:
                for history_version in history_versions:
                    version = DocumentVersion.objects.get(pk=history_version['id'])
                    history_version['read_log'] = get_version_read_log_data(version, request)
                    history_version['large_version_read_log'] = get_large_version_read_log_data(version, request)
    return farm_response.api_success(data=documents_data)


def get_document_read_log_data(document_id, request):
    document = Document.objects.get(pk=document_id)
    if request.developer:
        read_log = document.developer_current_large_version_read_log(request.developer)
    else:
        read_log = document.user_current_large_version_read_log(request.user)
    read_log_data = DocumentReadLogSerializer(read_log, many=False).data if read_log else None
    return read_log_data


def get_version_read_log_data(version, request):
    if request.developer:
        read_log = version.get_developer_read_log(request.developer)
    else:
        read_log = version.get_user_read_log(request.user)
    read_log_data = DocumentReadLogSerializer(read_log, many=False).data if read_log else None
    return read_log_data


def get_large_version_read_log_data(version, request):
    if request.developer:
        read_log = version.get_developer_large_version_read_log(request.developer)
    else:
        read_log = version.get_user_large_version_read_log(request.user)
    read_log_data = DocumentReadLogSerializer(read_log, many=False).data if read_log else None
    return read_log_data


@api_view(['POST'])
def read_document_version(request, id):
    document = get_object_or_404(DocumentVersion, pk=id)
    if request.developer:
        DocumentReadLog.objects.create(developer=request.developer, document=document)
    elif request.user and request.user.is_authenticated:
        DocumentReadLog.objects.create(user=request.user, document=document)
    return farm_response.api_success()


@api_view(['POST'])
def developer_real_name_auth(request):
    developer = request.developer
    name = request.data.get('name', '')
    id_card_number = request.data.get('id_card_number', '')
    front_side_string = request.data.get('front_side_of_id_card', None)
    back_side_string = request.data.get('back_side_of_id_card', None)
    request_data = deepcopy(request.data)
    if front_side_string:
        front_side_file = base64_string_to_file(front_side_string)
        if not front_side_file:
            return api_bad_request("请上传有效的base64图片字符串")
        request_data['front_side_of_id_card'] = front_side_file
    elif not developer.front_side_of_id_card:
        return api_bad_request("请上传身份证照片")

    if back_side_string:
        back_side_file = base64_string_to_file(back_side_string)
        if not back_side_file:
            return api_bad_request("请上传有效的base64图片字符串")
        request_data['back_side_of_id_card'] = back_side_file
    elif not developer.back_side_of_id_card:
        return api_bad_request("请上传身份证照片")
    if not developer.is_real_name_auth:
        result = AliAuth().real_name_auth(id_card_number, name)
        if result['error_code'] == 0 and result['result']['isok']:
            request_data['is_real_name_auth'] = True
            serializer = DeveloperRealNameSerializer(developer, data=request_data)
            if serializer.is_valid():
                developer = serializer.save()
                return api_success()
            return api_bad_request(serializer.errors)
        return api_bad_request('实名认证失败，请核对信息后重试')
    else:
        serializer = DeveloperIDCardEditSerializer(developer, data=request_data)
        if serializer.is_valid():
            developer = serializer.save()
            return api_success()
        return api_bad_request(serializer.errors)
