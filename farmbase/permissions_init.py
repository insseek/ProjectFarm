from django.contrib.auth.models import User, Group
from farmbase.models import FunctionModule, FunctionPermission

# 这里维护的数据   每次部署会创建新增加你的权限   groups是无效的只是为了阅读方便 不会重重（因为后台可以手动配置）
# python manage.py rebuild_permissions_from_init_data
# 肯定生命 进步超越。
# 极简是什么？生命存在意志之外所有精神可弃绝  保证生命存在的物质之外所有物质可弃绝
FUNC_PERMS = [
    {
        "func_perms": [
            {
                "name": "需求分配",
                "codename": "assign_proposals",
                "groups": []
            },
            {
                "name": "创建新需求",
                "codename": "create_proposal",
                "groups": [
                    "BD",
                    "TPM",
                    "培训产品经理",
                    "项目经理",
                    "市场",
                    "产品经理"
                ]
            },
            {
                "name": "编辑需求",
                "codename": "edit_proposal",
                "groups": [
                    "产品经理",
                    "项目经理",
                    "市场",
                    "BD",
                    "培训产品经理",
                    "TPM"
                ]
            },
            {
                "name": "需求.认领需求",
                "codename": "proposals.be_proposal_product_manager",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看需求商机列表",
                "codename": "view_all_proposal_biz_opportunities",
                "groups": [
                    "BD",
                    "SEM"
                ]
            },
            {
                "name": "查看全部需求",
                "codename": "view_all_proposals",
                "groups": []
            },
            {
                "name": "查看需求报价计算器",
                "codename": "view_calculator",
                "groups": [
                    "项目经理",
                    "培训产品经理",
                    "TPM",
                    "产品经理",
                    "BD"
                ]
            },
            {
                "name": "查看我的需求列表",
                "codename": "view_my_proposals",
                "groups": [
                    "BD",
                    "培训产品经理",
                    "项目经理",
                    "产品经理",
                    "市场"
                ]
            },
            {
                "name": "查看进行中的需求",
                "codename": "view_ongoing_proposals",
                "groups": [
                    "设计",
                    "产品经理",
                    "市场",
                    "培训产品经理",
                    "TPM",
                    "SEM",
                    "项目经理"
                ]
            },
            {
                "name": "查看需求交接清单",
                "codename": "view_proposal_handover_receipt",
                "groups": [
                    "产品经理",
                    "项目经理",
                    "BD",
                    "设计",
                    "培训产品经理"
                ]
            },
            {
                "name": "查看最近90天内结束的需求",
                "codename": "view_proposals_finished_in_90_days",
                "groups": [
                    "设计",
                    "BD",
                    "产品经理",
                    "市场",
                    "培训产品经理",
                    "TPM",
                    "SEM",
                    "项目经理"
                ]
            },
            {
                "name": "查看等待认领的需求",
                "codename": "view_unassigned_proposals",
                "groups": [
                    "培训产品经理",
                    "市场",
                    "产品经理",
                    "项目经理"
                ]
            }
        ],
        "func_module": {
            "name": "需求",
            "codename": "proposals"
        },
        "name": "需求",
        "codename": "proposals"
    },
    {
        "func_perms": [
            {
                "name": "克隆需求报告",
                "codename": "clone_proposal_report",
                "groups": [
                    "培训产品经理",
                    "产品经理",
                    "项目经理",
                    "BD"
                ]
            },
            {
                "name": "新增需求报告",
                "codename": "create_proposal_report",
                "groups": [
                    "培训产品经理",
                    "产品经理",
                    "BD",
                    "项目经理"
                ]
            },
            {
                "name": "发布需求报告无需审核",
                "codename": "publish_proposal_report",
                "groups": []
            },
            {
                "name": "发布需求报告需审核",
                "codename": "publish_proposal_report_review_required",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看全部报告",
                "codename": "view_all_reports",
                "groups": [
                    "产品经理",
                    "项目经理",
                    "培训产品经理",
                    "BD"
                ]
            },
            {
                "name": "查看报告框架图列表",
                "codename": "view_report_frame_diagrams",
                "groups": [
                    "培训产品经理",
                    "项目经理",
                    "产品经理",
                    "BD"
                ]
            }
        ],
        "func_module": {
            "name": "报告",
            "codename": "reports"
        },
        "name": "报告",
        "codename": "reports"
    },
    {
        "func_perms": [
            {
                "name": "为全部项目的职位需求添加候选人",
                "codename": "add_candidates_for_all_project_job_position_needs",
                "groups": [
                    "TPM"
                ]
            },
            {
                "name": "创建新项目",
                "codename": "create_project",
                "groups": [
                    "BD",
                    "TPM",
                    "培训产品经理",
                    "市场",
                    "产品经理",
                    "项目经理"
                ]
            },
            {
                "name": "创建所有项目客户日程计划",
                "codename": "create_project_calendar",
                "groups": []
            },
            {
                "name": "编辑项目",
                "codename": "edit_project",
                "groups": []
            },
            {
                "name": "管理全部项目的日程计划",
                "codename": "manage_all_project_calendars",
                "groups": []
            },
            {
                "name": "管理全部项目的交付文档",
                "codename": "manage_all_project_delivery_documents",
                "groups": []
            },
            {
                "name": "管理全部项目的职位需求",
                "codename": "manage_all_project_job_position_needs",
                "groups": []
            },
            {
                "name": "管理全部项目的开发职位",
                "codename": "manage_all_project_job_positions",
                "groups": []
            },
            {
                "name": "管理全部项目的项目收款",
                "codename": "manage_all_project_payments",
                "groups": []
            },
            {
                "name": "管理全部项目的项目原型",
                "codename": "manage_all_project_prototypes",
                "groups": []
            },
            {
                "name": "管理全部项目的工时计划",
                "codename": "manage_all_project_work_hour_plans",
                "groups": []
            },
            {
                "name": "管理全部项目的工时记录",
                "codename": "manage_all_project_work_hour_records",
                "groups": []
            },
            {
                "name": "管理我的项目的日程计划",
                "codename": "manage_my_project_calendars",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "管理我的项目的交付文档",
                "codename": "manage_my_project_delivery_documents",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "管理我的项目的职位需求",
                "codename": "manage_my_project_job_position_needs",
                "groups": [
                    "项目经理",
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "管理我的项目的开发职位",
                "codename": "manage_my_project_job_positions",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "管理我的项目的项目收款",
                "codename": "manage_my_project_payments",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "管理我的项目的项目原型",
                "codename": "manage_my_project_prototypes",
                "groups": [
                    "产品经理",
                    "项目经理",
                    "培训产品经理",
                    "设计"
                ]
            },
            {
                "name": "管理我的项目的工时计划",
                "codename": "manage_my_project_work_hour_plans",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "管理我的项目的工时记录",
                "codename": "manage_my_project_work_hour_records",
                "groups": [
                    "培训产品经理",
                    "TPM",
                    "测试",
                    "产品经理",
                    "设计",
                    "项目经理",
                    "远程TPM"
                ]
            },
            {
                "name": "项目代码提交管理",
                "codename": "manage_projects_gitlab_committers",
                "groups": [
                    "TPM",
                    "项目经理"
                ]
            },
            {
                "name": "给成单交接的需求分配项目经理",
                "codename": "reassign_project_manager_for_proposal",
                "groups": []
            },
            {
                "name": "项目监督",
                "codename": "track_project_development",
                "groups": [
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "测试",
                    "设计",
                    "项目经理"
                ]
            },
            {
                "name": "一键更新项目所有检查点",
                "codename": "update_project_all_checkpoints",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "查看全部项目的日程计划",
                "codename": "view_all_project_calendars",
                "groups": []
            },
            {
                "name": "查看全部项目的项目合同",
                "codename": "view_all_project_contracts",
                "groups": []
            },
            {
                "name": "查看全部项目的交付文档",
                "codename": "view_all_project_delivery_documents",
                "groups": []
            },
            {
                "name": "查看全部项目工程师文档",
                "codename": "view_all_project_developers_documents",
                "groups": [
                    "TPM",
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "远程TPM"
                ]
            },
            {
                "name": "查看全部项目的邮件记录",
                "codename": "view_all_project_emails",
                "groups": []
            },
            {
                "name": "查看全部项目的甘特图",
                "codename": "view_all_project_gantt_charts",
                "groups": [
                    "测试",
                    "培训产品经理",
                    "TPM",
                    "产品经理",
                    "设计",
                    "项目经理"
                ]
            },
            {
                "name": "查看全部项目的职位需求",
                "codename": "view_all_project_job_position_needs",
                "groups": [
                    "TPM"
                ]
            },
            {
                "name": "查看全部项目的开发职位",
                "codename": "view_all_project_job_positions",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "查看全部项目的项目收款",
                "codename": "view_all_project_payments",
                "groups": []
            },
            {
                "name": "查看所有项目的项目原型",
                "codename": "view_all_project_prototypes",
                "groups": [
                    "TPM",
                    "培训产品经理",
                    "项目经理",
                    "测试",
                    "产品经理",
                    "设计",
                    "远程TPM",
                    "BD"
                ]
            },
            {
                "name": "查看全部项目",
                "codename": "view_all_projects",
                "groups": [
                    "产品经理",
                    "项目经理"
                ]
            },
            {
                "name": "查看项目工程师款项",
                "codename": "view_dev_table",
                "groups": []
            },
            {
                "name": "查看我的项目的日程计划",
                "codename": "view_my_project_calendars",
                "groups": [
                    "BD",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的项目的项目合同",
                "codename": "view_my_project_contracts",
                "groups": [
                    "BD",
                    "培训产品经理",
                    "产品经理",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的项目的交付文档",
                "codename": "view_my_project_delivery_documents",
                "groups": [
                    "TPM",
                    "远程TPM",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的项目工程师文档",
                "codename": "view_my_project_developers_documents",
                "groups": [
                    "产品经理",
                    "项目经理",
                    "远程TPM",
                    "TPM",
                    "培训产品经理"
                ]
            },
            {
                "name": "查看我的项目的邮件记录",
                "codename": "view_my_project_emails",
                "groups": [
                    "BD",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的项目的甘特图",
                "codename": "view_my_project_gantt_charts",
                "groups": [
                    "TPM",
                    "培训产品经理",
                    "设计",
                    "远程TPM",
                    "产品经理",
                    "测试",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的项目的职位需求",
                "codename": "view_my_project_job_position_needs",
                "groups": [
                    "项目经理",
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看我的项目的开发职位",
                "codename": "view_my_project_job_positions",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "测试",
                    "远程TPM",
                    "TPM",
                    "培训产品经理",
                    "设计"
                ]
            },
            {
                "name": "查看我的项目的项目收款",
                "codename": "view_my_project_payments",
                "groups": [
                    "BD",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的项目的原型",
                "codename": "view_my_project_prototypes",
                "groups": [
                    "BD",
                    "产品经理",
                    "测试",
                    "远程TPM",
                    "TPM",
                    "培训产品经理",
                    "设计",
                    "项目经理"
                ]
            },
            {
                "name": "查看进行中的项目",
                "codename": "view_ongoing_projects",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "市场",
                    "培训产品经理",
                    "TPM",
                    "测试",
                    "设计"
                ]
            },
            {
                "name": "查看产品经理数据",
                "codename": "view_pm_statistical_data",
                "groups": [
                    "市场",
                    "产品经理"
                ]
            },
            {
                "name": "查看项目饱和度数据",
                "codename": "view_project_capacity_data",
                "groups": []
            },
            {
                "name": "查看项目部署信息",
                "codename": "view_project_deployment_servers",
                "groups": [
                    "测试",
                    "培训产品经理",
                    "TPM",
                    "项目经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看最近60天内结束的项目",
                "codename": "view_projects_finished_in_60_days",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "市场",
                    "培训产品经理",
                    "TPM",
                    "测试",
                    "设计"
                ]
            },
            {
                "name": "查看项目进度",
                "codename": "view_projects_schedules",
                "groups": [
                    "TPM",
                    "培训产品经理",
                    "设计",
                    "产品经理",
                    "测试",
                    "项目经理"
                ]
            },
            {
                "name": "查看项目工时统计页面",
                "codename": "view_project_work_hour_statistic",
                "groups": [
                    "培训产品经理",
                    "TPM",
                    "测试",
                    "产品经理",
                    "设计",
                    "项目经理",
                    "远程TPM"
                ]
            }
        ],
        "func_module": {
            "name": "项目",
            "codename": "projects"
        },
        "name": "项目",
        "codename": "projects"
    },
    {
        "func_perms": [
            {
                "name": "财务.新建固定工程师合同",
                "codename": "finance.create_regular_developer_contract",
                "groups": []
            },
            {
                "name": "财务.管理全部项目工程师合同",
                "codename": "finance.manage_all_project_developer_contracts",
                "groups": [
                    "财务"
                ]
            },
            {
                "name": "财务.管理固定工程师合同打款",
                "codename": "finance.manage_regular_developer_contract_payments",
                "groups": []
            },
            {
                "name": "财务.管理固定工程师合同",
                "codename": "finance.manage_regular_developer_contracts",
                "groups": []
            },
            {
                "name": "财务.查看管理全部项目合同",
                "codename": "finance.view_all_project_contracts",
                "groups": [
                    "财务"
                ]
            },
            {
                "name": "财务.查看全部项目工程师合同",
                "codename": "finance.view_all_project_developer_contracts",
                "groups": [
                    "财务"
                ]
            },
            {
                "name": "财务.查看管理全部项目收款",
                "codename": "finance.view_all_project_payments",
                "groups": [
                    "财务"
                ]
            },
            {
                "name": "财务.查看全部固定工程师合同",
                "codename": "finance.view_all_regular_developer_contracts",
                "groups": []
            },
            {
                "name": "财务.查看我的固定工程师合同",
                "codename": "finance.view_my_regular_developer_contracts",
                "groups": []
            },
            {
                "name": "财务.管理全部工程师打款",
                "codename": "handle_all_developer_payments",
                "groups": [
                    "财务"
                ]
            },
            {
                "name": "财务.查看全部工程师打款",
                "codename": "view_all_developer_payments",
                "groups": [
                    "财务"
                ]
            }
        ],
        "func_module": {
            "name": "财务",
            "codename": "finance"
        },
        "name": "财务",
        "codename": "finance"
    },
    {
        "func_perms": [
            {
                "name": "确认与工程师同步文档",
                "codename": "document_confirm_sync",
                "groups": [
                    "TPM",
                    "远程TPM"
                ]
            },
            {
                "name": "管理工程师文档",
                "codename": "manage_developers_documents",
                "groups": [
                    "TPM",
                    "远程TPM"
                ]
            },
            {
                "name": "查看全部工程师身份证信息",
                "codename": "view_all_developer_id_card_info",
                "groups": []
            },
            {
                "name": "查看全部开发工程师",
                "codename": "view_all_developers",
                "groups": [
                    "TPM",
                    "项目经理"
                ]
            },
            {
                "name": "查看全部进行项目工程师日报",
                "codename": "view_all_ongoing_projects_developers_daily_works",
                "groups": []
            },
            {
                "name": "查看开发者详情页面-开发规范文档",
                "codename": "view_developer_detail_page_documents",
                "groups": []
            },
            {
                "name": "查看工程师报酬",
                "codename": "view_developer_remuneration",
                "groups": [
                    "TPM",
                    "培训产品经理",
                    "产品经理",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的进行项目工程师日报",
                "codename": "view_my_ongoing_projects_developers_daily_works",
                "groups": [
                    "远程TPM",
                    "培训产品经理",
                    "TPM",
                    "设计",
                    "项目经理",
                    "产品经理",
                    "测试"
                ]
            },
            {
                "name": "查看我的项目工程师需求",
                "codename": "view_my_project_position_needs",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "查看我的项目的工程师打款",
                "codename": "view_my_projects_job_payments",
                "groups": [
                    "项目经理"
                ]
            }
        ],
        "func_module": {
            "name": "开发工程师",
            "codename": "developers"
        },
        "name": "开发工程师",
        "codename": "developers"
    },
    {
        "func_perms": [
            {
                "name": "管理项目经理playbook模板",
                "codename": "manage_project_manager_playbook_template",
                "groups": []
            },
            {
                "name": "管理项目产品playbook模板",
                "codename": "manage_project_pm_playbook_template",
                "groups": []
            },
            {
                "name": "管理需求产品playbook模板",
                "codename": "manage_proposal_pm_playbook_template",
                "groups": []
            },
            {
                "name": "查看项目经理playbook",
                "codename": "view_project_manager_playbook",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "查看项目经理playbook模板",
                "codename": "view_project_manager_playbook_template",
                "groups": [
                    "项目经理"
                ]
            },
            {
                "name": "查看项目Playbook模板",
                "codename": "view_project_playbook_template",
                "groups": [
                    "产品经理",
                    "培训产品经理",
                    "项目经理"
                ]
            },
            {
                "name": "查看项目产品playbook",
                "codename": "view_project_pm_playbook",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看项目产品playbook模板",
                "codename": "view_project_pm_playbook_template",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看需求产品playbook",
                "codename": "view_proposal_pm_playbook",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看需求产品playbook模板",
                "codename": "view_proposal_pm_playbook_template",
                "groups": [
                    "培训产品经理",
                    "项目经理",
                    "产品经理"
                ]
            }
        ],
        "func_module": {
            "name": "Playbook",
            "codename": "playbook"
        },
        "name": "Playbook",
        "codename": "playbook"
    },
    {
        "func_perms": [
            {
                "name": "客户管理",
                "codename": "clients_management",
                "groups": []
            },
            {
                "name": "用户管理",
                "codename": "users_management",
                "groups": [
                    "用户管理"
                ]
            },
            {
                "name": "工程师问卷",
                "codename": "engineer_questionnaire",
                "groups": []
            },
            {
                "name": "用户权限限定",
                "codename": "users_perms_limit_management",
                "groups": []
            },
            {
                "name": "团队管理",
                "codename": "users_teams_management",
                "groups": []
            }
        ],
        "func_module": {
            "name": "用户",
            "codename": "users"
        },
        "name": "用户",
        "codename": "users"
    },
    {
        "func_perms": [
            {
                "name": "管理邮件模板",
                "codename": "manage_email_templates",
                "groups": []
            }
        ],
        "func_module": {
            "name": "邮件",
            "codename": "gearmail"
        },
        "name": "邮件",
        "codename": "gearmail"
    },
    {
        "func_perms": [
            {
                "name": "TPM看板.查看全部项目检查点",
                "codename": "tpm_board.view_all_project_checkpoints",
                "groups": [
                    "TPM"
                ]
            },
            {
                "name": "TPM看板.查看我的项目检查点",
                "codename": "tpm_board.view_my_project_checkpoints",
                "groups": [
                    "TPM",
                    "远程TPM"
                ]
            },
            {
                "name": "查看全部工单",
                "codename": "view_all_work_orders",
                "groups": [
                    "BD",
                    "TPM",
                    "培训产品经理",
                    "测试",
                    "财务",
                    "SEM",
                    "产品经理",
                    "市场",
                    "设计",
                    "项目经理"
                ]
            },
            {
                "name": "查看设计甘特图",
                "codename": "view_design_gantt_chart",
                "groups": [
                    "设计",
                    "项目经理"
                ]
            },
            {
                "name": "查看我的工单",
                "codename": "view_my_work_orders",
                "groups": [
                    "远程TPM"
                ]
            },
            {
                "name": "查看测试甘特图",
                "codename": "view_test_gantt_chart",
                "groups": [
                    "测试",
                    "项目经理"
                ]
            },
            {
                "name": "查看TPM看板",
                "codename": "view_tpm_board",
                "groups": [
                    "TPM",
                    "远程TPM"
                ]
            }
        ],
        "func_module": {
            "name": "工单",
            "codename": "work_order"
        },
        "name": "工单",
        "codename": "work_order"
    },
    {
        "func_perms": [
            {
                "name": "管理Quip分享文档",
                "codename": "manage_quip_shared_documents",
                "groups": []
            },
            {
                "name": "查看项目与需求统计数据",
                "codename": "view_projects_and_proposals_statistical_data",
                "groups": [
                    "BD",
                    "项目经理"
                ]
            }
        ],
        "func_module": {
            "name": "其他",
            "codename": "others"
        },
        "name": "其他",
        "codename": "others"
    },
    {
        "func_perms": [
            {
                "name": "使用语音通话服务",
                "codename": "use_voice_call",
                "groups": [
                    "产品经理",
                    "培训产品经理",
                    "市场",
                    "项目经理"
                ]
            },
            {
                "name": "查看所有通话记录",
                "codename": "view_all_call_records",
                "groups": [
                    "产品经理",
                    "培训产品经理",
                    "市场",
                    "项目经理"
                ]
            }
        ],
        "func_module": {
            "name": "语音通话",
            "codename": "voicecall"
        },
        "name": "语音通话",
        "codename": "voicecall"
    },
    {
        "func_perms": [
            {
                "name": "创建参考原型",
                "codename": "create_prototype_reference",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "删除原型参考",
                "codename": "delete_prototype_references",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            },
            {
                "name": "查看所有原型参考",
                "codename": "view_all_prototype_references",
                "groups": [
                    "培训产品经理",
                    "产品经理"
                ]
            }
        ],
        "func_module": {
            "name": "原型参考",
            "codename": "prototype_references"
        },
        "name": "原型参考",
        "codename": "prototype_references"
    },
    {
        "func_perms": [
            {
                "name": "关闭线索-无需被审核",
                "codename": "close_lead",
                "groups": []
            },
            {
                "name": "审核关闭线索的申请",
                "codename": "close_lead_review",
                "groups": []
            },
            {
                "name": "关闭线索-需要被审核",
                "codename": "close_lead_review_required",
                "groups": [
                    "BD"
                ]
            },
            {
                "name": "创建线索",
                "codename": "create_lead",
                "groups": [
                    "BD",
                    "SEM"
                ]
            },
            {
                "name": "编辑线索",
                "codename": "edit_lead",
                "groups": [
                    "BD",
                    "SEM"
                ]
            },
            {
                "name": "SEM线索跟踪管理",
                "codename": "leads_manage_sem_track",
                "groups": [
                    "SEM"
                ]
            },
            {
                "name": "提供线索报价",
                "codename": "provide_lead_quotation",
                "groups": []
            },
            {
                "name": "查看全部线索",
                "codename": "view_all_leads",
                "groups": []
            },
            {
                "name": "查看全部线索报价",
                "codename": "view_all_leads_quotations",
                "groups": []
            },
            {
                "name": "查看线索转化率",
                "codename": "view_leads_conversion_rate",
                "groups": []
            },
            {
                "name": "查看我的线索",
                "codename": "view_my_leads",
                "groups": [
                    "BD",
                    "SEM"
                ]
            }
        ],
        "func_module": {
            "name": "线索",
            "codename": "leads"
        },
        "name": "线索",
        "codename": "leads"
    },
    {
        "func_perms": [
            {
                "name": "登录数据统计",
                "codename": "sign_up_for_gear_tracker",
                "groups": []
            }
        ],
        "func_module": {
            "name": "齿轮应用",
            "codename": "gear_apps"
        },
        "name": "齿轮应用",
        "codename": "gear_apps"
    }
]


def init_func_perms(init_data=None, build_groups=False):
    init_data = init_data or FUNC_PERMS
    for func_module_perms in init_data:
        func_module_data = func_module_perms['func_module']
        func_module, created = FunctionModule.objects.get_or_create(name=func_module_data['name'],
                                                                    codename=func_module_data['codename'])
        for permission_data in func_module_perms['func_perms']:
            permission = FunctionPermission.objects.filter(codename=permission_data['codename'])
            if permission.exists():
                permission = permission.first()
                permission.name = permission_data['name']
                permission.module = func_module
                permission.save()
            else:
                permission, created = FunctionPermission.objects.get_or_create(codename=permission_data['codename'],
                                                                               module=func_module,
                                                                               name=permission_data['name'])
            if build_groups and 'groups' in permission_data:
                permission.groups.clear()
                for group_name in permission_data['groups']:
                    Group.objects.get_or_create(name=group_name)
                groups = Group.objects.filter(name__in=permission_data['groups'])
                permission.groups.add(*groups)
