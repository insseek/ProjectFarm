import re
from copy import deepcopy
from itertools import chain
from bs4 import BeautifulSoup

import reports.diff_match_patch as dmp_module


class ReportHTMLParser():
    def __init__(self, html):
        self.html = html
        self.soup = BeautifulSoup(self.html, "html.parser")
        self.images = []
        self.links = []
        self.extract_media_tags()

        self.html = self.clean_comments()
        self.html = self.clean_medias()
        self.html = self.clean_html_tag()

    def extract_media_tags(self):
        self.images = self.soup.find_all('img')
        self.links = self.soup.find_all('a')

    def clean_html_tag(self):
        for tag in self.soup.find_all(True):
            tag.attrs = {}
        self.html = self.soup.prettify()
        self.html = re.sub(r'<p>[\s]*(<br[/]?>)?[\s]*</p>', '', self.html).strip()
        return self.html

    def clean_medias(self):
        images = self.soup.find_all('img')
        links = self.soup.find_all('a')
        for tag in chain(images, links):
            tag.extract()
        return self.soup.prettify()

    def clean_comments(self):
        self.html = re.sub(r'<annotation[\S\s]*?>', '', self.html)
        self.html = re.sub(r'</annotation>', '', self.html)
        self.html = re.sub(r'<span[\S\s]*?>', '', self.html)
        self.html = re.sub(r'</span>', '', self.html)
        return self.soup.prettify()


class DiffReportHTML():
    def __init__(self, origin_html, html):
        self.origin_html = origin_html if origin_html else ''
        self.html = html if html else ''
        self.origin_html_parser = ReportHTMLParser(self.origin_html)
        self.html_parser = ReportHTMLParser(self.html)

        self.origin_html = self.origin_html_parser.html
        self.html = self.html_parser.html

        self.origin_images = self.origin_html_parser.images
        self.images = self.html_parser.images
        self.diff_html = ''
        self.diff_images = {'insert': [], 'delete': []}

    def build_diff_html(self):
        dmp = dmp_module.diff_match_patch()
        diff = dmp.diff_main(self.origin_html, self.html)
        dmp.diff_cleanupSemantic(diff)
        # result: [(-1, "Hell"), (1, "G"), (0, "o"), (1, "odbye"), (0, " World.")]
        # 1：新增, 0：保持 ,-1:删除
        diff_html = ''
        is_diff = False
        for flag, text in diff:
            if flag != 0:
                is_diff = True
                break
        if not is_diff:
            return None
        for result_flag, result_text in diff:
            if result_text:
                origin = deepcopy(result_text)
                text = deepcopy(result_text)
                text = re.sub(r'<[\S\s]*?>', '蠿龘', text)
                text = re.sub(r'[\S\s]*?>', '蠿龘', text)
                text = re.sub(r'</[\S\s]*', '蠿龘', text)
                text = re.sub(r'<[\S\s]*', '蠿龘', text)
                text_list = text.split('蠿龘')
                for text_item in set(text_list):
                    if text_item and text_item.strip():
                        clean_text = text_item.strip()
                        if result_flag == 0:
                            origin = origin.replace(clean_text, '<span class="retain-text">{}</span>'.format(clean_text))
                        if result_flag == 1:
                            origin = origin.replace(clean_text, '<span class="insert-text">{}</span>'.format(clean_text))
                        if result_flag == -1:
                            origin = origin.replace(clean_text, '<span class="delete-text">{}</span>'.format(clean_text))
                origin = re.sub(r'\r\n', '<br>', origin)
                origin = re.sub(r'\n', '<br>', origin)
                diff_html += origin
        diff_html = re.sub(r'(<br>)+', '<br>', diff_html)
        self.diff_html = diff_html
        return self.diff_html

    def build_diff_images(self):
        origin_images = [image.attrs['src'] for image in self.origin_images]
        images = [image.attrs['src'] for image in self.images]
        diff_images = {'insert': [], 'delete': []}
        for image in self.images:
            if image.attrs['src'] not in origin_images:
                diff_images['insert'].append(dict(image.attrs))
        for image in self.origin_images:
            if image.attrs['src'] not in images:
                diff_images['delete'].append(dict(image.attrs))
        self.diff_images = diff_images
        return self.diff_images
