# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations


def change_developers_status(apps, schema_editor):
    Developer = apps.get_model("developers", "Developer")

    Developer.objects.filter(status='B').update(status='0')
    Developer.objects.filter(status='A').update(status='1')

    DEVELOPMENT_LANGUAGES = {
        'python': 'Python',
        'java': 'Java',
        'Android': 'Java',
        'PHP': 'PHP',
        'JavaScript': 'JavaScript',
        'js': 'JavaScript',
        'Swift': 'Swift',
        'Objective-C': 'Objective-C',
        'iOS': 'Objective-C',
        'HTML': 'HTML/CSS',
        'Kotlin': 'Kotlin'
    }

    FRAMEWORKS = {
        'Yii': 'Yii2',
        'Laravel': 'Laravel',
        'react': 'React',
        'spring': 'Spring',
        'vue': 'Vue',
        '小程序': '小程序',
        'PS': 'PS',
        'Sketch': 'Sketch',
        'node': 'Node.js',
        'flask': 'Flask',
        'angular': 'Angular',
        'express': 'Express',
        'Django': 'Django'
    }

    developers = Developer.objects.prefetch_related("tags").all()
    for developer in developers:
        developer_tags = developer.tags.all().values_list('name', flat=True)
        development_languages = set()
        frameworks = set()
        for tag in developer_tags:
            if tag in DEVELOPMENT_LANGUAGES:
                development_languages.add(DEVELOPMENT_LANGUAGES[tag])
            if tag in FRAMEWORKS:
                frameworks.add(FRAMEWORKS[tag])
        developer.development_languages.add(*development_languages)
        developer.frameworks.add(*frameworks)


class Migration(migrations.Migration):
    dependencies = [
        ('developers', '0013_auto_20180205_1350'),
    ]
    operations = [
        migrations.RunPython(change_developers_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='developer',
            name='tags',
        ),
    ]
