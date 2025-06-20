from datetime import datetime, timedelta
import logging
import os
import re
import contextlib
import json
import time
from functools import wraps
from django.utils import six

from django.core.cache import cache
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlquote
from django.utils.decorators import available_attrs
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.base import ContentFile
from selenium.webdriver.support.wait import WebDriverWait
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from tenacity import retry, wait_fixed, stop_after_attempt
import xmltodict

from farmbase.utils import gen_uuid
from reports import quip
from reports.models import Report
from files.models import PublicFile

logger = logging.getLogger(__name__)


def get_report_uid():
    return 'r' + timezone.now().strftime('%y%m%d') + gen_uuid(length=16)


def get_report_date(date):
    return "{year}.{month}.{day}".format(year=date.year, month=date.month, day=date.day)


# 构造报告列表缓存数据 结束
# 生成报告时对文档中文件的下载 开始
def extract_thread_blob(url):
    url = url.split('?')[0]
    match = re.search(r'\/blob\/(\S+)\/(\S+)', url)
    if match:
        return match.group(1), match.group(2)
    else:
        raise ValueError('Invalid Image or File Tag')


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def save_quip_file(file_path, client, thread_id, blob_id):
    with open(file_path, 'wb') as blob_file:
        blob = client.get_blob(thread_id, blob_id)
        content = blob.read()
        if content:
            blob_file.write(content)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def download_quip_file(blob_urls):
    if isinstance(blob_urls, str):
        blob_urls = [blob_urls, ]
    else:
        blob_urls = blob_urls
    blob_urls = set(blob_urls)
    need_processed_urls = []
    for blob_url in blob_urls:
        thread_id, blob_id = extract_thread_blob(blob_url)
        file_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if not os.path.exists(file_path):
            need_processed_urls.append(blob_url)

    if need_processed_urls:
        client = quip.QuipClient(settings.QUIP_TOKEN)
        for blob_url in need_processed_urls:
            thread_id, blob_id = extract_thread_blob(blob_url)
            file_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id
            logger.info("begin download quip file:{}".format(blob_url))
            try:
                save_quip_file(file_path, client, thread_id, blob_id)
            except Exception as exc:
                with contextlib.suppress(FileNotFoundError):
                    os.remove(file_path)
                logger.error(exc)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def save_quip_file_to_public_file(thread_id, blob_id, filename=None):
    client = quip.QuipClient(settings.QUIP_TOKEN)
    blob = client.get_blob(thread_id, blob_id)
    content = blob.read()
    if content:
        file_name = filename or 'quip-{thread_id}-{blob_id}'.format(thread_id=thread_id, blob_id=blob_id)
        file = ContentFile(content, file_name)
        public_file = PublicFile.objects.create(file=file, filename=file_name)
        return public_file.clean_url


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def download_quip_file_to_public_file(blob_url, filename=None):
    thread_id, blob_id = extract_thread_blob(blob_url)
    link = save_quip_file_to_public_file(thread_id, blob_id, filename=filename)
    return link


def convert_opml_to_json(blob_urls):
    if isinstance(blob_urls, str):
        blob_urls = [blob_urls, ]
    else:
        blob_urls = blob_urls
    blob_urls = set(blob_urls)
    need_processed_urls = []
    for blob_url in blob_urls:
        thread_id, blob_id = extract_thread_blob(blob_url)
        xml_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id
        json_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.json'
        if not os.path.exists(json_path):
            if not os.path.exists(xml_path):
                download_quip_file(blob_url)
            if os.path.exists(xml_path):
                need_processed_urls.append(blob_url)

    if need_processed_urls:
        for blob_url in need_processed_urls:
            thread_id, blob_id = extract_thread_blob(blob_url)
            xml_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id
            json_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.json'
            xml_str = ''
            with open(xml_path, 'rb') as xml_file:
                # 读取xml文件内容
                xml_str = xml_file.read().decode(encoding='utf-8')
                if xml_str:
                    xml_str = xml_str.replace('&', '与')
                    json_text = xmltodict.parse(xml_str)
                    result_data = json_text['opml']['body']['outline']
                    json_str = json.dumps(result_data, ensure_ascii=False)
                    data = json_str.replace('@text', 'name').replace('outline', 'children')
                    logger.info("save_mindmap_opml_file %s" % (json_path))
                    with open(json_path, 'w', encoding='utf-8') as json_file:
                        json_file.write(data)
                else:
                    logger.info("{} xml is empty".format(xml_path))
                    os.remove(xml_path)


