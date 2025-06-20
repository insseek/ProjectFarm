from django.urls import path

from . import api

app_name = 'prototypes_api'
urlpatterns = [
    path(r'', api.PrototypeReferenceList.as_view(), name='list'),
    path(r'filter_data', api.prototype_reference_filter_data, name='filter_data'),
    path(r'batch_upload', api.batch_upload_prototype_references,
         name='batch_upload_prototype_references'),
    path(r'collections/<int:id>', api.PrototypeCollectionDetail.as_view(), name='collection_detail'),
    path(r'<int:id>', api.PrototypeReferenceDetail.as_view(), name='detail'),
    path(r'<int:id>/tags', api.prototype_reference_tags, name='prototype_reference_tags'),
    path(r'collections/<int:collection_id>/add', api.batch_upload_prototype_references,
         name='add_references_to_collection'),
]
