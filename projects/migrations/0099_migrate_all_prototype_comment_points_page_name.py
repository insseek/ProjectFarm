from __future__ import unicode_literals
import re
import shutil
import urllib

from django.db import migrations
from django.core.cache import cache
from django.conf import settings

from farmbase.utils import encrypt_string


def migrate_prototype_comment_points_html_name(apps, schema_editor):
    PrototypeCommentPoint = apps.get_model("projects", "PrototypeCommentPoint")
    ProjectPrototype = apps.get_model("projects", "ProjectPrototype")
    comment_points = PrototypeCommentPoint.objects.all()

    for comment_point in comment_points:
        page_name = ''
        if comment_point.page_name:
            page_name = urllib.parse.unquote(comment_point.page_name)
        else:
            url_hash = urllib.parse.unquote(comment_point.url_hash)
            hash_list = re.sub(r'[#&]', ' ', url_hash).split()
            for hash_item in hash_list:
                if hash_item and hash_item.startswith('p='):
                    page_name = hash_item.split('p=')[-1]
            if page_name:
                page_name = page_name + '.html'
        comment_point.page_name = page_name
        comment_point.save()
    prototypes = ProjectPrototype.objects.all()
    for prototype in prototypes:
        key = 'prototype-{}-comments'.format(prototype.uid)
        cache.delete(key)
        prototype_dir = settings.PROTOTYPE_ROOT + encrypt_string(prototype.uid)[:16] + '/'
        shutil.rmtree(prototype_dir, True)


class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0098_auto_20190425_1331'),
    ]

    operations = [
        migrations.RunPython(migrate_prototype_comment_points_html_name, migrations.RunPython.noop),
    ]
