# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import shared_task
import zipfile
import os
import logging
import codecs
import shutil

from django.core.cache import cache
from django.conf import settings
from django.core.files import File
from django.contrib.auth.models import User
from django.shortcuts import reverse
from django.utils.http import urlquote

from gearfarm.utils.page_path_utils import build_page_path
from farmbase.utils import get_protocol_host
from projects.models import Project, DeliveryDocumentType, ProjectPrototype
from projects.serializers import DeliveryDocumentSerializer, PrototypeCommentPointWithCommentsSerializer
from farmbase.utils import gen_uuid, encrypt_string
from notifications.models import Notification
from notifications.tasks import send_notification, send_document_data
from logs.models import Log


def get_document_filename_and_path(project=None, document_type=None, document=None):
    if document or all([project, document_type]):
        if document:
            project = document.project
            document_type = document.document_type
        filename_template = "《{project_name}》{document_type}.{suffix}"
        filename = filename_template.format(project_name=project.name, document_type=document_type.name,
                                            suffix=document_type.suffix)
        if document_type.number == DeliveryDocumentType.UNCLASSIFIED_DOCUMENT_NUMBER:
            filename = document.filename
        path_template = "{project_document_root}temp/{project_id}/{uuid}-{filename}"
        uuid = gen_uuid()
        path = path_template.format(project_document_root=settings.PROJECT_DOCUMENTS_ROOT, project_id=project.id,
                                    uuid=uuid, filename=filename)
        return filename, path


