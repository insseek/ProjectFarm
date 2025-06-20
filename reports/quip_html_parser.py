import logging
import os
import re

from bs4 import BeautifulSoup
from django.conf import settings

from gearfarm.utils.common_utils import gen_uuid
from reports.models import DocRecord, Plan, Section
from reports.utils import download_quip_file, convert_opml_to_json
from reports.tasks import convert_opml_to_image

logger = logging.getLogger(__name__)


class HTMLParser():
    def __init__(self, html, request_domain=None):
        self.title = ''
        self.html = html
        # 当前版本
        self.current_version = None
        # 版本记录
        self.doc_records = []

        # 报告内容列表 以h2分割
        self.sections = []
        self.catalogue = []

        # 时间报价预估
        self.plans = []

        self.request_domain = request_domain
        self.html = self.remove_comments()
        self.soup = BeautifulSoup(self.html, "html.parser")
        self.html = self.clean_html()

    def get_title(self):
        p_title = re.compile('<h1[\S\s]*>([\S\s]*)</h1>')
        for m in p_title.finditer(self.html):
            self.title = m.group(1).strip()
        return self.title

    def build_html(self):
        self.html = self.replace_image_path()
        self.html = self.replace_file_path()
        self.html = self.set_h3_tags_id()

        self.extract_info()
        self.extract_sections()
        return self.html

    def set_h3_tags_id(self):
        for tag in self.soup.find_all('h3'):
            tag['id'] = gen_uuid()
        return self.soup.prettify()

    def clean_html(self):
        whitelist = ['a', 'img']
        for tag in self.soup.find_all(True):
            if tag.name not in whitelist:
                tag.attrs = {}
            else:
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in ['src', 'href']:
                        del tag.attrs[attr]
        return self.soup.prettify()

    def remove_comments(self):
        self.html = self.html.split('<hr/>')[0].split('<hr')[0]
        self.html = re.sub(r'<annotation[\S\s]*?>', '', self.html)
        self.html = re.sub(r'</annotation>', '', self.html)

        return self.html

    def replace_image_path(self):
        image_tags = self.soup.find_all('img')
        for tag in image_tags:
            url = tag.get('src', None)
            if url:
                thread_id, blob_id = self.extract_thread_blob(url)
                file_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id
                if not os.path.exists(file_path):
                    download_quip_file(url)
                tag['src'] = tag['src'].replace('/blob/', settings.QUIPFILE_URL)
        return self.soup.prettify()

    def replace_file_path(self):
        file_tags = self.soup.find_all('a')
        for tag in file_tags:
            url = tag.get('href', None)
            if url and '/blob/' in url:
                url = url.split('/blob/')[-1]
                filename = tag.get_text()
                if filename:
                    filename = filename.strip()
                    if filename.endswith('opml'):
                        self.replace_mindmap_opml_file(tag)
                        continue
                tag['href'] = settings.QUIPFILE_URL + url
        return self.soup.prettify()

    def replace_mindmap_opml_file(self, tag):
        url = tag.get('href', None)
        thread_id, blob_id = self.extract_thread_blob(url)
        file_url = settings.QUIPFILE_URL + thread_id + '/' + blob_id + '.json'
        image_url = settings.QUIPFILE_URL + thread_id + '/' + blob_id + '.png'
        file_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.json'
        image_path = settings.QUIPFILE_ROOT + thread_id + '/' + blob_id + '.png'
        if not os.path.exists(file_path):
            convert_opml_to_json(url)
        if not os.path.exists(image_path):
            convert_opml_to_image.delay(url)

        new_div_tag = self.soup.new_tag("div")
        new_div_tag['class'] = 'mindmap-box'
        new_div_tag['data-file-url'] = file_url
        new_div_tag['data-image-url'] = image_url
        tag.insert_after(new_div_tag)
        tag.extract()

    def extract_thread_blob(self, url):
        url = url.split('?')[0]
        match = re.search(r'\/blob\/(\S+)\/(\S+)', url)
        if match:
            return match.group(1), match.group(2)
        else:
            raise ValueError('Invalid Image Tag')

    def extract_info(self):
        p_info = re.compile(
            r'版本[:：](?P<version>[\S\s]*?)\<[\S\s]*?日期[:：](?P<date>[\S\s]*?)\<[\S\s]*?制作人[:：](?P<author>[\S\s]*?)<')
        p_title = re.compile('<h1[\S\s]*>([\S\s]*)</h1>')
        for m in p_info.finditer(self.html):
            doc_record = DocRecord()
            doc_record.version = m.group('version').replace('<br>', '').replace('<p>', '').replace('</p>', '').rstrip()
            doc_record.date = m.group('date').replace('<br>', '').replace('<p>', '').replace('</p>', '').rstrip()
            doc_record.author = m.group('author').replace('<br>', '').replace('<p>', '').replace('</p>', '').rstrip()
            self.doc_records.append(doc_record)
        self.current_version = self.doc_records[0]
        for m in p_title.finditer(self.html):
            self.title = m.group(1).strip()

    def extract_sections(self):
        self.html = re.sub(r'<h2>[\s]*</h2>', '', self.html).strip()
        p_section = re.compile(r'<h2[\S\s]*?>(?P<title>[\S\s]*?)</h2>(?P<content>[\S\s]*?)(?=<h2)')
        for m in p_section.finditer(self.html):
            content = re.sub(r'<p>[\s]*(<br[/]?>)?[\s]*</p>', '', m.group('content')).strip()
            content = re.sub(r'\s+', '', content)

            section_title = re.sub(r'<[\S\s]*?>', '', m.group('title')).strip()
            section_content = m.group('content') if content else ''

            if section_content:
                section = Section()
                section.title = section_title
                section.content = section_content
                self.sections.append(section)

                catalogue_children = self.extract_subsection_catalogue(section_content)
                catalogue_data = {"title": section_title, "uid": section.uid, "type": "h2",
                                  "children": catalogue_children}
                self.catalogue.append(catalogue_data)

    # h3分割 三级标题
    def extract_subsection_catalogue(self, content):
        data = []
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup.find_all('h3'):
            uid = tag.get('id', None)
            title = tag.string.strip() if tag.string else ''
            if title:
                catalogue_data = {"title": title, "uid": uid, "type": "h3"}
                data.append(catalogue_data)
        return data

    def get_plans(self):
        self.plans.clear()
        p_oneplan = re.compile(r'<h3[\S\s]*?>(?P<title>[\S\s]*?)</h3>[\S\s]*?<p[\S\s]*?>(?P<plan>((?!\<h3)[\S\s])*)')
        p_sect = re.compile(r'(?P<name>[\S]*?)[:：](?P<content>[^<]*)')
        for m in p_oneplan.finditer(self.html):
            plan = Plan()
            plan.title = m.group('title').replace('<br>', '').replace('<p>', '').replace('</p>', '').strip()
            plantext = m.group('plan')
            for m in p_sect.finditer(plantext):
                name = m.group('name').replace('<br>', '').replace('<p>', '').replace('</p>', '').strip()
                content = m.group('content').replace('<br>', '').replace('<p>', '').replace('</p>', '').strip()
                item = (name, content)
                if name in ['报价估算', '报价']:
                    plan.price = content
                    if content and "万" in content:
                        plan.price = content.replace("万", '')
                        plan.price_unit = "万"
                else:
                    plan.items.append(item)
            self.plans.append(plan)
        return self.plans