import logging
import os
import re

from bs4 import BeautifulSoup
from django.conf import settings

from reports.utils import download_quip_file, download_quip_file_to_public_file

logger = logging.getLogger(__name__)


class HTMLParser():
    def __init__(self, html):
        self.html = html
        self.html = self.remove_comments()
        self.html = self.clean_html()
        self.soup = BeautifulSoup(self.html, "html.parser")

    def build_html(self):
        self.html = self.replace_image_path()
        self.html = self.replace_file_path()
        return self.html

    def clean_title(self):
        self.html = re.sub(r'<h1[\S\s]*>([\S\s]*)</h1>', "", self.html, 1)
        return self.html

    def clean_html(self):
        self.html = self.html.strip()
        self.html = self.clean_title()
        self.html = self.html.strip()
        return self.html

    def remove_comments(self):
        self.html = self.html.split('<hr/>')[0].split('<hr')[0]
        self.html = re.sub(r'<annotation[\S\s]*?>', '', self.html)
        self.html = re.sub(r'</annotation>', '', self.html)
        return self.html

    def replace_image_path(self):
        image_tags = self.soup.find_all('img')
        for tag in image_tags:
            url = tag.get('src', None)
            if url and '/blob/' in url:
                link = download_quip_file_to_public_file(url)
                tag['src'] = link
        return self.soup.prettify()

    def replace_file_path(self):
        file_tags = self.soup.find_all('a')
        for tag in file_tags:
            href = tag.get('href', None)
            if href and href.startswith('https://quip.com') and '/blob/' in href:
                filename = tag.text.strip() if tag.text else None
                link = download_quip_file_to_public_file(href, filename)
                tag['href'] = link
        return self.soup.prettify()

    def extract_thread_blob(self, url):
        url = url.split('?')[0]
        match = re.search(r'\/blob\/(\S+)\/(\S+)', url)
        if match:
            return match.group(1), match.group(2)
        else:
            raise ValueError('Invalid Image Tag')
