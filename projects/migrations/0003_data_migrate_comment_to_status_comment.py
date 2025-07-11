# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-22 10:36
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.contenttypes.models import ContentType


def copy_comments(apps, schema_editor):
    Comment = apps.get_model("comments", "Comment")
    StatusComment = apps.get_model("projects", "StatusComment")
    try:
        project_type = ContentType.objects.get(app_label="projects", model="project")
    except Exception:
        return
    for comment in Comment.objects.filter(content_type=project_type.id):
        status_comment = StatusComment(
            author=comment.author,
            project_id=comment.object_id,
            content=comment.content,
            is_public=False,
            is_warning=False,
        )
        status_comment.save()
        status_comment.created_at = comment.create_at
        status_comment.save()


class Migration(migrations.Migration):
    dependencies = [

        ('projects', '0002_statuscomment'),
        ('comments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(copy_comments, migrations.RunPython.noop),
    ]
