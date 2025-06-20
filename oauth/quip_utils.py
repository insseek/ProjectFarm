import json
import time

from django.conf import settings
from django.core.cache import cache
from tenacity import retry, wait_fixed, stop_after_attempt

from oauth.quip import QuipClient

# from oauth.project_quip_folder_template import project_template_data
import logging

logger = logging.getLogger()

client = QuipClient(settings.QUIP_TOKEN)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_folder(id):
    return client.get_folder(id)


def get_quip_doc_simple_data(folder):
    return {
        'title': folder['title'],
        'id': folder['id'],
        "type": folder['type'],
        "link": folder['link'] if folder.get('link', None) else 'https://quip.com/' + folder['id'],
    }


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_thread_data(thread_id):
    thread_data = client.get_thread(thread_id)
    return thread_data


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_folder_deep_data(id):
    folder_data = get_folder(id)
    if 'children' in folder_data:
        children = folder_data['children']
        for child_index, child in enumerate(children):
            if "thread_id" in child:
                thread_id = child['thread_id']
                thread_data = get_thread_data(thread_id)
                children[child_index] = {"thread": get_quip_doc_simple_data(thread_data['thread'])}
            if "folder_id" in child:
                folder_id = child['folder_id']
                children[child_index] = get_folder_deep_data(folder_id)
    return folder_data


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def create_quip_folder(title, parent_id):
    folder_data = client.new_folder(title, parent_id=parent_id)
    return folder_data


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def copy_document_to_folder(thread_id, folder_id, title=None):
    document_data = client.copy_document(thread_id, folder_ids=[folder_id, ], title=title)
    return document_data


def new_folder_from_template(template, parent_id, title=None):
    if template:
        top_folder_title = title or template['folder']['title']
        new_folder_data = create_quip_folder(top_folder_title, parent_id)
        new_folder_id = new_folder_data['folder']['id']
        if 'children' in template:
            for child in template['children']:
                if 'thread' in child:
                    template_thread_id = child['thread']['id']
                    copy_document_to_folder(template_thread_id, new_folder_id)
                elif 'folder' in child:
                    folder_title = child['folder']['title']
                    folder_data = new_folder_from_template(child, new_folder_id)
                    if folder_title.lower().strip() == 'tpm产出物':
                        new_folder_data['quip_tpm_folder_id'] = folder_data['folder']['id']
        return new_folder_data


def new_project_folder(project, title=None):
    title = title or project.name
    template = get_project_quip_folder_template()
    parent_id = settings.QUIP_PROJECT_FOLDER_ID
    folder_data = new_folder_from_template(template, parent_id, title)
    return folder_data


def new_project_engineer_contact_folder(project, title=None):
    title = title or project.name
    parent_id = settings.QUIP_PROJECT_ENGINEER_FOLDER_ID
    folder_data = create_quip_folder(title, parent_id)
    return folder_data


@retry(stop=stop_after_attempt(3))
def get_project_quip_folder_template(rebuild=False):
    template_data = cache.get('quip_project_folder_template_data', None)
    if not template_data or rebuild:
        template_data = get_folder_deep_data(settings.QUIP_PROJECT_FOLDER_TEMPLATE_ID)
        cache.set('quip_project_folder_template_data', template_data, None)
        return template_data
        # if template_data:
        #     with open('oauth/project_quip_folder_template.py', 'w') as template_file:
        #         content = 'project_template_data=' + json.dumps(template_data, ensure_ascii=False)
        #         template_file.write(content)
    return template_data


def get_folders_docs(folder_ids: list):
    if isinstance(folder_ids, str) or isinstance(folder_ids, int):
        folder_ids = [folder_ids, ]
    folders = client.get_folders(folder_ids)

    docs = []
    child_folder_ids = []
    child_thread_ids = []
    for folder_data in folders.values():
        for child in folder_data["children"]:
            if "thread_id" in child:
                child_thread_ids.append(child["thread_id"])
            if "folder_id" in child:
                child_folder_ids.append(child["folder_id"])
    if child_thread_ids:
        threads = client.get_threads(child_thread_ids)
        docs.extend([clean_quip_doc_data(folder['thread']) for folder in threads.values()])

    if child_folder_ids:
        child_folders_docs = get_folders_docs(child_folder_ids)
        docs.extend(child_folders_docs)
    return docs


def get_quip_doc_html(thread_id):
    data = client.get_thread(thread_id)
    return data['html']


def get_quip_doc(thread_id):
    data = client.get_thread(thread_id)
    return data


def clean_quip_doc_data(folder):
    return {
        'title': folder['title'],
        'link': folder['link'] if folder.get('link') else 'https://quip.com/' + folder['id'],
        'id': folder['id'],
        'updated_usec': folder.get('updated_usec') or None,
        'created_usec': folder.get('created_usec') or None,
        'updated_at': change_quip_timestamp_to_str(folder.get('updated_usec')),
        'created_at': change_quip_timestamp_to_str(folder.get('created_usec')),
    }


def change_quip_timestamp_to_str(timestamp):
    if timestamp:
        short_timestamp = int(str(timestamp)[:10])
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(short_timestamp))
