from datetime import datetime
import os
from wsgiref.util import FileWrapper
from django.http import FileResponse
from django.utils.encoding import escape_uri_path
from django.conf import settings
from xlwt import Workbook


def build_excel_response(data, export_fields, filename, verbose_filename=''):
    verbose_filename = verbose_filename or filename
    w = Workbook()  # 创建一个工作簿
    ws = w.add_sheet(verbose_filename)  # 创建一个工作表
    # 写表头
    for index_num, field in enumerate(export_fields):
        ws.write(0, index_num, field['verbose_name'])
    # 表头宽度
    for i in range(len(export_fields)):
        ws.col(i).width = 256 * export_fields[i]['col_width']
    # 写每一行
    for index_num, item_data in enumerate(data):
        for field_num, field in enumerate(export_fields):
            ws.write(index_num + 1, field_num, item_data[field['field_name']])

    time_str = datetime.now().strftime('%y%m%d%H%M')
    path = settings.MEDIA_ROOT + '{}-{}.xls'.format(filename, time_str)

    dir_path = os.path.dirname(path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    w.save(path)  # 保存
    wrapper = FileWrapper(open(path, 'rb'))
    response = FileResponse(wrapper, content_type='application/vnd.ms-excel')
    filename = "{}-{}.xls".format(verbose_filename, time_str)
    response['Content-Disposition'] = "attachment; filename*=utf-8''{}".format(escape_uri_path(filename))
    response['Access-Control-Expose-Headers'] = 'Content-Disposition'
    return response
