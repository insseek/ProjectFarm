import json
import ssl
import urllib.request
from datetime import datetime, timedelta
from copy import deepcopy
from urllib.parse import urlencode

from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

from farmbase.utils import today_zero, tomorrow_zero
from projects.models import GanttTaskTopic, Project
from developers.models import DailyWork


def get_day_task_topics(project, developer, day, include_day_dev_done=False):
    if not getattr(project, 'gantt_chart', None):
        return GanttTaskTopic.objects.none()

    task_topics = GanttTaskTopic.objects.none()
    roles = project.gantt_chart.roles.filter(developer_id=developer.id)
    for role in roles:
        task_topics = task_topics | role.task_topics.filter(is_done=False)
    undone_tasks = task_topics.filter(is_dev_done=False, start_time__lte=day)
    result_tasks = undone_tasks
    if include_day_dev_done:
        start_time = today_zero(day)
        end_time = tomorrow_zero(day)
        today_dev_done_tasks = task_topics.filter(is_dev_done=True, dev_done_at__lt=end_time,
                                                  dev_done_at__gte=start_time)
        result_tasks = result_tasks | today_dev_done_tasks

    return result_tasks


def get_need_submit_daily_work(project, developer, day):
    if not getattr(project, 'gantt_chart', None):
        return False
    task_topics = GanttTaskTopic.objects.none()
    roles = project.gantt_chart.roles.filter(developer_id=developer.id)
    for role in roles:
        task_topics = task_topics | role.task_topics.filter(is_done=False)

    task_topics = task_topics.filter(gantt_chart__project__done_at__isnull=True)
    undone_tasks = task_topics.filter(is_dev_done=False, start_time__lte=day)
    is_weekend = day.weekday() >= 5

    # 周末  且不是法定节假日调休  且截止时间在今天之后  仅工作日工作的任务不算在必须打卡的任务里
    if is_weekend:
        undone_tasks = undone_tasks.exclude(only_workday=True, expected_finish_time__gt=day)

    # 法定节假日 放假 且截止时间在今天之后的任务  不统计






    start_time = today_zero(day)
    end_time = tomorrow_zero(day)
    today_dev_done_tasks = task_topics.filter(is_dev_done=True, dev_done_at__lt=end_time,
                                              dev_done_at__gte=start_time)
    result_tasks = undone_tasks | today_dev_done_tasks
    need_submit_daily_work = True if len(result_tasks) else False
    return need_submit_daily_work


def build_today_daily_work(project, developer):
    today = timezone.now().date()
    today_daily_work, created = DailyWork.objects.get_or_create(project_id=project.id, developer_id=developer.id,
                                                                day=today)
    return today_daily_work


def build_tommorow_daily_work(project, developer):
    tomorrow = timezone.now().date() + timedelta(days=1)
    tomorrow_daily_work, created = DailyWork.objects.get_or_create(project_id=project.id, developer_id=developer.id,
                                                                   day=tomorrow)
    return tomorrow_daily_work


def get_project_developer_daily_works_statistics(project, developer, rebuild=False):
    cache_key = 'project-{}-developer-{}-daily-works-statistics'.format(project.id, developer.id)
    if not cache.get(cache_key, None) or rebuild:
        build_project_developer_daily_works_statistics(project, developer)
    return cache.get(cache_key)


def build_project_developer_daily_works_statistics(project, developer):
    if not getattr(project, 'gantt_chart', None):
        return
    task_topics = GanttTaskTopic.objects.none()
    roles = project.gantt_chart.roles.filter(developer_id=developer.id)
    for role in roles:
        task_topics = task_topics | role.task_topics.all()

    task_days = set()
    undone_task_days = set()
    for task_topic in task_topics:
        start_time = deepcopy(task_topic.start_time)
        finish_time = task_topic.expected_finish_time
        is_dev_done = task_topic.is_dev_done
        while start_time <= finish_time:
            if task_topic.only_workday and start_time.weekday() >= 5:
                start_time = start_time + timedelta(days=1)
                continue
            day_str = start_time.strftime(settings.DATE_FORMAT)
            task_days.add(day_str)
            if not is_dev_done:
                undone_task_days.add(day_str)
            start_time = start_time + timedelta(days=1)
    task_days = sorted(task_days)
    undone_task_days = sorted(undone_task_days)

    DailyWork.objects.exclude()
    daily_work_days = {"postpone": [], "normal": [], "absence": []}
    daily_works = project.daily_works.filter(developer_id=developer.id).exclude(status='pending').order_by('day')
    first_daily_work_day = None
    last_daily_work_day = None
    if daily_works.exists():
        first_daily_work_day = daily_works.first().day
        last_daily_work_day = daily_works.last().day

    for daily_work in daily_works:
        day_str = daily_work.day.strftime(settings.DATE_FORMAT)
        if daily_work.status not in daily_work_days:
            daily_work_days[daily_work.status] = []
        daily_work_days[daily_work.status].append(day_str)
    daily_work_days_count = 0
    for status_work_days in daily_work_days.values():
        daily_work_days_count += len(status_work_days)
    statistics_data = {
        "task_days": task_days,  # 总任务天数组
        "undone_task_days": undone_task_days,  # 未完成任务天数组
        "daily_work_days": daily_work_days,  # 日报的各种状态dict
        "task_days_count": len(task_days),  # 预计总工时数
        "daily_work_days_count": daily_work_days_count,  # 当前工时数
        "first_daily_work_day": first_daily_work_day,
        "last_daily_work_day": last_daily_work_day
    }
    cache_key = 'project-{}-developer-{}-daily-works-statistics'.format(project.id, developer.id)
    cache.set(cache_key, statistics_data, 60 * 60 * 12)
    return statistics_data


def has_cooperation_with_developer_at_present(user, developer_id):
    ongoing_project = Project.ongoing_projects().filter(manager=user)
    developer_id = int(developer_id)
    for project in ongoing_project:
        if project.job_positions.filter(developer_id=developer_id).exists():
            return True
    return False


class AliAuth(object):
    def __init__(self):
        self.host = 'https://zid.market.alicloudapi.com'
        self.path = '/idcard/VerifyIdcardv2'
        # method = 'GET'
        self.appcode = settings.ALIYUN_REAL_NAME_APPCODE
        self.bodys = {}

    def real_name_auth(self, id_card_number, name):
        params = {
            'cardNo': id_card_number,
            'realName': name
        }
        params = urlencode(params)
        url = self.host + self.path + '?' + params
        req = urllib.request.Request(url)
        req.add_header('Authorization', 'APPCODE ' + self.appcode)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        response = urllib.request.urlopen(req, context=ctx)
        content = json.loads(response.read())
        return content
