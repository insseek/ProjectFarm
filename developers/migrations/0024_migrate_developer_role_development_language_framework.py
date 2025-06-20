# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.db import migrations


def data_migrate_role_development_language_framework(apps, schema_editor):
    Role = apps.get_model("developers", "Role")
    Developer = apps.get_model("developers", "Developer")
    mini_program_role, created = Role.objects.get_or_create(name="小程序工程师")
    developers = Developer.objects.all()

    for developer in developers.filter(Q(development_languages__name='小程序') | Q(frameworks__name='小程序')):
        developer.roles.add(mini_program_role)

    for developer in developers.filter(development_languages__name='小程序'):
        developer.development_languages.remove('小程序')
    for developer in developers.filter(frameworks__name='小程序'):
        developer.frameworks.remove('小程序')

    for developer in developers.filter(frameworks__name='ReactNative'):
        developer.frameworks.add('React Native')
        developer.frameworks.remove('ReactNative')

    for developer in developers.filter(frameworks__name='iOS'):
        developer.frameworks.remove('iOS')


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0023_developer_gitlab_user_id'),
    ]
    operations = [
        migrations.RunPython(data_migrate_role_development_language_framework, migrations.RunPython.noop),
    ]
