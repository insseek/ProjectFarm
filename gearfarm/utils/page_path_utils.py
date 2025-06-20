def url_params_to_str(params={}, question_mark=True):
    params_str = ''
    if params:
        params_str = "?" if question_mark else ''
        for key, value in params.items():
            params_str += "{}={}&".format(key, value)
    return params_str


PAGE_PATH_DICT = {
    "project_view": {
        'name': '项目详情',
        "path": "/projects/detail/?projectId={id}"
    },
    "my_position_needs": {
        'name': '我的工程师需求',
        "path": '/projects/position_needs/mine/'
    },
    "projects_position_needs": {
        'name': '我的工程师需求',
        "path": '/projects/position_needs/'
    },
    # "report_view": {
    #     'name': '报告详情',
    #     "path": "/reports/{uid}",
    # },
    "project_calendar_detail": {
        'name': '项目日程计划详情',
        "path": "/projects/calendars/detail/?uid={uid}"
    },
    "project_delivery_document_download": {
        "path": "/projects/documents/download/?uid={uid}",
        'name': '项目交付文档下载',
    }
}


def build_page_path(page_code, kwargs={}, params={}):
    '''
    :param page_code: 自定义的页面code标识   与前端路由统一
    :param kwargs:  构造路由必须的参数
    :param params: 额外参数
    :return:
    '''
    path = PAGE_PATH_DICT.get(page_code, {}).get('path', '')
    if path:
        if kwargs:
            path = path.format(**kwargs)
        if params:
            question_mark = "?" not in path
            path += url_params_to_str(params, question_mark=question_mark)
    return path
