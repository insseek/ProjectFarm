# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
import os
import contextlib
import time

from django.core.cache import cache
from django.conf import settings
from django.urls import reverse
from celery import shared_task, app
from selenium.webdriver.support.wait import WebDriverWait
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from reports.models import Report
from reports.utils import extract_thread_blob, convert_opml_to_json

logger = logging.getLogger(__name__)


def build_report_group_list(reports):
    # report_type
    # TYPE_CHOICES = (
    #     ('proposal', '需求报告'),
    #     ('lead', '线索报告'),
    # )
    # 构建报告分组
    report_group_dict = {}
    report_group_list = []
    for report in reports:
        group_data, is_new_group = add_report_in_report_group_dict(report, report_group_dict)
        if is_new_group:
            report_group_list.append(group_data)
    return report_group_list, report_group_dict


@shared_task
def rebuild_all_proposal_lead_report_group_list_cache():
    build_all_report_group_list('proposal', rebuild=True)
    build_all_report_group_list('lead', rebuild=True)


def add_report_in_report_group_dict(report, report_group_dict):
    is_new_group = False
    content_object_id = report.content_object.id if report.content_object else ''
    group_key = '{report_type}-{object_id}-{title}'.format(report_type=report.report_type,
                                                           object_id=content_object_id,
                                                           title=report.title)
    if group_key not in report_group_dict:
        report_group_dict[group_key] = {
            "title": report.title,
            report.report_type: content_object_id or None,
            "reports": [],
            "published_at": report.published_at
        }
        is_new_group = True
    group_data = report_group_dict[group_key]
    if report.id not in group_data["reports"]:
        group_data["reports"].append(report.id)
    return group_data, is_new_group


ALL_REPORT_GROUP_DICT_KEY_TEMPLATE = "{report_type}_all_report_group_dict"


@shared_task
def add_report_to_all_report_group_cache_data(report_id):
    report = Report.objects.filter(pk=report_id).first()
    if report:
        report_type = report.report_type
        cache_key = ALL_REPORT_GROUP_DICT_KEY_TEMPLATE.format(report_type=report_type)
        report_group_dict = cache.get(cache_key, None)
        if not report_group_dict:
            reports = Report.objects.filter(is_public=True, report_type=report_type)
            report_group_list, report_group_dict = build_report_group_list(reports)
            cache.set(cache_key, report_group_dict, None)
        else:
            add_report_in_report_group_dict(report, report_group_dict)
            cache.set(cache_key, report_group_dict, None)


def build_all_report_group_list(report_type, rebuild=False):
    cache_key = ALL_REPORT_GROUP_DICT_KEY_TEMPLATE.format(report_type=report_type)
    report_group_dict = cache.get(cache_key, None)
    if not report_group_dict or rebuild:
        reports = Report.objects.filter(is_public=True, report_type=report_type)
        report_group_list, report_group_dict = build_report_group_list(reports)
        cache.set(cache_key, report_group_dict, None)
    else:
        report_group_list = sorted(report_group_dict.values(), key=lambda x: x['published_at'], reverse=True)
    return report_group_list, report_group_dict


@shared_task
def convert_opml_to_image(blob_urls, request_domain=None):
    if isinstance(blob_urls, str):
        blob_urls = [blob_urls, ]
    else:
        blob_urls = blob_urls
    blob_urls = set(blob_urls)
    need_processed_urls = []
    for blob_url in blob_urls:
        thread_id, blob_id = extract_thread_blob(blob_url)
        json_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.json'
        image_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.png'

        if not os.path.exists(image_path):
            if not os.path.exists(json_path):
                convert_opml_to_json(blob_url)
            if os.path.exists(json_path):
                need_processed_urls.append(blob_url)

    if need_processed_urls and settings.PHANTOMJS_PATH:
        browser = None
        try:
            browser = webdriver.PhantomJS(executable_path=settings.PHANTOMJS_PATH)
            # browser.set_window_size(960, 760)
            browser.set_window_size(738, 492)
            for blob_url in need_processed_urls:
                thread_id, blob_id = extract_thread_blob(blob_url)
                image_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.png'
                json_url = settings.QUIPFILE_URL + thread_id + '/' + blob_id + '.json'
                if os.path.exists(image_path):
                    continue
                logger.info(
                    'legin get_img_from_browser blob_url:{blob_url} image_path:{image_path}'.format(blob_url=blob_url,
                                                                                                    image_path=image_path))
                logger.info('get mindmap_url')
                mindmap_url = get_mindmap_url(json_url, request_domain=request_domain)
                logger.info('mindmap_url:{}'.format(mindmap_url))
                browser.get(mindmap_url)
                locator = (By.TAG_NAME, 'g')
                time.sleep(5)
                if os.path.exists(image_path):
                    continue
                try:
                    EC.presence_of_all_elements_located
                    WebDriverWait(browser, 15, 5).until(EC.presence_of_element_located(locator))
                    logger.info("element = browser.find_element_by_tag_name('svg')")
                    element = browser.find_element_by_tag_name('svg')
                    g_element = browser.find_element_by_tag_name('g')
                    if not all([g_element.size['width'], g_element.size['height']]):
                        logger.info('svg is empty')
                        continue
                    element_png = g_element.screenshot_as_png
                    logger.info('open(image_path, "wb") as file')
                    if os.path.exists(image_path):
                        continue
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


def get_mindmap_url(json_url, request_domain=None):
    if not request_domain:
        request_domain = settings.SITE_URL
    report_url = reverse('reports:mindmap_view') + '?json_url=' + json_url
    return request_domain + report_url
