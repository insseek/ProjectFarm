import logging
import re
from datetime import timedelta
import os

from django.conf import settings
from django.utils import timezone
from reports import quip
from reports.quip_html_parser import HTMLParser
from reports.models import Report
from reports.utils import download_quip_file, convert_opml_to_json, get_report_uid
from reports.tasks import convert_opml_to_image

logger = logging.getLogger(__name__)


class QuipToReport():
    def __init__(self, url=None, html=None, request_domain=None, request=None):
        self.doc_records = []
        self.current_version = None
        self.plans = []
        self.sections = []
        self.url = url
        self.title = ''
        self.client = quip.QuipClient(settings.QUIP_TOKEN)
        self.request_domain = request_domain
        self.request = request
        if url:
            self.thread_id = self.extract_thread_id(url)
            if self.thread_id:
                self.html = self.get_html(self.thread_id)
            else:
                raise ValueError('Invalid Url')
            self.html_parser = HTMLParser(self.html)
        if html:
            self.html = html
            self.html_parser = HTMLParser(self.html)

    def extract_thread_id(self, url):
        match = re.search(r'https\://quip\.com/(?P<thread_id>\S+)', url)
        if match:
            return match.group(1)
        return None

    def extract_thread_blob(self, url):
        url = url.split('?')[0]
        match = re.search(r'\/blob\/(\S+)\/(\S+)', url)
        if match:
            return match.group(1), match.group(2)
        else:
            raise ValueError('Invalid Image Tag')

    def get_html(self, thread_id):
        thread = self.client.get_thread(thread_id)
        return thread['html']

    def get_img_blobs_urls(self):
        logger.info("开始获取所有img的url")
        url_set = set()
        tags = self.html_parser.soup.find_all('img')
        for tag in tags:
            url = tag.get('src', None)
            logger.info("img的src为{}".format(url))
            if url and '/blob/' in url:
                url_set.add(url)
        return url_set

    def get_opml_blobs_urls(self):
        logger.info("开始脑图文件urls")
        url_set = set()
        tags = self.html_parser.soup.find_all('a')
        for tag in tags:
            url = tag.get('href', None)
            logger.info("'a标签的的href为{}".format(url))
            if url and '/blob/' in url:
                filename = tag.get_text()
                if filename.endswith('.opml'):
                    logger.info("获取到脑图opml文件:{}".format(filename))
                    url_set.add(url)
        return url_set

    def save_blobs(self, blob_urls):
        download_quip_file(blob_urls)

    def opmls_to_jsons(self, blob_urls):
        """报告中的opml文件默认为脑图文件"""
        convert_opml_to_json(blob_urls)

    def opmls_to_image(self, blob_urls):
        """报告中的opml文件默认为脑图文件"""
        blob_urls = set(blob_urls)
        need_processed_urls = []
        for blob_url in blob_urls:
            thread_id, blob_id = self.extract_thread_blob(blob_url)
            image_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.png'
            if not os.path.exists(image_path):
                need_processed_urls.append(blob_url)
        if need_processed_urls:
            convert_opml_to_image.delay(need_processed_urls)

    def create_report(self, proposal, show_next, show_services):
        img_urls = self.get_img_blobs_urls()
        opml_urls = self.get_opml_blobs_urls()
        self.save_blobs(img_urls)
        self.save_blobs(opml_urls)
        self.opmls_to_jsons(opml_urls)
        self.opmls_to_image(opml_urls)
        uuid = get_report_uid()
        report = Report(
            proposal=proposal,
            markdown='',
            creation_source='quip_link',
            html=self.html_parser.html,
            title=self.html_parser.title,
            version=self.html_parser.current_version.version,
            author=self.html_parser.current_version.author,
            date=self.html_parser.current_version.date,
            uid=uuid,
            show_next=show_next,
            show_services=show_services,
            expired_at=timezone.now() + timedelta(days=14),
            published_at=timezone.now()
        )
        if self.request:
            report.creator = self.request.user
        return report

    def replace_report(self, proposal, show_next, show_services, repeated_report=None):
        if repeated_report:
            img_urls = self.get_img_blobs_urls()
            opml_urls = self.get_opml_blobs_urls()
            self.save_blobs(img_urls)
            self.save_blobs(opml_urls)
            self.opmls_to_jsons(opml_urls)
            repeated_report.proposal = proposal
            repeated_report.markdown = ''
            repeated_report.html = self.html_parser.html
            repeated_report.title = self.html_parser.title
            repeated_report.version = self.html_parser.current_version.version
            repeated_report.author = self.html_parser.current_version.author
            repeated_report.date = self.html_parser.current_version.date
            repeated_report.show_next = show_next
            repeated_report.show_services = show_services
            repeated_report.created_at = timezone.now()
            repeated_report.published_at = timezone.now()
            if self.request:
                repeated_report.creator = self.request.user
            repeated_report.save()
            repeated_report.extend_expiration()
            return repeated_report