@shared_task
def create_project_delivery_documents(project_id, user_id):
    user = User.objects.get(pk=user_id)
    project = Project.objects.get(pk=project_id)
    documents_zip_path = None
    notification_content = ''
    result_data = {"result": True, "message": ''}
    try:
        # 需要压缩的文件
        documents = project.delivery_documents.filter(is_deleted=False).exclude(
            document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER)
        # 交付文档对应的document_type
        document_type = DeliveryDocumentType.objects.get(number=DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER)
        documents_zip_filename, documents_zip_path = get_document_filename_and_path(project, document_type)
        documents_zip_path = urlquote(documents_zip_path)
        dir_path = os.path.dirname(documents_zip_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with zipfile.ZipFile(documents_zip_path, 'w', zipfile.ZIP_DEFLATED) as documents_zip:
            for document in documents:
                filename, document_path = get_document_filename_and_path(document=document)
                document_path = urlquote(document_path)
                document_dir_path = os.path.dirname(document_path)
                if not os.path.exists(document_dir_path):
                    os.makedirs(document_dir_path)
                with open(document_path, 'wb') as file:
                    content = document.file.file.read()
                    file.write(content)
                documents_zip.write(document_path, arcname=filename)
                os.remove(document_path)
        file = File(open(documents_zip_path, 'rb'), name=documents_zip_filename)

        data = {"project": project.id, "document_type": document_type.id, "uid": gen_uuid(),
                "filename": documents_zip_filename,
                "file": file, "cipher": gen_uuid()[:6]}
        serializer = DeliveryDocumentSerializer(data=data)
        if serializer.is_valid():
            delivery_document = serializer.save()
            Log.build_create_object_log(user, delivery_document, related_object=project)
            project.delivery_documents.filter(document_type=document_type).exclude(uid=delivery_document.uid).update(
                is_deleted=True)
            notification_content = "项目:{} 交付文档压缩完成".format(project.name)
            result_data = {"result": True, "message": notification_content, "data": serializer.data}
            project.delivery_documents.filter(
                document_type__number=DeliveryDocumentType.DELIVERY_DOCUMENT_NUMBER).exclude(
                pk=delivery_document.id).delete()
        else:
            notification_content = "项目:{} 交付文档压缩失败 错误为{}".format(project.name, serializer.errors)
            result_data = {"result": False, "message": notification_content}
    except Exception as e:
        notification_content = "项目:{} 交付文档压缩失败 可能文件读写中出现问题".format(project.name)
        result_data = {"result": False, "message": notification_content}
        logger = logging.getLogger()
        logger.error(e)
        raise
    finally:
        if documents_zip_path and os.path.exists(documents_zip_path):
            os.remove(documents_zip_path)
        if notification_content:
            notification_url = settings.SITE_URL + build_page_path("project_view", kwargs={"id": project.id},
                                                                   params={"anchor": "documents"})
            notification = Notification.objects.create(user=user, content=notification_content,
                                                       url=notification_url)
            send_notification.delay(user_id, notification.id)
        send_document_data.delay(user_id, result_data)


def unzip_zipfile(zip_src, dst_dir):
    r = zipfile.is_zipfile(zip_src)
    if r:
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        # fz = zipfile.ZipFile(zip_src, 'r')
        # for file in fz.namelist():
        #     fz.extract(file, dst_dir)
        with zipfile.ZipFile(zip_src, 'r') as zip_file:
            for child_file in zip_file.namelist():
                file_name = decode_zipfile_namelist(child_file)
                file_path = dst_dir + file_name
                file_path = file_path.encode()
                if not os.path.exists(os.path.dirname(file_path)):
                    os.makedirs(os.path.dirname(file_path))
                if not os.path.isdir(file_path):
                    with codecs.open(file_path, 'wb') as file:
                        try:
                            content = zip_file.read(child_file)
                            file.write(content)
                        except EOFError:
                            pass


def unzip_prototype_zipfile(zip_src, dst_dir):
    r = zipfile.is_zipfile(zip_src)
    if r:
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        # fz = zipfile.ZipFile(zip_src, 'r')
        # for file in fz.namelist():
        #     fz.extract(file, dst_dir)
        with zipfile.ZipFile(zip_src, 'r') as zip_file:
            decode_namelist = list(map(decode_zipfile_namelist, zip_file.namelist()))
            # 压缩包外边嵌套的空文件夹去除
            commonprefix = ''
            for name in decode_namelist:
                if name.endswith('/index.html'):
                    commonprefix = name.rsplit('index.html', 1)[0]
                    break
            for child_file in zip_file.namelist():
                file_name = decode_zipfile_namelist(child_file)
                if commonprefix and file_name.startswith(commonprefix):
                    file_name = file_name.replace(commonprefix, '', 1)
                file_path = dst_dir + file_name
                file_path = file_path.encode()
                if not os.path.exists(os.path.dirname(file_path)):
                    os.makedirs(os.path.dirname(file_path))
                if not os.path.isdir(file_path):
                    with codecs.open(file_path, 'wb') as file:
                        try:
                            content = zip_file.read(child_file)
                            file.write(content)
                        except EOFError:
                            pass


@shared_task
def unzip_prototype_and_upload_to_oss(prototype_id):
    prototype = ProjectPrototype.objects.get(pk=prototype_id)
    if prototype.oss_url:
        return
    head_pro_link = '''<link type="text/css" href="https://cdn.plugins.chilunyc.com/gear-prototype/gear.prototype.css" rel="Stylesheet" />'''

    body_pro_link = '''<script src="https://cdn.plugins.chilunyc.com/gear-prototype/gear.prototype.min.js"></script>'''
    if settings.STAGING:
        body_pro_link = '''<script src="https://cdn.plugins.chilunyc.com/gear-prototype/gear.prototype.staging.min.js"></script>'''
    elif settings.DEVELOPMENT:
        body_pro_link = '''<script src="https://cdn.plugins.chilunyc.com/gear-prototype/gear.prototype.dev.min.js"></script>'''

    body_pro_link = body_pro_link + '<div class="gear-prototype-mask-screen" id="gear-prototype-mask-screen"></div>'
    zip_src = prototype.prototype_zip_path()
    zip_dir = os.path.dirname(zip_src)
    if not os.path.exists(zip_dir):
        os.makedirs(zip_dir)
    with open(zip_src, 'wb') as file:
        content = prototype.file.file.read()
        file.write(content)
    dst_dir = prototype.prototype_unzip_dir()
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    unzip_prototype_zipfile(zip_src, dst_dir)

    # 给index.html中注入
    for root, dirs, files in os.walk(dst_dir):
        for filename in files:
            if filename.endswith('/index.html') or filename == 'index.html':
                file_path = os.path.join(root, filename)
                content = ''
                with open(file_path, 'r') as current_file:
                    content = current_file.read()
                    head_post = content.find('</head>')
                    if head_post != -1:
                        content = content[:head_post] + head_pro_link + content[head_post:]
                    body_post = content.rfind('</body>')
                    if body_post != -1:
                        content = content[:body_post] + body_pro_link + content[body_post:]
                with open(file_path, 'w') as write_file:
                    write_file.write(content)
            elif filename.endswith('resources/scripts/axure/events.js'):
                file_path = os.path.join(root, filename)
                content = ''
                with open(file_path, 'r') as current_file:
                    content = current_file.read()
                    content = content.replace("$ax.messageCenter.postMessage('previousPage');", '')
                    content = content.replace("$ax.messageCenter.postMessage('nextPage');", '')
                with open(file_path, 'w') as write_file:
                    write_file.write(content)

    ossutil_config_path = settings.BASE_DIR + '/ossutil/ossutilconfig.txt'
    if not os.path.exists(ossutil_config_path):
        with open(ossutil_config_path, 'w') as config_file:
            config_content = '''[Credentials]
    language=CH
    accessKeyID={oss_key_id}
    accessKeySecret={oss_key_secret}
    endpoint={oss_endpoint}'''.format(oss_key_id=settings.PROTOTYPE_OSS_ACCESS_KEY_ID,
                                      oss_key_secret=settings.PROTOTYPE_OSS_ACCESS_KEY_SECRET,
                                      oss_endpoint=settings.PROTOTYPE_OSS_ENDPOINT)
            config_file.write(config_content)

    ossutil_path = "{base_dir}/ossutil/{ossutil}".format(
        ossutil='ossutilmac64' if settings.DEVELOPMENT else 'ossutil64',
        base_dir=settings.BASE_DIR)
    os.system("chmod 755 {ossutil_path}".format(ossutil_path=ossutil_path))
    upload_cmd = "{ossutil_path} -c {base_dir}/ossutil/ossutilconfig.txt  cp -r {prototype_dir} oss://{oss_prototype_bucket}/{prototype_uid}/ -u".format(
        ossutil_path=ossutil_path,
        base_dir=settings.BASE_DIR,
        prototype_dir=dst_dir,
        oss_prototype_bucket=settings.PROTOTYPE_OSS_BUCKET,
        prototype_uid=prototype.uid
    )
    os.system(upload_cmd)
    prototype.oss_url = settings.GEAR_PROTOTYPE_SITE_URL + '/{prototype_uid}/'.format(prototype_uid=prototype.uid)
    prototype.save()

    shutil.rmtree(dst_dir, True)
    if os.path.isfile(zip_src):
        os.remove(zip_src)


# @shared_task
# def unzip_prototype_file(prototype_id):
#     prototype = ProjectPrototype.objects.get(pk=prototype_id)
#     head_pro_link = '''<link rel="stylesheet" href="/static/projects/styles/prototype_comments.css">'''.encode()
#     body_pro_link = '''<script src="/static/projects/scripts/gear_prototypes.js?v=2.0830"></script>'''.encode()
#     if not prototype.index_path or not os.path.isfile(
#             prototype.index_path.replace(settings.PROTOTYPE_URL, settings.PROTOTYPE_ROOT, 1).encode()):
#         if not os.path.exists(prototype.prototype_dir()):
#             os.makedirs(prototype.prototype_dir())
#         prototype_file_path = prototype.prototype_zip_path()
#         with open(prototype_file_path, 'wb') as file:
#             content = prototype.file.file.read()
#             file.write(content)
#
#         with zipfile.ZipFile(prototype_file_path, 'r') as prototype_zip:
#             decode_namelist = list(map(decode_zipfile_namelist, prototype_zip.namelist()))
#             commonprefix = ''
#             for name in decode_namelist:
#                 if name.endswith('/index.html'):
#                     commonprefix = name.rsplit('index.html', 1)[0]
#                     break
#             for zip_file in prototype_zip.namelist():
#                 file_name = decode_zipfile_namelist(zip_file)
#                 if commonprefix and file_name.startswith(commonprefix):
#                     file_name = file_name.replace(commonprefix, '', 1)
#                 file_path = prototype.prototype_dir() + file_name
#                 file_path = file_path.encode()
#                 if not os.path.exists(os.path.dirname(file_path)):
#                     os.makedirs(os.path.dirname(file_path))
#                 if not os.path.isdir(file_path):
#                     with codecs.open(file_path, 'wb') as file:
#                         try:
#                             content = prototype_zip.read(zip_file)
#                             if file_name.endswith('/index.html') or file_name == 'index.html':
#                                 prototype.index_path = settings.PROTOTYPE_URL + encrypt_string(
#                                     prototype.uid)[:16] + '/' + file_name
#                                 prototype.save()
#                                 head_post = content.find(b'</head>')
#                                 if head_post != -1:
#                                     content = content[:head_post] + head_pro_link + content[head_post:]
#                                 body_post = content.rfind(b'</body>')
#                                 if body_post != -1:
#                                     content = content[:body_post] + body_pro_link + content[body_post:]
#                             if file_name.endswith('resources/scripts/axure/events.js'):
#                                 content = content.replace(b"$ax.messageCenter.postMessage('previousPage');", b'')
#                                 content = content.replace(b"$ax.messageCenter.postMessage('nextPage');", b'')
#                             file.write(content)
#                         except EOFError:
#                             pass
#

@shared_task
def create_prototype_comment_point_cache_data(prototype_id):
    prototype = ProjectPrototype.objects.get(pk=prototype_id)
    statistical_data = {}
    comment_points = prototype.comment_points.filter(comments__isnull=False).distinct()
    prototype.comment_points.filter(comments__isnull=True).delete()
    data = PrototypeCommentPointWithCommentsSerializer(comment_points, many=True).data
    for comment_point in data:
        if len(comment_point['comments']):
            node_url = comment_point.get('page_name')
            if node_url:
                if node_url not in statistical_data:
                    statistical_data[node_url] = {'point_num': 0, 'comment_num': 0, 'node_url': node_url}
                statistical_data[node_url]['point_num'] += 1
                statistical_data[node_url]['comment_num'] += len(comment_point['comments'])
    cache.set('prototype-{}-comments'.format(prototype.uid), statistical_data, None)


@shared_task
def create_prototype_client_comment_point_cache_data(prototype_id):
    prototype = ProjectPrototype.objects.get(pk=prototype_id)
    statistical_data = {}
    comment_points = prototype.comment_points.filter(creator__client_id__isnull=False).filter(
        comments__isnull=False).distinct()
    prototype.comment_points.filter(comments__isnull=True).delete()
    data = PrototypeCommentPointWithCommentsSerializer(comment_points, many=True).data
    for comment_point in data:
        if len(comment_point['comments']):
            node_url = comment_point.get('page_name')
            if node_url:
                if node_url not in statistical_data:
                    statistical_data[node_url] = {'point_num': 0, 'comment_num': 0, 'node_url': node_url}
                statistical_data[node_url]['point_num'] += 1
                statistical_data[node_url]['comment_num'] += len(comment_point['comments'])
    cache.set('prototype-{}-client-comments'.format(prototype.uid), statistical_data, None)


@shared_task
def create_prototype_developer_comment_point_cache_data(prototype_id):
    prototype = ProjectPrototype.objects.get(pk=prototype_id)
    statistical_data = {}
    comment_points = prototype.comment_points.exclude(creator__client_id__isnull=False).filter(
        comments__isnull=False).distinct()
    prototype.comment_points.filter(comments__isnull=True).delete()
    data = PrototypeCommentPointWithCommentsSerializer(comment_points, many=True).data
    for comment_point in data:
        if len(comment_point['comments']):
            node_url = comment_point.get('page_name')
            if node_url:
                if node_url not in statistical_data:
                    statistical_data[node_url] = {'point_num': 0, 'comment_num': 0, 'node_url': node_url}
                statistical_data[node_url]['point_num'] += 1
                statistical_data[node_url]['comment_num'] += len(comment_point['comments'])
    cache.set('prototype-{}-developer-comments'.format(prototype.uid), statistical_data, None)


def decode_zipfile_namelist(file_name):
    try:
        file_name = file_name.encode('cp437').decode('utf-8')
    except:
        try:
            file_name = file_name.encode('cp437').decode('gbk')
        except:
            pass
    return file_name
