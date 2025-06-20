import re
import os

from django.conf import settings
from django.utils.http import urlquote
from bs4 import BeautifulSoup
from django.core.mail import send_mail

from gearfarm.utils.common_utils import gen_uuid
from reports.models import Section
from reports.utils import convert_mind_map_json_to_image


class QuillHTMLParser():
    def __init__(self, html, request_domain=None, request=None):
        self.request_domain = request_domain
        self.request = request
        self.title = ''
        self.html = html

        self.html = self.remove_comments()
        self.soup = BeautifulSoup(self.html, "html.parser")
        self.html = self.clean_comment_attrs()

        # 报告内容列表 以h2分割
        self.sections = []
        self.catalogue = []

    def build_html(self):
        self.html = self.clean_html()
        self.html = self.replace_mindmap_image_tag()
        self.html = self.set_h3_tags_id()
        # 替换空白行
        # self.html = re.sub(r'<p>[\s]*(<br[/]?>)?[\s]*</p>', '', self.html).strip()
        self.extract_sections()
        return self.html

    def set_h3_tags_id(self):
        for tag in self.soup.find_all('h3'):
            tag['id'] = gen_uuid()
        return self.soup.prettify()

    def clean_html(self):
        whitelist = ['table', 'colgroup', 'col', 'tbody', 'tr', 'td']
        for tag in self.soup.find_all(True):
            if tag.name in whitelist:
                continue
            else:
                attrs = dict(tag.attrs)
                if attrs.get('data-tag-flag', None) == 'gear-custom-module':
                    continue
                elif tag.name == 'li':
                    for attr in attrs:
                        if attr not in ['class', 'data-list']:
                            del tag.attrs[attr]
                elif tag.name in ['a', 'img']:
                    for attr in attrs:
                        if attr not in ['src', 'href', 'json_url', 'file_url', 'filename']:
                            del tag.attrs[attr]
                else:
                    tag.attrs = {}
        return self.soup.prettify()

    def clean_comment_attrs(self):
        for tag in self.soup.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                attr_value = tag.attrs[attr]
                if attr == 'comment_uid':
                    del attr_value
                if attr == 'class' and 'active' in attr_value:
                    if isinstance(attr_value, list):
                        attr_value.remove('active')
                    if isinstance(attr_value, str):
                        tag.attrs[attr] = attr_value.replace('active', '')
        return self.soup.prettify()

    def remove_comments(self):
        self.html = re.sub(r'<annotation[\S\s]*?>', '', self.html)
        self.html = re.sub(r'</annotation>', '', self.html)
        # self.html = re.sub(r'<span[\S\s]*?>', '', self.html)
        # self.html = re.sub(r'</span>', '', self.html)
        return self.html

    def replace_mindmap_image_tag(self):
        image_tags = self.soup.find_all('img')
        for tag in image_tags:
            if tag.get('json_url', None):
                opml_url = tag.get('file_url', None)
                filename = tag.get('filename', None)

                image_url = tag.get('src', None)
                json_url = tag.get('json_url', None)

                if 'chilunyc.com' in json_url:
                    json_path = json_url.split('chilunyc.com')[-1].replace(settings.MEDIA_URL, settings.MEDIA_ROOT)
                else:
                    json_path = json_url.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)

                if 'chilunyc.com' in image_url:
                    image_path = image_url.split('chilunyc.com')[-1].replace(settings.MEDIA_URL,
                                                                             settings.MEDIA_ROOT)
                else:
                    image_path = image_url.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)

                if (not os.path.exists(image_path)) and os.path.exists(json_path):
                    # message = "image_url[{image_url},json_url[{json_url}]], image_path[{image_path}] exists([{image_path_exists}]), MEDIA_URL[{media_url}],MEDIA_ROOT[{media_root}]".format(
                    #     image_url=image_url, json_url=json_url, image_path=image_path,
                    #     image_path_exists=os.path.exists(image_path), media_url=settings.MEDIA_URL,
                    #     media_root=settings.MEDIA_ROOT)
                    # send_mail("{}脑图图片不存在".format(self.request.path if self.request else ''), message,
                    #           settings.DEFAULT_FROM_EMAIL, ['fanping@chilunyc.com', ])
                    convert_mind_map_json_to_image(json_url, image_path, request_domain=self.request_domain)

                new_div_tag = self.soup.new_tag("div")
                new_div_tag['class'] = 'mindmap-box'
                new_div_tag['data-file-url'] = json_url
                new_div_tag['data-opml-url'] = opml_url
                new_div_tag['data-image-url'] = image_url
                new_div_tag['data-filename'] = filename
                tag.insert_after(new_div_tag)
                tag.extract()
        return self.soup.prettify()

    # h2分割  二级标题
    def extract_sections(self):
        # 匹配h2及到下一个h2之间的内容
        p_section = re.compile(r'<h2[\S\s]*?>(?P<title>[\S\s]*?)</h2>(?P<content>[\S\s]*?)(?=<h2)')
        # 清除空白的h2
        self.html = re.sub(r'<h2>[\s]*</h2>', '', self.html).strip()
        for m in p_section.finditer(self.html + '<h2>'):
            content = re.sub(r'<p>[\s]*(<br[/]?>)?[\s]*</p>', '', m.group('content')).strip()
            content = re.sub(r'\s+', '', content)

            section_title = re.sub(r'<[\S\s]*?>', '', m.group('title')).strip()
            section_content = m.group('content') if content else ''

            if section_title or section_content:
                section = Section()
                section.title = section_title
                section.content = section_content
                self.sections.append(section)

                catalogue_children = self.extract_subsection_catalogue(section_content)
                catalogue_data = {"title": section_title, "uid": section.uid, "type": "h2",
                                  "children": catalogue_children}
                self.catalogue.append(catalogue_data)

        if not self.sections:
            section = Section()
            section.title = "报告内容"
            section.content = self.html
            self.sections.append(section)

    # h3分割 三级标题
    def extract_subsection_catalogue(self, content):
        data = []
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup.find_all('h3'):
            uid = tag.get('id', None)
            title = tag.string.strip() if tag.string else ''
            if title:
                catalogue_data = {"title": title, "uid": uid, "type": 'h3'}
                data.append(catalogue_data)
        return data
