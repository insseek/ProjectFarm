import uuid
import random
from copy import deepcopy
import threading
import logging
import string
from datetime import timedelta, datetime
import re
import hashlib
import calendar
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.conf import settings
import requests

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


def url_params_to_str(params={}):
    params_str = ''
    if params:
        params_str = "?"
        for key, value in params.items():
            params_str += "{}={}&".format(key, value)
    return params_str


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


def this_week_friday(base_date=None):
    today = base_date or datetime.now().date()
    return today + timedelta(days=4 - today.weekday())


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


def get_first_day_of_last_month():
    """
    获取上个月第一天的日期
    :return: 返回日期
    """
    today = datetime.today()
    year = today.year
    month = today.month
    if month == 1:
        month = 12
        year -= 1
    else:
        month -= 1
    res = datetime(year, month, 1)
    return res


def get_1st_of_next_month(today):
    """
    获取下个月的1号的日期
    :return: 返回日期
    """
    year = today.year
    month = today.month
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1
    res = datetime(year, month, 1).date()
    return res


def validate_email(email):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def get_protocol_host(request):
    protocol = 'https' if request.is_secure() else 'http'
    return protocol + "://" + request.get_host()


def get_file_suffix(filename):
    if filename and '.' in filename:
        return filename.rsplit(".", 1)[1]


# 讲数字金额转化为大写金额
def format_currency(currencyDigits):
    maximum_number = 99999999999.99
    cn_zero = "零"
    cn_one = "壹"
    cn_two = "贰"
    cn_three = "叁"
    cn_four = "肆"
    cn_five = "伍"
    cn_six = "陆"
    cn_seven = "柒"
    cn_eight = "捌"
    cn_nine = "玖"
    cn_ten = "拾"
    cn_hundred = "佰"
    cn_thousand = "仟"
    cn_ten_thousand = "万"
    cn_hundred_million = "亿"
    cn_symbol = "人民币"
    cn_dollar = "元"
    cn_ten_cent = "角"
    cn_cent = "分"
    cn_integer = "整"
    integral = None
    decimal = None
    outputCharacters = None
    parts = None
    digits, radices, bigRadices, decimals = None, None, None, None
    zeroCount = None
    i, p, d = None, None, None
    quotient, modulus = None, None
    currencyDigits = str(currencyDigits)
    if currencyDigits == "":
        return ""
    if float(currencyDigits) > maximum_number:
        print("转换金额过大!")
        return ""
    parts = currencyDigits.split(".")
    if len(parts) > 1:
        integral = parts[0]
        decimal = parts[1]
        decimal = decimal[0:2]
        if decimal == "0" or decimal == "00":
            decimal = ""
    else:
        integral = parts[0]
        decimal = ""
    digits = [cn_zero, cn_one, cn_two, cn_three, cn_four, cn_five, cn_six, cn_seven, cn_eight, cn_nine]
    radices = ["", cn_ten, cn_hundred, cn_thousand]
    bigRadices = ["", cn_ten_thousand, cn_hundred_million]
    decimals = [cn_ten_cent, cn_cent]
    outputCharacters = ""
    if int(integral) > 0:
        zeroCount = 0
        for i in range(len(integral)):
            p = len(integral) - i - 1
            d = integral[i]
            quotient = int(p / 4)
            modulus = p % 4
            if d == "0":
                zeroCount += 1
            else:
                if zeroCount > 0:
                    outputCharacters += digits[0]
                zeroCount = 0
                outputCharacters = outputCharacters + digits[int(d)] + radices[modulus]
            if modulus == 0 and zeroCount < 4:
                outputCharacters = outputCharacters + bigRadices[quotient]
        outputCharacters += cn_dollar
    if decimal != "":
        jiao = decimal[0]
        if jiao == "":
            jiao = "0"
        try:
            fen = decimal[1]
        except:
            fen = "0"
        if fen == "":
            fen = "0"
        if jiao == "0" and fen == "0":
            pass
        if jiao == "0" and fen != "0":
            outputCharacters = outputCharacters + cn_zero + digits[int(fen)] + decimals[1]
        if jiao != "0" and fen == "0":
            outputCharacters = outputCharacters + digits[int(jiao)] + decimals[0]
        if jiao != "0" and fen != "0":
            outputCharacters = outputCharacters + digits[int(jiao)] + decimals[0]
            outputCharacters = outputCharacters + digits[int(fen)] + decimals[1]
    if outputCharacters == "":
        outputCharacters = cn_zero + cn_dollar
    if decimal == "":
        outputCharacters = outputCharacters + cn_integer
    outputCharacters = outputCharacters
    return outputCharacters


def get_date_list(start_date, end_date):
    """
    获取开始结束日期列表
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return:
    """
    data = []
    current_date = start_date
    while current_date <= end_date:
        data.append(deepcopy(current_date))
        current_date = current_date + timedelta(days=1)
    return data


def get_date_str_list(start_date, end_date, date_format=settings.DATE_FORMAT):
    """
    获取开始结束日期列表
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param date_format:'%Y-%m-%d'
    :return:
    """
    data = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime(date_format)
        data.append(date_str)
        current_date = current_date + timedelta(days=1)
    return data


def get_month_str_list(start_date, end_date, date_format="%Y-%m"):
    """
    获取开始结束日期列表
    :param start_date: 开始日期
    :param end_date: 结束日期
    :param date_format:'%Y-%m-%d'
    :return:
    """
    data = []
    current_date = start_date
    end_date_format = end_date.strftime(date_format)
    while current_date.strftime(date_format) <= end_date_format:
        date_str = current_date.strftime(date_format)
        data.append(date_str)
        current_date = current_date + relativedelta(months=1)
    return data


def get_address_by_ip(ip):
    if not ip:
        return
    address = ''
    ignore_ips = ['127.0.0.1', 'localhost', '192.168', '0.0.0.0']
    try:
        if ip in ignore_ips:
            address = "本地"
        else:
            url = 'http://ip.taobao.com/service/getIpInfo.php?ip={}&accessKey=alibaba-inc'.format(ip)
            data = requests.get(url).json()
            if data['code'] == 0:
                address = data['data']['country'] + data['data']['area'] + data['data']['region'] + \
                          data['data']['city']
    except Exception as e:
        logging.getLogger().error(e)
        pass
    finally:
        return address


def get_request_ip(request):
    headers = (
        'HTTP_CLIENT_IP', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED',
        'HTTP_X_CLUSTERED_CLIENT_IP', 'HTTP_FORWARDED_FOR', 'HTTP_FORWARDED',
        'REMOTE_ADDR'
    )
    for header in headers:
        if request.META.get(header, None):
            ip = request.META[header].split(',')[0]
            try:
                validate_ipv46_address(ip)
                return ip
            except ValidationError:
                pass


def build_obj_ip_address(obj):
    if obj.ip:
        address = get_address_by_ip(obj.ip)
        if address:
            obj.address = address
            obj.save()
    return obj.address


def async_build_obj_ip_address(obj):
    thread = threading.Thread(target=build_obj_ip_address,
                              args=(obj,))
    thread.start()


def clean_text(text):
    rule = re.compile(r"[^a-zA-Z0-9\u4e00-\u9fa5]")
    text = rule.sub('', text)
    return text
