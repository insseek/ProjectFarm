from django.urls import path

from . import api
import projects.api

app_name = 'proposals_api'
urlpatterns = [
    path(r'', api.ProposalList.as_view(), name='list'),
    path(r'filter_data', api.proposal_filter_data, name='filter_data'),
    path(r'ongoing', api.ongoing_proposals, name='ongoing_proposals'),
    path(r'closed', api.closed_proposals, name='closed_proposals'),
    path(r'mobile/list', api.mobile_proposal_list, {'is_mine': False}, name='mobile_proposal_list'),
    path(r'mobile/list/mine', api.mobile_proposal_list, {'is_mine': True}, name='mine_mobile_proposal_list'),

    path(r'mine', api.MyProposalList.as_view(), name='my_proposals'),
    path(r'mine/ongoing', api.my_ongoing_proposals, name='my_ongoing_proposals'),
    path(r'mine/closed', api.my_closed_proposals, name='my_closed_proposals'),
    path(r'mine/submitted_proposals', api.my_submitted_proposals, name='my_submitted_proposals'),

    path(r'<int:id>', api.ProposalDetail.as_view(), name='detail'),
    path(r'<int:id>/assign', api.assign, name='assign'),
    path(r'<int:id>/reassign', api.reassign, name="reassign"),
    path(r'<int:id>/name', api.proposal_name, name="name"),
    path(r'<int:id>/reliability', api.proposal_reliability, name="reliability"),
    path(r'<int:proposal_id>/members', api.ProposalMemberList.as_view(), name="proposal_members"),

    path(r'<int:id>/contact', api.contact, name='contact'),
    path(r'<int:id>/report', api.report_request, name='report_request'),
    path(r'<int:id>/nodeal', api.nodeal, name='nodeal'),
    path(r'<int:id>/open', api.open_proposal, name='open_proposal'),
    path(r'<int:proposal_id>/create_project', projects.api.ProjectList.as_view(), name='create_project'),

    path(r'<int:proposal_id>/reports', api.proposal_reports, name="reports"),

    path(r'<int:proposal_id>/latest_report', api.proposal_latest_report, name="latest_report"),
    path(r'<int:proposal_id>/latest_report/tags', api.proposal_latest_report_tags, name="latest_report_tags"),

    path(r'<int:proposal_id>/biz_opp', api.BusinessOpportunityList.as_view(),
         name="proposal_biz_opportunity"),
    path(r'biz_opps', api.BusinessOpportunityList.as_view(),
         name="all_biz_opportunities"),
    path(r'sources', api.get_proposal_source_data,
         name="proposal_sources"),
    path(r'<int:proposal_id>/call_records', api.ProposalCallRecordList.as_view(), name="call_records"),
    path(r'call_records/<int:call_record_id>', api.ProposalCallRecordDetail.as_view(), name="call_record_detail"),

    path(r'<int:proposal_id>/handover_receipt', api.HandoverReceiptList.as_view(), name="handover_receipt"),

    path(r'quip_folders', api.quip_folders, name="quip_folders"),
]
