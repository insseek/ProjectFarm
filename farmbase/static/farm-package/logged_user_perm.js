function checkCurrentUserPermData() {
    if (typeof loggedUser == "undefined" || window.loggedUser == undefined) {
        setSyncCurrentUserPermData()
    }
}

function setSyncCurrentUserPermData() {
    let url = '/api/users/me/perms';
    commonSyncRequest('get', url, null, function (data) {
        if (data.result) {
            window.loggedUser = data.data;
        }
    })
}

checkCurrentUserPermData();

function hasFuncPerms(perms) {
    let permList = perms;
    if (typeof perms == 'string') {
        permList = [perms]
    }
    if (typeof loggedUser == "undefined" && window.loggedUser == undefined) {
        setSyncCurrentUserPermData()
    }
    let permData = loggedUser ? loggedUser : window.loggedUser;
    if (permData) {
        if (permData.is_superuser) {
            return true
        } else {
            return permList.every(function (item, index, array) {
                return permData.perms.includes(item)
            });
        }
    }
    return false
}

function hasAnyFuncPerms(perms) {
    let permList = perms;
    if (typeof perms == 'string') {
        permList = [perms]
    }
    if (typeof loggedUser == "undefined" && window.loggedUser == undefined) {
        setSyncCurrentUserPermData()
    }
    let permData = loggedUser ? loggedUser : window.loggedUser;
    if (permData) {
        if (permData.is_superuser) {
            return true
        } else {
            return permList.some(function (item, index, array) {
                return permData.perms.includes(item)
            });
        }
    }
    return false
}
const GROUP_NAME_DICT = {
    "project_manager": "项目经理",
    "pm": '产品经理',
    "learning_pm": '培训产品经理',
    "tpm": 'TPM',
    "remote_tpm": "远程TPM",
    "finance": '财务',
    "test": '测试',
    // "csm": '客户成功',
    "bd": "BD",
    "designer": "设计",
    "marketing": "市场",
    "sem": 'SEM'
}
// loggedUser的示例
const USER_PERM_DATA_TEMP = {
    "username": "唐海鹏",
    "id": 13,
    "groups": ["产品经理"],
    "perms": ["view_ongoing_proposals", "track_project_development", "view_project_job_positions", "view_calculator", "view_test_gantt_chart", "view_all_reports", "use_voice_call", "view_my_projects_job_payments", "use_farm_email", "view_my_project_payments", "view_all_prototype_references", "view_projects_finished_in_60_days", "view_all_proposals", "view_project_prototypes", "view_all_developer_id_card_info", "create_proposal", "view_all_project_gantt_charts", "view_all_developers", "view_all_projects", "create_project", "view_ongoing_projects_payments", "view_ongoing_projects_contracts", "view_project_calendar", "view_project_deployment_servers", "view_tpm_work_orders", "view_project_playbook", "view_ongoing_projects", "delete_prototype_references", "view_my_project_position_needs", "view_proposals_finished_in_90_days", "view_all_call_records", "view_proposal_playbook", "create_prototype_reference", "view_all_project_position_needs", "view_unassigned_proposals", "view_design_gantt_chart", "update_project_all_checkpoints", "view_all_proposal_biz_opportunities", "view_report_frame_diagrams", "view_projects_and_proposals_statistical_data", "download_call_records", "view_pm_statistical_data", "view_project_capacity_data"],
    "is_superuser": false, //是否超级管理员
    "is_sem": false, //是否SEM
    "is_learning_pm": false, //是否培训产品经理
    "is_pm": true,//是否产品经理
    "is_bd": false, //是否BD
    "is_marketing": false, //是否市场
    // "is_csm": false,//是否客户成功
    "is_finance": false, //是否财务
    "is_tpm": false, //是否TPM
    "is_designer": false, //是否设计
    "is_test": false,//是否测试
};