def download_and_convert_opml_to_json_and_img(mind_map, request_domain=None):
    relative_path = "reports/mind_maps/{uid}.opml".format(uid=mind_map.uid)
    relative_path = urlquote(relative_path)
    file_path = settings.MEDIA_ROOT + relative_path
    file_url = settings.MEDIA_URL + relative_path

    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(file_path, 'wb') as file:
        content = mind_map.file.file.read()
        file.write(content)

    json_relative_path = "reports/mind_maps/{uid}.json".format(uid=mind_map.uid)
    json_relative_path = urlquote(json_relative_path)
    json_path = settings.MEDIA_ROOT + json_relative_path
    json_url = settings.MEDIA_URL + json_relative_path
    dir_path = os.path.dirname(json_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    with open(file_path, 'rb') as xml_file:
        # 读取xml文件内容
        xml_str = xml_file.read().decode(encoding='utf-8')
        if xml_str:
            xml_str = xml_str.replace('&', '与')
            json_text = xmltodict.parse(xml_str)
            result_data = json_text['opml']['body']['outline']
            json_str = json.dumps(result_data, ensure_ascii=False)
            data = json_str.replace('@text', 'name').replace('outline', 'children')
            logger.info("save_mindmap_opml_file %s" % (json_path))
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json_file.write(data)
        else:
            logger.info("{} xml is empty".format(file_path))
            os.remove(file_path)
            return
    if not os.path.exists(json_path):
        return False

    image_relative_path = "reports/mind_maps/{uid}.png".format(uid=mind_map.uid)
    image_relative_path = urlquote(image_relative_path)
    image_path = settings.MEDIA_ROOT + image_relative_path
    image_url = settings.MEDIA_URL + image_relative_path
    dir_path = os.path.dirname(image_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    convert_mind_map_json_to_image(json_url, image_path, request_domain=request_domain)
    if not os.path.exists(image_path):
        return False
    mind_map.file_url = file_url
    mind_map.json_url = json_url
    mind_map.image_url = image_url
    mind_map.save()
    return True


def convert_mind_map_json_to_image(json_url, image_path, request_domain=None):
    if settings.PHANTOMJS_PATH:
        browser = None
        try:
            browser = webdriver.PhantomJS(executable_path=settings.PHANTOMJS_PATH)
            browser.set_window_size(738, 492)
            if os.path.exists(image_path):
                return
            mindmap_url = get_mindmap_url(json_url, request_domain=request_domain)
            logger.info('mindmap_url:{}'.format(mindmap_url))
            browser.get(mindmap_url)
            locator = (By.TAG_NAME, 'g')
            time.sleep(5)
            if os.path.exists(image_path):
                return
            try:
                EC.presence_of_all_elements_located
                WebDriverWait(browser, 15, 5).until(EC.presence_of_element_located(locator))
                logger.info("element = browser.find_element_by_tag_name('svg')")
                element = browser.find_element_by_tag_name('svg')
                g_element = browser.find_element_by_tag_name('g')
                if not all([g_element.size['width'], g_element.size['height']]):
                    logger.info('svg is empty')
                    return
                element_png = g_element.screenshot_as_png
                logger.info('open(image_path, "wb") as file')
                if os.path.exists(image_path):
                    return
                with open(image_path, "wb") as file:
                    file.write(element_png)
            except Exception as exc:
                with contextlib.suppress(FileNotFoundError):
                    if os.path.exists(image_path):
                        os.remove(image_path)
                logger.error("fail to element.screenshot_as_png :{}".format(exc))
            finally:
                if browser:
                    browser.close()
        except Exception as exc:
            logger.error("fail to convert_opml_to_image:{}".format(exc))
        finally:
            if browser:
                browser.quit()

    if os.path.exists(image_path):
        return True


def get_mindmap_url(json_url, request_domain=None):
    if not request_domain:
        request_domain = settings.SITE_URL
    report_url = reverse('reports:mindmap_view') + '?json_url=' + json_url
    return request_domain + report_url


def download_frame_diagram(frame_diagram):
    suffix = '.' + frame_diagram.suffix if frame_diagram.suffix else ''
    relative_path = "reports/frame_diagrams/{uid}{suffix}".format(uid=frame_diagram.uid, suffix=suffix)
    relative_path = urlquote(relative_path)
    file_path = settings.MEDIA_ROOT + relative_path
    file_url = settings.MEDIA_URL + relative_path
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(file_path, 'wb') as file:
        content = frame_diagram.file.file.read()
        file.write(content)
        frame_diagram.file_url = file_url
        frame_diagram.save()


def download_report_file(frame_diagram):
    suffix = '.' + frame_diagram.suffix if frame_diagram.suffix else ''
    relative_path = "reports/files/{uid}{suffix}".format(uid=frame_diagram.uid, suffix=suffix)
    relative_path = urlquote(relative_path)
    file_path = settings.MEDIA_ROOT + relative_path
    file_url = settings.MEDIA_URL + relative_path
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(file_path, 'wb') as file:
        content = frame_diagram.file.file.read()
        file.write(content)
        frame_diagram.file_url = file_url
        frame_diagram.save()


# 生成报告时对文档中文件的下载 结束

from notifications.tasks import send_report_editable_data_update_reminder

# 报告编辑时 当前页面用户数据缓存 开始
'''
存储在缓存中的数据结构
{'report_uid':
    {
        'users': {
            'user1': {'username': 'user1', 'updated_at': timezone.now()},
            'user2': {'username': 'user2', 'updated_at': timezone.now()}
        },
        'editable_data': {'username': 'user3', 'updated_at': timezone.now()}
    }
}
'''


# 1、用户进入页面
def report_user_return(report, user):
    report_uid = report.uid
    username = user.username
    report_id = report.id
    is_updated = False
    now = timezone.now()
    reports_data = cache.get('reports_editable_data', {})

    viewing_user_data = {'username': username, 'updated_at': now}
    if not reports_data or report.uid not in reports_data:
        is_updated = True
        editable_data = {'username': None, 'updated_at': None}
        report_data = {"users": {username: viewing_user_data}, 'editable_data': editable_data}
    else:
        report_data = reports_data[report_uid]
        if username not in report_data['users']:
            is_updated = True
        if isinstance(report_data['users'], set):
            users_data = {}
            for user in report_data['users']:
                users_data[user] = {'username': user, 'updated_at': now}
            report_data['users'] = users_data
        report_data['users'][username] = viewing_user_data
    reports_data[report_uid] = report_data
    cache.set('reports_editable_data', reports_data, None)
    if is_updated:
        send_report_editable_data_update_reminder.delay(report_id)


# 2、用户离开页面
def report_user_leave(report, user):
    username = user.username
    reports_data = cache.get('reports_editable_data', {})
    is_updated = False
    if reports_data:
        if report.uid in reports_data:
            report_data = reports_data[report.uid]
            editable_data = report_data['editable_data']
            if username in report_data['users']:
                is_updated = True
                del report_data['users'][username]
            if editable_data and editable_data['username'] == username:
                is_updated = True
                report_data['editable_data'] = {'username': None, 'updated_at': None}
            if is_updated:
                cache.set('reports_editable_data', reports_data, None)
                send_report_editable_data_update_reminder.delay(report.id)


# 3、用户编辑

def report_user_edit(report, user):
    username = user.username
    reports_data = cache.get('reports_editable_data', {})
    is_updated = False
    now = timezone.now()
    user_data = {'username': username, 'updated_at': now}
    if not reports_data or report.uid not in reports_data:
        is_updated = True
        report_data = {"users": {username: user_data}, 'editable_data': user_data}
    else:
        report_data = reports_data[report.uid]
        if username not in report_data['users']:
            is_updated = True
            report_data['users'][username] = user_data
        if report_data['editable_data'] and username != report_data['editable_data']['username']:
            is_updated = True
        report_data['editable_data'] = user_data
    reports_data[report.uid] = report_data
    cache.set('reports_editable_data', reports_data, None)
    if is_updated:
        send_report_editable_data_update_reminder.delay(report.id)


def json_response_bad_request(message=''):
    if not message:
        message = '检查请求参数'
    return JsonResponse({'result': False, 'message': message}, json_dumps_params={'ensure_ascii': False})


# 4、获取用户编辑权限
def get_report_editable_result(request, report):
    reports_editable_data = cache.get('reports_editable_data')
    if reports_editable_data and report.uid in reports_editable_data:
        report_editable_data = reports_editable_data[report.uid]['editable_data']
        try:
            editable_user = report_editable_data['username']
            updated_at = report_editable_data['updated_at']
            if editable_user and updated_at > timezone.now() - timedelta(
                    minutes=3) and editable_user != request.user.username:
                return {"result": False, 'editable_user': editable_user}
        except KeyError:
            return {"result": True, 'editable_user': None}
    return {"result": True, 'editable_user': None}


# 5、检查用户编辑权限装饰器

def check_report_editable_status():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, uid, *args, **kwargs):
            report = Report.objects.filter(uid=uid)
            if not report.exists():
                return json_response_bad_request(message="该报告不存在")
            report = report.first()
            editable_result = get_report_editable_result(request, report)
            if not editable_result['result']:
                message = "该报告{}正在编辑，你不能同时操作".format(editable_result['editable_user'])
                return json_response_bad_request(message=message)
            report_user_edit(report, request.user)
            return view_func(request, uid, *args, **kwargs)

        return _wrapped_view

    return decorator


def check_report_deletable_status():
    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(request, uid, *args, **kwargs):
            report = Report.objects.filter(uid=uid)
            if not report.exists():
                return json_response_bad_request(message="该报告不存在")
            report = report.first()
            editable_result = get_report_editable_result(request, report)
            if not editable_result['result']:
                message = "该报告{}正在编辑，你不能同时操作".format(editable_result['editable_user'])
                return json_response_bad_request(message=message)
            return view_func(request, uid, *args, **kwargs)

        return _wrapped_view

    return decorator
# 报告编辑时 当前页面用户数据缓存 结束
