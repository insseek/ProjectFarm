# -*- coding:utf-8 -*-
PROPOSAL_STATUS_ACTIONS = {
    1: {'code': 1, 'codename': 'pending', 'name': '等待认领',
        "actions": ['assign']
        },
    2: {
        'code': 2, 'codename': 'contact', 'name': '等待沟通',
        "actions": ['contact', 'contract', 'others']
    },
    4: {
        'code': 4, 'codename': 'ongoing', 'name': '进行中',
        "actions": ['report', 'create_biz_opp', 'contract', 'others']
    },
    5: {'code': 5, 'codename': 'biz_opp', 'name': '商机',
        "actions": ['edit_biz_opp', 'contract', 'others']},
    6: {'code': 6, 'codename': 'contract', 'name': '成单交接',
        "actions": ['deal', 'others']},
    10: {'code': 10, 'codename': 'deal', 'name': '成单',
         "actions": ['edit']},
    11: {'code': 11, 'codename': 'no_deal', 'name': '未成单',
         "actions": ['reset', 'edit']},
}

LEAD_STATUS = {
    'contact': ('contact', '前期沟通'),
    'proposal': ('proposal', '进入需求'),
    'no_deal': ('no_deal', '未成单'),
    'deal': ('deal', '成单'),
    'apply_close': ('apply_close', '关闭审核'),
    'invalid': ('invalid', '无效关闭'),
}

PROPOSAL_STATUS_FLOW = (
    {'code': 1, 'codename': 'pending', 'name': '等待认领'},
    {'code': 2, 'codename': 'contact', 'name': '等待沟通'},
    {'code': 4, 'codename': 'ongoing', 'name': '进行中'},
    {'code': 5, 'codename': 'biz_opp', 'name': '商机'},
    {'code': 6, 'codename': 'contract', 'name': '成单交接'},
    {'code': 10, 'codename': 'deal', 'name': '成单'},
    {'code': 11, 'codename': 'no_deal', 'name': '未成单'},
)

DEVELOPMENT_GUIDES = {
    'JAVA开发规范和要求': {
        'title': 'JAVA开发规范和要求', 'link': 'http://documents.pages.git.chilunyc.com/public/java/guide.html',
        'keywords': ['Java']
    },
    'JAVA项目Readme模板': {
        'title': 'JAVA项目Readme模板', 'link': 'http://documents.pages.git.chilunyc.com/public/java/readme-template.html',
        'keywords': ['Java']
    },
    'JAVA参考代码规范': {
        'title': 'JAVA参考代码规范', 'link': 'http://documents.pages.git.chilunyc.com/public/java/spec.html',
        'keywords': ['Java']
    },
    'PHP-Laravel项目开发规范': {
        'title': 'PHP-Laravel项目开发规范', 'link': 'http://documents.pages.git.chilunyc.com/public/php-laravel/guide.html',
        'keywords': ['PHP']
    },
    'API设计与文档规范': {
        'title': 'API设计与文档规范', 'link': 'http://documents.pages.git.chilunyc.com/public/api.html',
        'keywords': ['后端工程师', 'Java', 'PHP', 'Python']
    },
    '前端JS规范': {
        'title': '前端JS规范', 'link': 'http://documents.pages.git.chilunyc.com/public/js/guide.html ',
        'keywords': ['前端工程师', '小程序工程师', 'JavaScript', 'HTML/CSS']
    },
    '关于服务端渲染（SSR）前端工程师注意事项': {
        'title': '关于服务端渲染（SSR）前端工程师注意事项',
        'link': 'http://documents.pages.git.chilunyc.com/public/ssr-nuxtjs/guide.html',
        'keywords': ['前端工程师', '小程序工程师', 'JavaScript', 'HTML/CSS']
    },
    'Android工程师须知': {
        'title': 'Android工程师须知', 'link': 'http://documents.pages.git.chilunyc.com/public/ssr-nuxtjs/guide.html',
        'keywords': ['Android', 'Kotlin']
    },
    'iOS工程师须知': {
        'title': 'iOS工程师须知', 'link': 'http://documents.pages.git.chilunyc.com/public/iOS/guide.html',
        'keywords': ['iOS工程师', 'Objective-C', 'Swift', 'iOS']
    },
    '齿轮微服务框架说明': {
        'title': '齿轮微服务框架说明', 'link': 'http://documents.pages.git.chilunyc.com/public/gear-cloud/guide.html',
        'keywords': []
    },
}
