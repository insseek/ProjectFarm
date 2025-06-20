# -*- coding:utf-8 -*-
from files.models import File
from files.serializers import FileSerializer
from django.core.files import File as DjangoFile


def handle_obj_files(obj, request):
    file_list = request.data.pop('files', None)
    if file_list is not None and not file_list:
        obj.files.update(is_deleted=True)
    elif file_list:
        add_files_to_object(obj, file_list)


def add_files_to_object(proposal, file_list):
    if file_list:
        old_files = [file.id for file in proposal.files.all()]
        new_file_ids = list(set(file_list) - set(old_files))
        new_files = File.objects.filter(id__in=new_file_ids)
        deleted_file_ids = list(set(old_files) - set(file_list))
        File.objects.filter(id__in=deleted_file_ids).update(is_deleted=True)
        for file in new_files:
            if file.content_object:
                filed_file = DjangoFile(file.file, name=file.filename)
                file_data = {'filename': file.filename, 'file': filed_file}
                file_serializer = FileSerializer(data=file_data)
                if file_serializer.is_valid():
                    new_file = file_serializer.save()
                    new_file.content_object = proposal
                    new_file.save()
                continue
            file.content_object = proposal
            file.save()
