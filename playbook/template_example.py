proposal_stages = [
    {
        "name": "等待认领阶段",
        "check_groups": [],
        "status": 1
    },
    {
        "name": "等待沟通阶段",
        "check_groups": [
            {
                "description": "需求沟通准备",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "创建需求文件夹：客户-需求文件夹下面",
                        "info_items": [
                            {
                                "description": "文件夹命名格式 Farm编号+需求名称",
                                "links": []
                            }
                        ],
                        "links": []
                    },
                    {
                        "type": "Quip",
                        "description": "创建需求沟通准备文档，并和导师确认",
                        "info_items": [
                            {
                                "description": "示例",
                                "links": [
                                    {
                                        "name": "电话沟通准备",
                                        "url": "https://quip.com/5tIcAwGUx4De"
                                    }
                                ]
                            }
                        ],
                        "links": [
                            {
                                "name": "客户初次电话需求沟通手册",
                                "url": "https://quip.com/Hk6fAmQYVcoA"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "需求沟通&电话录音",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "打电话并录音",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何与新客户沟通",
                                "url": "https://quip.com/YSxkAaoUW9no"
                            },
                            {
                                "name": "需求通话及录音文件管理",
                                "url": "https://quip.com/sq4LATvtxQHW)[电话/面谈咨询注意事项](https://quip.com/TOdBABFUyZCn"
                            },
                            {
                                "name": "产品经理咨询常见问题回答思路和话术汇总",
                                "url": "https://quip.com/iCHHAfY8evjc"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "需求状态变更，勾选已联系客户",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            }
        ],
        "status": 2
    },
    {
        "name": "进行中阶段",
        "check_groups": [
            {
                "description": "编写反馈报告",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "需求报告文档",
                        "info_items": [
                            {
                                "description": "关于UI设计部分的特殊说明：",
                                "links": [
                                    {
                                        "name": "产品反馈报告-UI设计特别说明",
                                        "url": "https://quip.com/4ZuVAeEjayMH"
                                    }
                                ]
                            },
                            {
                                "description": "报价需要注意的事项",
                                "links": [
                                    {
                                        "name": "产品反馈报告中报价及工期估算",
                                        "url": "https://quip.com/HPfpAz5P6Nnw"
                                    }
                                ]
                            }
                        ],
                        "links": [
                            {
                                "name": "产品反馈报告写作原则",
                                "url": "https://quip.com/gqIzA3bbzbf0"
                            },
                            {
                                "name": "产品反馈报告撰写注意事项及细节",
                                "url": "https://quip.com/VMbnA9iW0c7v"
                            },
                            {
                                "name": "Farm报告编辑器使用说明",
                                "url": "https://quip.com/jLmXAKyX593Q"
                            }
                        ]
                    },
                    {
                        "type": null,
                        "description": "通知导师（默认小明老师）确认报告方案、周期及报价",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            },
            {
                "description": "生成并发送报告",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "生成报告",
                        "info_items": [],
                        "links": [
                            {
                                "name": "使用Quip链接直接生成报告",
                                "url": "https://quip.com/g0RIAVWQpMWB"
                            }
                        ]
                    },
                    {
                        "type": "微信",
                        "description": "发送到BD产品经理一家亲群",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "Farm",
                        "description": "需求状态变更，勾选已发报告",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            },
            {
                "description": "持续客户沟通",
                "check_items": [
                    {
                        "type": "微信",
                        "description": "收集用户反馈",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": null,
                        "description": "迭代报告并由导师确认，生成报告，发给BD/客户",
                        "info_items": [
                            {
                                "description": "关于UI设计部分的特殊说明：",
                                "links": [
                                    {
                                        "name": "产品反馈报告-UI设计特别说明",
                                        "url": "https://quip.com/4ZuVAeEjayMH"
                                    }
                                ]
                            },
                            {
                                "description": "报价需要注意的事项",
                                "links": [
                                    {
                                        "name": "产品反馈报告中报价及工期估算",
                                        "url": "https://quip.com/HPfpAz5P6Nnw"
                                    }
                                ]
                            }
                        ],
                        "links": []
                    }
                ],
                "links": []
            }
        ],
        "status": 4
    },
    {
        "name": "商机阶段",
        "check_groups": [
            {
                "description": "配合BD制作合同",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "合同文档",
                        "info_items": [
                            {
                                "description": "",
                                "links": [
                                    {
                                        "name": "主合同中UI部分的特殊约定",
                                        "url": "https://quip.com/kTNhA5cmdSN0"
                                    }
                                ]
                            }
                        ],
                        "links": [
                            {
                                "name": "如何做合同",
                                "url": "https://quip.com/OO8aAc3KSmRv"
                            },
                            {
                                "name": "如何书写用于普票备案的合同附件一",
                                "url": "https://quip.com/dy43ASjzW5Z3"
                            }
                        ]
                    }
                ],
                "links": []
            }
        ],
        "status": 5
    },
    {
        "name": "成单交接阶段",
        "check_groups": [
            {
                "description": "配合BD制作合同",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "合同文档",
                        "info_items": [
                            {
                                "description": "",
                                "links": [
                                    {
                                        "name": "主合同中UI部分的特殊约定",
                                        "url": "https://quip.com/kTNhA5cmdSN0"
                                    }
                                ]
                            }
                        ],
                        "links": [
                            {
                                "name": "如何做合同",
                                "url": "https://quip.com/OO8aAc3KSmRv"
                            },
                            {
                                "name": "如何书写用于普票备案的合同附件一",
                                "url": "https://quip.com/dy43ASjzW5Z3"
                            }
                        ]
                    }
                ],
                "links": []
            }
        ],
        "status": 6
    },
    {
        "name": "成单阶段",
        "check_groups": [],
        "status": 10
    },
    {
        "name": "未成单阶段",
        "check_groups": [],
        "status": 11
    }
]

