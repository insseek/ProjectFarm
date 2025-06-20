# 创建新报告时 、报告的初始内容
# 线索第一个报告
lead_report_new_init_content = {
    "ops": [{"insert": "公司背景"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n项目背景"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n会议记录"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n下一步计划"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n"}]}
# 报告下一个版本的初始内容
lead_report_update_init_content = {
    "ops": [{"insert": "公司背景"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n项目背景"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n会议记录"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n下一步计划"},
            {"attributes": {"header": 2}, "insert": "\n"},
            {"insert": "\n"}]}
# 下一个版本报告新增内容
lead_report_update_ops = [
]

# 线索第一个报告 文本
lead_report_new_init_text = '''公司背景

项目背景

会议记录

下一步计划

'''

# 报告下一个版本的初始内容 文本
lead_report_update_init_text = '''公司背景

项目背景

会议记录

下一步计划


'''

# 下一个版本报告新增内容 文本
lead_report_update_text = ""

# 报告内容 对应的html
lead_report_new_init_html = "<h2>公司背景</h2><p><br></p><h2>项目背景</h2><p><br></p><h2>会议记录</h2><p><br></p><h2>下一步计划</h2><p><br></p>"
lead_report_update_init_html = "<h2>公司背景</h2><p><br></p><h2>项目背景</h2><p><br></p><h2>会议记录</h2><p><br></p><h2>下一步计划</h2><p><br></p>"
lead_report_update_html = ""
