import uuid
import random
import string
from datetime import timedelta, datetime
import hashlib
import calendar

from django.utils import six
from django.contrib.auth.models import User
from crum import get_current_request

from farmbase.models import FunctionPermission

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def get_phone_verification_code():
    return ''.join(random.choice(string.digits) for _ in range(6))


def base62_encode(num, alphabet=ALPHABET):
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)


def gen_uuid(length=None):
    uid = base62_encode(uuid.uuid4().int)
    if length:
        uid = uid[:length]
    return uid


def encrypt_string(string):
    d = {}
    for c in (65, 97):
        for i in range(26):
            d[chr(i + c)] = chr((i + 13) % 26 + c)
    return "".join([d.get(c, c) for c in string])


def get_md5(s):
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def seconds_to_format_str(total_seconds):
    total_seconds = int(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    seconds = str(seconds) if seconds >= 10 else '0' + str(seconds)
    minutes = str(minutes) if minutes >= 10 else '0' + str(minutes)
    return "{}:{}:{}".format(hours, minutes, seconds)


def any_true(iterable, num=1):
    i = 0
    for item in iterable:
        if item:
            i += 1
    if i == num:
        return True


def get_url_params(url):
    url_slices = url.split('?')
    data = {}
    if len(url_slices) > 1:
        search = url_slices[1]
        params = search.split('&')
        for param in params:
            param_slices = param.split('=')
            if len(param_slices) == 2:
                key, value = param_slices
                data[key] = value
    return data


def today_zero(day=None):
    now = day or datetime.now()
    return datetime(now.year, now.month, now.day, 0, 0, 0)


def tomorrow_zero(day=None):
    now = day or datetime.now()
    return datetime(now.year, now.month, now.day, 0, 0, 0) + timedelta(days=1)


def tomorrow_date(day=None):
    now_day = day or datetime.now().date()
    return now_day + timedelta(days=1)


def this_week_day(weekday, base_date=None):
    return this_week_start(base_date=base_date) + timedelta(days=weekday)


def next_week_day(weekday, base_date=None):
    return next_week_start(base_date=base_date) + timedelta(days=weekday)


def in_the_same_week(days):
    week_starts = set()
    for day in days:
        start_day = this_week_start(day)
        week_starts.add(start_day)
    if len(week_starts) == 1:
        return True


# 本周第一天和最后一天

def this_week_start(base_date=None):
    today = base_date or datetime.now().date()
    return today - timedelta(days=today.weekday())


def this_week_start_zero():
    day = this_week_start()
    return today_zero(day=day)


def this_week_end(base_date=None):
    today = base_date or datetime.now().date()
    return today + timedelta(days=6 - today.weekday())


# 上周第一天和最后一天
def last_week_start(base_date=None):
    today = base_date or datetime.now().date()
    return today - timedelta(days=today.weekday() + 7)


def last_week_end(base_date=None):
    today = base_date or datetime.now().date()
    return today - timedelta(days=today.weekday() + 1)


# 下周第一天和最后一天
def next_week_start(base_date=None):
    today = base_date or datetime.now().date()
    return today + timedelta(days=7 - today.weekday())


def next_week_end(base_date=None):
    today = base_date or datetime.now().date()
    return today + timedelta(days=13 - today.weekday())


# 本月第一天和最后一天
def this_month_start(this_month=None):
    now = this_month or datetime.now()
    return datetime(now.year, now.month, 1)


def this_month_end(this_month=None):
    now = this_month or datetime.now()
    return datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])


def validate_email(email):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False
    return False


def get_user_by_name(name):
    users = User.objects.filter(username=name)
    if users.exists():
        user = users.first()
        return user


def get_users_by_group(groups):
    if isinstance(groups, six.string_types):
        groups = (groups,)
    else:
        groups = groups
    users = User.objects.filter(is_active=True).filter(groups__name__in=groups).distinct()
    return users


def get_user_data(manager):
    avatar_url = None
    if manager.profile.avatar:
        avatar_url = manager.profile.avatar.url
    avatar_color = manager.profile.avatar_color
    manager_data = {'username': manager.username,
                    "avatar": avatar_url,
                    "phone": manager.profile.phone,
                    "avatar_url": avatar_url, 'avatar_color': avatar_color,
                    'id': manager.id,
                    'is_active': manager.is_active
                    }
    return manager_data


def in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


def in_any_groups(user, group_names):
    if isinstance(group_names, str):
        group_names = [group_names]
    else:
        group_names = group_names
    return user.groups.filter(name__in=group_names).exists()


def get_active_users_by_function_perm(perm, need_superuser=False):
    func_perm = FunctionPermission.objects.filter(codename=perm)
    users = User.objects.none()
    if need_superuser:
        users = User.objects.filter(is_active=True, is_superuser=True)
    if func_perm.exists():
        func_perm = func_perm.first()
        groups = func_perm.groups.all()
        perm_users = func_perm.users.filter(is_active=True)
        if users:
            users = users | perm_users
        else:
            users = perm_users
        for group in groups:
            users = users | group.user_set.filter(is_active=True)
        users = users.distinct()
    return users


def get_protocol_host(request=None):
    if not request:
        request = get_current_request()
    if not request:
        return ''
    protocol = 'https' if request.is_secure() else 'http'
    return protocol + "://" + request.get_host()
