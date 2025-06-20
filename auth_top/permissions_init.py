from django.utils import six

GEAR_TEST_FUNC_PERMS = [
    {
        "func_module": {
            "codename": "project_list",
            "name": "项目列表"
        },
        "func_perms": [
            {
                "name": "查看项目列表",
                "codename": "project_list",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            }
        ],
    },
    {
        "func_module": {
            "codename": "project_detail",
            "name": "项目详情"
        },
        "func_perms": [
            {
                "name": "查看项目详情",
                "codename": "project_detail",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
            {
                "name": "查看测试计划列表",
                "codename": "project_detail.test_plan_list",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                ]
            },
            {
                "name": "查看测试计划详情",
                "codename": "project_detail.test_plan_detail",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                ]
            },
            {
                "name": "管理测试计划（新建、执行、完成）",
                "codename": "project_detail.test_plan_manage",
                "groups": [
                    "测试",
                    "测试工程师",
                    "项目经理",
                    "TPM",
                    "远程TPM",
                    "产品经理"
                ]
            },

            {
                "name": "查看项目用例",
                "codename": "project_detail.test_cases",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "测试",
                    "测试工程师",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "工程师"
                ]
            },
            {
                "name": "管理项目用例平台",
                "codename": "project_detail.test_cases_platform_manage",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "测试",
                    "测试工程师",
                ]
            },
            {
                "name": "管理项目用例模块",
                "codename": "project_detail.test_cases_module_manage",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "测试",
                    "测试工程师",
                ]
            },
            {
                "name": "管理项目用例(新增、编辑、移动、复制、删除)",
                "codename": "project_detail.test_cases_case_manage",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "测试",
                    "测试工程师",
                ]
            },

            {
                "name": "从用例库导入用例",
                "codename": "project_detail.test_cases_case_import",
                "groups": [
                    "测试",
                    "测试工程师",
                ]
            },

            {
                "name": "评审项目用例",
                "codename": "project_detail.test_cases_case_review",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "测试",
                    "测试工程师"
                ]
            },

            {
                "name": "查看Bug列表",
                "codename": "project_detail.bug_list",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
            {
                "name": "查看Bug详情",
                "codename": "project_detail.bug_detail",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
            {
                "name": "编辑Bug",
                "codename": "project_detail.bug_edit",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
            {
                "name": "新增Bug",
                "codename": "project_detail.bug_create",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
            {
                "name": "修复，指派Bug",
                "codename": "project_detail.bug_fix",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
            {
                "name": "确认修复，无效关闭，激活Bug",
                "codename": "project_detail.bug_confirm",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "设计师",
                    "测试",
                    "测试工程师",
                ]
            },
            {
                "name": "评论Bug",
                "codename": "project_detail.bug_comment",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
            {
                "name": "查看Bug操作记录",
                "codename": "project_detail.bug_log",
                "groups": [
                    "项目经理",
                    "产品经理",
                    "培训产品经理",
                    "TPM",
                    "远程TPM",
                    "设计",
                    "测试",
                    "测试工程师",
                    "工程师",
                ]
            },
        ],
    },
    {
        "func_module": {
            "codename": "case_library",
            "name": "用例库"
        },
        "func_perms": [
            {
                "name": "查看用例库列表",
                "codename": "case_library_list",
                "groups": ['测试', "测试工程师"],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            },
            {
                "name": "新增用例库",
                "codename": "case_library_create",
                "groups": ['测试'],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            },
            {
                "name": "管理用例库(编辑、删除)",
                "codename": "case_library_manage",
                "groups": ['测试'],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            },
            {
                "name": "通过excel导入用例库用例",
                "codename": "case_library_case_import",
                "groups": ['测试', "测试工程师"],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            },
            {
                "name": "查看用例库详情",
                "codename": "case_library_detail",
                "groups": ['测试', "测试工程师"],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            },
            {

                "name": "管理用例库模块",
                "codename": "case_library_module_manage",
                "groups": ['测试'],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            },
            {

                "name": "管理用例库用例(新增、编辑、移动、复制、删除)",
                "codename": "case_library_case_manage",
                "groups": ['测试'],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            },
            {

                "name": "评审用例库用例",
                "codename": "case_library_case_review",
                "groups": [],
                "users": ['唐海鹏', '袁佩璋', '霍俊光']
            }
        ],
    },
]


def get_top_user_perms(top_user, app_id):
    base_data = None
    if app_id == 'gear_test':
        base_data = GEAR_TEST_FUNC_PERMS
    perms = []
    if base_data and top_user.is_active:
        is_superuser = False
        if top_user.is_freelancer:
            group_names = ['工程师']
            group_names.extend(top_user.developer.roles.values_list('name', flat=True))
        else:
            group_names = list(top_user.user.groups.values_list('name', flat=True))
            is_superuser = top_user.user.is_superuser

        for func_module in base_data:
            for func_perm in func_module['func_perms']:
                if is_superuser:
                    perms.append(func_perm['codename'])
                else:
                    perm_groups = func_perm['groups']
                    perm_users = func_perm.get('users', [])
                    if set(group_names) & set(perm_groups):
                        perms.append(func_perm['codename'])
                    elif perm_users and top_user.username in perm_users:
                        perms.append(func_perm['codename'])
    return perms


def has_app_function_perms(user, perms, app_id):
    if isinstance(perms, six.string_types):
        perms = (perms,)
    for perm in perms:
        if not has_app_function_perm(user, perm, app_id):
            return False
    return True


def has_app_function_perm(user, perm, app_id):
    if user.is_active and user.is_superuser:
        return True
    perms = get_top_user_perms(user, app_id)
    if perm in perms:
        return True
    return False
