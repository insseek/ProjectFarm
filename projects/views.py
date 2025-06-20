from django.shortcuts import render, redirect
from django.conf import settings

from projects.models import DeliveryDocument


def download_documents(request, uid):
    document = DeliveryDocument.objects.filter(uid=uid, is_deleted=False).first()
    if not document:
        return render(request, "projects/delivery_document_400.html",
                      {"title": "交付文档", "message": "链接失效，您所下载的交付文档不存在或已更新至最新链接"})
    return render(request, "projects/delivery_document_download.html",
                  {"title": "交付文档下载", "uid": uid, "message": "请输入密码"})


def calendar_view(request, uid):
    return redirect(settings.REPORTS_HOST + "/projects/calendars/detail/?uid={}".format(uid))
