# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations
from prototypes.models import Platform, Category


def init_platform_categoty_data(apps, schema_editor):
    CATEGORIES = [
        '导航', '各类列表', '登录', '注册', '密码类', '个人中心', 'Profile', 'Feed', '搜索', '聊天', '订单', '购物车', '支付', '会员', '隐私', '积分',
        '排行榜', '拦截引导', '动效', '数据统计展示', '管理系统', '营销推广类', '发布', '地图类','启动页'
    ]

    PLATFORMS = [
        'APP',
        'H5',
        '公众号',
        '小程序',
        'PC-web',
        '其他'
    ]

    for category in CATEGORIES:
        if not Category.objects.filter(name=category).exists():
            Category.objects.create(name=category)

    for platform in PLATFORMS:
        if not Platform.objects.filter(name=platform).exists():
            Platform.objects.create(name=platform)


class Migration(migrations.Migration):
    dependencies = [
        ('prototypes', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(init_platform_categoty_data, migrations.RunPython.noop),
    ]
