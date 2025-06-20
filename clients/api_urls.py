from django.urls import path

from . import api
from proposals.api import ProposalList

app_name = 'clients_api'
urlpatterns = [
    path(r'', api.ClientList.as_view(), name='list'),
    path(r'<int:id>', api.ClientDetail.as_view(), name='client_detail'),
    path(r'<int:client_id>/one_time/authentication_key', api.one_time_authentication_key,
         name='client_one_time_authentication_key'),
    path(r'projects/<int:project_id>/add', api.add_project_client, name='add_project_client'),
    path(r'phone/check', api.client_phone_check, name='client_phone_check'),
    path(r'organizations', api.client_organizations, name='client_organizations'),

    path(r'leads/create', api.LeadList.as_view(), name='create_lead'),
    path(r'leads', api.LeadList.as_view(), {'is_mine': False}, name='leads'),
    path(r'leads/salesmen/<int:user_id>', api.salesman_leads, name='salesman_leads'),
    path(r'leads/mine', api.LeadList.as_view(), {'is_mine': True}, name='my_leads'),
    path(r'leads/filter_data', api.leads_filter_data, name='filter_data'),
    path(r'leads/sources', api.leads_sources, name='leads_sources'),

    path(r'leads/phone/check', api.leads_phone_check, name='leads_phone_check'),
    path(r'leads/<int:lead_id>', api.LeadDetail.as_view(), name='lead_detail'),
    path(r'leads/<int:lead_id>/edit', api.LeadList.as_view(), name='lead_edit'),
    path(r'leads/<int:lead_id>/reassign', api.lead_reassign, name="lead_reassign"),
    path(r'leads/batch_reassign', api.lead_batch_reassign, name="lead_batch_reassign"),

    path(r'leads/<int:lead_id>/close', api.close_lead, name='close_lead'),
    path(r'leads/<int:lead_id>/close/apply', api.apply_close_lead, name='apply_close_lead'),
    path(r'leads/<int:lead_id>/close/confirm', api.confirm_close_lead, name='confirm_close_lead'),

    path(r'leads/<int:lead_id>/open', api.open_lead, name='open_lead'),
    path(r'leads/<int:lead_id>/perfect', api.perfect_fields, name='lead_perfect_fields'),

    path(r'leads/<int:lead_id>/check', api.check_required_fields, name='lead_check_required_fields'),

    path(r'leads/<int:lead_id>/create_proposal', ProposalList.as_view(), name='lead_create_proposal'),

    path(r'leads/<int:lead_id>/requirement', api.LeadRequirement.as_view(), name='lead_requirement'),

    path(r'leads/<int:lead_id>/punch_records', api.LeadPunchRecordList.as_view(), name='lead_punch_records'),
    path(r'leads/<int:lead_id>/latest_punch_record', api.lead_latest_punch_record, name="lead_latest_punch_record"),

    path(r'leads/<int:lead_id>/report_files', api.LeadReportFileList.as_view(), name="lead_report_files"),
    path(r'leads/report_files/<int:report_file_id>', api.LeadReportFileDetail.as_view(), name="lead_report_file"),

    path(r'leads/<int:lead_id>/reports', api.lead_reports, name="lead_reports"),
    path(r'leads/<int:lead_id>/latest_report', api.lead_latest_report, name="lead_latest_report"),

    path(r'leads/<int:lead_id>/latest_report/tags', api.lead_latest_report_tags, name="lead_latest_report_tags"),

    path(r'leads/<int:lead_id>/quotations', api.LeadQuotationList.as_view(), name='lead_quotations'),
    path(r'leads/<int:lead_id>/latest_quotation', api.lead_latest_quotation, name="lead_latest_quotation"),
    path(r'leads/quotations/<int:id>', api.LeadQuotationDetail.as_view(), name='lead_quotation_detail'),
    path(r'leads/quotations/<int:id>/quote', api.lead_quotation_quote, name='lead_quotation_quote'),
    path(r'leads/quotations/<int:id>/reject', api.lead_quotation_reject, name='lead_quotation_reject'),
    path(r'leads/quotations', api.all_leads_quotations, name='all_leads_quotations'),

    path(r'leads/quotations/mine', api.my_leads_quotations, name='my_leads_quotations'),

    path(r'leads/quotations/filter_data', api.leads_quotations_filter_data, name='leads_quotations_filter_data'),

    path(r'leads/track_file_template/download', api.download_sem_track_template, name="download_sem_track_template"),

    path(r'leads/track_file/upload', api.sem_track_file_upload, name="sem_track_file_upload"),
    path(r'leads/track_file/<int:track_id>/download', api.sem_track_file_download, name="sem_track_file_download"),

    path(r'leads/sem_leads/download', api.sem_leads_download, name="sem_leads_download"),
    path(r'leads/sem/filter_data', api.sem_leads_filter_data, name='sem_filter_data'),
    path(r'leads/conversion_rate', api.leads_conversion_rate, name="leads_conversion_rate"),
    path(r'leads/conversion_rate/monthly', api.leads_conversion_rate_monthly, name="leads_conversion_rate_monthly"),

    # 移动端飞书
    # 我的进行中的线索
    path(r'leads/ongoing/mine', api.my_ongoing_leads, name='my_ongoing_leads'),
    path(r'leads/punch_leads/mine', api.recent_punch_leads, name='recent_punch_leads'),
    path(r'leads/punch_records/mine/recent', api.my_recent_punch_records, name='my_recent_punch_records'),
    path(r'leads/<int:lead_id>/punch_records/recent', api.lead_recent_punch_records, name='lead_recent_punch_records'),

    path(r'data/migrate', api.data_migrate, name="data_migrate"),

]