project_stages = [
    {
        "name": "原型阶段",
        "check_groups": [
            {
                "description": "创建项目及准备工作",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "客户-项目目录下创建项目文件夹",
                        "info_items": [],
                        "links": [
                            {
                                "name": "Quip项目文件夹结构（新）",
                                "url": "https://quip.com/atdyADkAQwbj"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "项目工程师沟通目录下创建项目文件夹",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            },
            {
                "description": "确认首期款",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "录入项目应收款",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目待收款记录",
                                "url": "https://quip.com/3qWQArY5BhIL"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "确认首期款已打",
                        "info_items": [],
                        "links": [
                            {
                                "name": "客户付款确认流程",
                                "url": "https://quip.com/bd5UAHnO5zpe"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "项目启动通知",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "制作项目日程表",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目日程计划表（给客户的）",
                                "url": "https://quip.com/vugoADTc3fhx"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "发送项目启动邮件（邮件模板【1】）",
                        "info_items": [],
                        "links": [
                            {
                                "name": "提醒客户需要准备的材料",
                                "url": "https://quip.com/qIISArdAaGbN"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "制作原型",
                "check_items": [
                    {
                        "type": "电话/见面",
                        "description": "进一步了解客户业务需求",
                        "info_items": [],
                        "links": [
                            {
                                "name": "产品经理主动去客户处确认业务需求注意事项",
                                "url": "https://quip.com/ATTRADC23YDJ"
                            }
                        ]
                    },
                    {
                        "type": "视频会议/见面",
                        "description": "跟客户确认核心的需求和流程（原型或者框架图）",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "Axure",
                        "description": "制作原型",
                        "info_items": [],
                        "links": [
                            {
                                "name": "原型制作逻辑原则+标准格式源文件",
                                "url": "https://quip.com/X2uPAPjbUAjU"
                            }
                        ]
                    },
                    {
                        "type": "会议1",
                        "description": "导师原型评审",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "会议2",
                        "description": "原型内部评审",
                        "info_items": [],
                        "links": [
                            {
                                "name": "产品原型+PRD评审流程规则",
                                "url": "https://quip.com/bNb4ATPg2ZQ3"
                            }
                        ]
                    },
                    {
                        "type": "视频会议3/见面",
                        "description": "客户原型沟通（注意：这不是确认）",
                        "info_items": [],
                        "links": [
                            {
                                "name": "跟客户过原型的技巧",
                                "url": "https://quip.com/iYv8AcF2ZChz"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "原型确认邮件【邮件模板2】",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            },
            {
                "description": "制作PRD",
                "check_items": [
                    {
                        "type": "Axure",
                        "description": "制作PRD",
                        "info_items": [],
                        "links": [
                            {
                                "name": "原型制作逻辑原则+标准格式源文件",
                                "url": "https://quip.com/X2uPAPjbUAjU"
                            }
                        ]
                    },
                    {
                        "type": "会议4",
                        "description": "导师原型PRD审核",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            }
        ],
        "status": 5
    },
    {
        "name": "设计阶段",
        "check_groups": [
            {
                "description": "内部评审会",
                "check_items": [
                    {
                        "type": "微信",
                        "description": "通知UI/QA/TPM项目内审会时间",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "Quip",
                        "description": "提交UI启动交接文档",
                        "info_items": [],
                        "links": [
                            {
                                "name": "设计启动工单",
                                "url": "https://quip.com/5SIJAd1xeTBD"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "制作初版甘特图",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何制作甘特图",
                                "url": "https://quip.com/vYoFAxHuHiia"
                            }
                        ]
                    },
                    {
                        "type": "会议5",
                        "description": "内部评审会",
                        "info_items": [],
                        "links": [
                            {
                                "name": "内部评审会流程及注意事项",
                                "url": "https://quip.com/OwfGAU0sYhUb"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "UI设计",
                "check_items": [
                    {
                        "type": "微信",
                        "description": "设计风格客户确认",
                        "info_items": [],
                        "links": [
                            {
                                "name": "UI设计风格确认",
                                "url": "https://quip.com/i3ftAPTZ5ciy"
                            }
                        ]
                    },
                    {
                        "type": "会议6",
                        "description": "UI设计评审会",
                        "info_items": [],
                        "links": [
                            {
                                "name": "设计阶段蓝湖使用说明",
                                "url": "https://quip.com/wsFBAXocH0hL"
                            }
                        ]
                    },
                    {
                        "type": "微信",
                        "description": "设计稿客户确认",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "Farm",
                        "description": "原型PRD及UI设计确认邮件【邮件模板3】",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "蓝湖",
                        "description": "UI设计交付工程师",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            },
            {
                "description": "确定工程师",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "提交工程师需求",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目工程师需求提交和确认",
                                "url": "https://quip.com/8q42AYYZm9jV"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "工期评估文档（TPM）示例：",
                        "info_items": [],
                        "links": [
                            {
                                "name": "开发时间评估示例",
                                "url": "https://box.chilunyc.com/s/ONDLbHNRF4qFsva"
                            }
                        ]
                    },
                    {
                        "type": "电话",
                        "description": "备选工程师沟通",
                        "info_items": [],
                        "links": [
                            {
                                "name": "与备选工程师初次沟通指南",
                                "url": "https://quip.com/yiMLArtaf1Y7"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "工程师提供工期评估文档（工程师）示例：",
                        "info_items": [],
                        "links": [
                            {
                                "name": "开发时间评估示例",
                                "url": "https://box.chilunyc.com/s/ONDLbHNRF4qFsva"
                            }
                        ]
                    },
                    {
                        "type": "微信",
                        "description": "确认工期与报酬",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目工程师选择、成本估算流程及注意事项",
                                "url": "https://quip.com/knq9AVLnEs2C"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "制作工程师合同",
                        "info_items": [],
                        "links": [
                            {
                                "name": "工程师签约流程",
                                "url": "https://quip.com/Gu4DAT21tSks"
                            },
                            {
                                "name": "工程师合同模板",
                                "url": "https://quip.com/OxpQAbnZkYv5"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "录入开发职位信息",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目工程师需求提交和确认",
                                "url": "https://quip.com/8q42AYYZm9jV"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "项目文件夹分享给工程师",
                        "info_items": [],
                        "links": [
                            {
                                "name": "Quip项目文件夹结构（新）",
                                "url": "https://quip.com/atdyADkAQwbj"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "Sprint",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "Sprint计划及开发框架文档",
                        "info_items": [],
                        "links": [
                            {
                                "name": "敏捷项目管理简述",
                                "url": "https://quip.com/cBCkApfuGDdG"
                            }
                        ]
                    },
                    {
                        "type": "会议7",
                        "description": "Sprint计划及开发框架评审会",
                        "info_items": [],
                        "links": [
                            {
                                "name": "Sprint评审流程及注意事项",
                                "url": "https://quip.com/l68ZA31QPkpO"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "更新Sprint计划至甘特图",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何制作甘特图",
                                "url": "https://quip.com/vYoFAxHuHiia"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "测试用例",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "测试输出测试要点",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "会议8",
                        "description": "测试要点评审",
                        "info_items": [],
                        "links": [
                            {
                                "name": "测试要点评审流程及注意事项",
                                "url": "https://quip.com/uDF0AWYLWJU6"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "测试输出测试用例",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "会议9",
                        "description": "测试用例评审会",
                        "info_items": [],
                        "links": [
                            {
                                "name": "测试用例评审流程及注意事项",
                                "url": "https://quip.com/65abA8YgP6PL"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "项目中期款",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "客户资料",
                        "info_items": [],
                        "links": [
                            {
                                "name": "提醒客户需要准备的材料",
                                "url": "https://quip.com/qIISArdAaGbN"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "开发资料",
                        "info_items": [],
                        "links": [
                            {
                                "name": "需要提供的开发资料",
                                "url": "https://quip.com/TlGAA5m7fNhc"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "确认客户打款（第二笔）",
                        "info_items": [],
                        "links": [
                            {
                                "name": "客户付款确认流程",
                                "url": "https://quip.com/bd5UAHnO5zpe"
                            }
                        ]
                    }
                ],
                "links": []
            }
        ],
        "status": 6
    },
    {
        "name": "开发阶段",
        "check_groups": [
            {
                "description": "项目启动会",
                "check_items": [
                    {
                        "type": "Quip",
                        "description": "项目启动会沟通提纲",
                        "info_items": [],
                        "links": [
                            {
                                "name": "Kick Off Meeting（待修改）",
                                "url": "https://quip.com/jX5MAABqUNef"
                            }
                        ]
                    },
                    {
                        "type": "会议10",
                        "description": "项目启动会",
                        "info_items": [],
                        "links": [
                            {
                                "name": "PRD评审-工程师",
                                "url": "https://quip.com/SF98A8XyrhDR"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "项目启动会会议记录 @启动会会议记录示例",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "Farm",
                        "description": "更新甘特图（如果需要）",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            },
            {
                "description": "项目周会（每周执行）",
                "check_items": [
                    {
                        "type": "Git",
                        "description": "确保工程师代码及时更新",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "会议11",
                        "description": "项目周会",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何开项目周例会",
                                "url": "https://quip.com/D4HWAY9xBHKL"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "更新甘特图（如果需要）",
                        "info_items": [],
                        "links": []
                    }
                ],
                "links": []
            },
            {
                "description": "Sprint执行",
                "check_items": [
                    {
                        "type": "Yapi",
                        "description": "输出接口文档  @接口文档输出说明示例",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "会议12",
                        "description": "接口文档评审会 @接口文档评审会流程及注意事项",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "Farm",
                        "description": "打工程师首次款",
                        "info_items": [],
                        "links": [
                            {
                                "name": "工程师打款流程说明",
                                "url": "https://quip.com/FqnjAaUTuogZ"
                            }
                        ]
                    },
                    {
                        "type": "微信/Farm",
                        "description": "开发进度每日跟进",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何跟进工程师每日的进度",
                                "url": "https://quip.com/paS3Ae8errFP"
                            }
                        ]
                    },
                    {
                        "type": "会议13",
                        "description": "Sprint测试范围确认",
                        "info_items": [],
                        "links": [
                            {
                                "name": "确保测试/UI人员权限",
                                "url": "https://quip.com/lOcWA8qrfsmG"
                            }
                        ]
                    },
                    {
                        "type": "Git",
                        "description": "Sprint测试",
                        "info_items": [],
                        "links": [
                            {
                                "name": "敏捷项目管理简述",
                                "url": "https://quip.com/cBCkApfuGDdG"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "UI走查",
                        "info_items": [],
                        "links": [
                            {
                                "name": "UI走查阶段如何与工程师/产品经理配合",
                                "url": "https://quip.com/4CqsAIL4aR5I"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "工程师打款首期款",
                        "info_items": [],
                        "links": [
                            {
                                "name": "工程师打款流程说明",
                                "url": "https://quip.com/FqnjAaUTuogZ"
                            }
                        ]
                    },
                    {
                        "type": "Farm",
                        "description": "打工程师二次款",
                        "info_items": [],
                        "links": [
                            {
                                "name": "工程师打款流程说明（待更新9-02）",
                                "url": "https://quip.com/FqnjAaUTuogZ"
                            }
                        ]
                    }
                ],
                "links": []
            }
        ],
        "status": 7
    },
    {
        "name": "测试阶段",
        "check_groups": [
            {
                "description": "项目周会（每周执行）",
                "check_items": [
                    {
                        "type": "会议11",
                        "description": "项目周会",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何开项目周例会",
                                "url": "https://quip.com/D4HWAY9xBHKL"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "全量测试",
                "check_items": [
                    {
                        "type": "Git",
                        "description": "全量测试",
                        "info_items": [],
                        "links": [
                            {
                                "name": "敏捷项目管理简述",
                                "url": "https://quip.com/cBCkApfuGDdG"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "UI走查",
                        "info_items": [],
                        "links": [
                            {
                                "name": "UI走查流程",
                                "url": "https://quip.com/4CqsAIL4aR5I"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "兼容性测试覆盖确认",
                        "info_items": [],
                        "links": [
                            {
                                "name": "XXX项目兼容性测试确认表",
                                "url": "https://quip.com/9oP4Aneoklup"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "验收前回归测试",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目交付三方确认",
                                "url": "https://quip.com/8wBSAD4d0vx1"
                            }
                        ]
                    }
                ],
                "links": []
            }
        ],
        "status": 8
    },
    {
        "name": "验收阶段",
        "check_groups": [
            {
                "description": "客户验收阶段反馈",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "验收邮件（邮件模板【5】）",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "微信",
                        "description": "通知客户开始验收",
                        "info_items": [],
                        "links": [
                            {
                                "name": "通知客户验收话术",
                                "url": "https://quip.com/temp:Be099aa8b2ae4f745d5481a8a907d540"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "客户验收阶段反馈文档",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何应对客户的不合理需求？",
                                "url": "https://quip.com/oRMhARsgZP7z)[客户验收阶段反馈【示例】](https://quip.com/StQpAjfH3D9u"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "客户反馈更新记录",
                        "info_items": [],
                        "links": [
                            {
                                "name": "更新记录【示例】",
                                "url": "https://quip.com/rhniA0U07v7Y"
                            }
                        ]
                    },
                    {
                        "type": "Quip",
                        "description": "每次版本提交时验收确认",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目交付三方确认",
                                "url": "https://quip.com/8wBSAD4d0vx1"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "确认客户验收通过",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "确认项目尾款",
                        "info_items": [],
                        "links": [
                            {
                                "name": "客户付款确认流程",
                                "url": "https://quip.com/bd5UAHnO5zpe"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "收集交付文档",
                "check_items": [
                    {
                        "type": "Git",
                        "description": "确认所有最新代码已上传(TPM代码审核)",
                        "info_items": [],
                        "links": []
                    },
                    {
                        "type": "Farm",
                        "description": "交付文档上传（原型PRD更新）",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目交付文档",
                                "url": "https://quip.com/D1aJAUBu3ZFV"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "部署",
                "check_items": [
                    {
                        "type": "Git",
                        "description": "部署后全量测试",
                        "info_items": [],
                        "links": [
                            {
                                "name": "部署后回归测试注意事项",
                                "url": "https://quip.com/Uas4Aa05j6ye"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "正式交付",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "发交付文件邮件（邮件模板【6】）",
                        "info_items": [],
                        "links": [
                            {
                                "name": "项目交付文档",
                                "url": "https://quip.com/D1aJAUBu3ZFV"
                            }
                        ]
                    }
                ],
                "links": []
            }
        ],
        "status": 9
    },
    {
        "name": "完成",
        "check_groups": [
            {
                "description": "工程师打尾款",
                "check_items": [
                    {
                        "type": "Farm",
                        "description": "打工程师尾款",
                        "info_items": [],
                        "links": [
                            {
                                "name": "工程师打款流程说明",
                                "url": "https://quip.com/FqnjAaUTuogZ"
                            }
                        ]
                    }
                ],
                "links": []
            },
            {
                "description": "项目复盘",
                "check_items": [
                    {
                        "type": "会议",
                        "description": "会议16：项目复盘",
                        "info_items": [],
                        "links": [
                            {
                                "name": "如何有效的复盘",
                                "url": "https://quip.com/TbC4A8aZBjkV"
                            }
                        ]
                    }
                ],
                "links": []
            }
        ],
        "status": 10
    }
]
