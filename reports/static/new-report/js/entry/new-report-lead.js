import React from 'react';
import ReactDOM from 'react-dom';
import ReactCSSTransitionGroup from 'react-addons-css-transition-group';
import 'antd/dist/antd.less';
import AvatarImg from '../components/AvatarImg';
import Review from '../components/Review'
import ReportTagsModal from '../components/ReportTagsModal';
import GuideModal from '../components/GuideModal';

import {
    Button,
    DatePicker,
    ConfigProvider,
    Icon,
    Input,
    message,
    Modal,
    Form,
    Checkbox,
    TreeSelect,
    Select,
    Tree,
    Spin
} from "antd";

const {Option} = Select;

import zhCN from 'antd/es/locale/zh_CN';

const dateFormat = 'YYYY.M.D'
const {SHOW_PARENT, SHOW_ALL} = TreeSelect;

//初始化quill的Icon
import {initQuillIcon} from '../quill-custom-icons.js'
import {initQuillKeyboard} from '../quill-custom-keyboard.js'

//全局提交时的定时器
let editTimeoutFun = null;

const PlanProjectSelect = ["iOS App ", "Android App", "移动端H5网站", "微信小程序", "微信服务号", "微信公众号", "PC端 Web 网站", "PC端 Web 管理后台", "Pad端 iOS App", "Pad端 Android App"];
const PlanSeverSelect = ['产品咨询', '原型制作', 'UI设计', '功能开发', '功能测试'];

//编辑报告
class NewReports extends React.Component {
    constructor(props) {
        super(props);
        this.state = {

            savaState: '', // 1 正在保存 2 保存成功 3 出错  4 别人正在编辑
            savaTime: '', //保存时间

            return_page: true,

            allCommentData: null,
            pointCommentData: [],

            reportDetail: '',
            showBoxDetail: '',

            editAndViewUsers: {}, //编辑与查看的用户的列表
            isNewComment: false, //是否有新的评论

            title: '',

            time1: null, //制作时间
            time2: null, //沟通时间
            address: null, //沟通地点

            // 历史版本 表格中的数据
            tableData: [
                {
                    company: '',
                    name: '',
                    position: '',
                    contact: '',
                }
            ],

            quotation_plans: [],

            //开关
            show_plan: false,
            // show_attention: true,
            show_company_about: true,
            show_company_clients: true,


            //点击编辑
            isEdit: false,

            //全剧弹框中的tab
            showTab: '',  //空是不显示 1评论 2历史 3记录
            commentCount: 0, //评论的条数


            //当前显示历史记录id
            activeHistoryId: '',
            historyData: [],// 历史列表

            showBox: false,  //展示

            recordData: [], //记录列表


            //发布报告
            showPublishReportModal: false,

        };
    }

    componentDidMount() {
        //获取当前报告编辑及查看用户列表的接口
        this.getEditUserLsit();

        // 获取报告详情
        this.getRepoetDetail();
        this.historyVersion();

        this.getReportCommentData();

        this.getHistoryData();
        this.getRecordData();

        this.pusherFun();

        let that = this;
        window.pointState = {
            _updatePoint:'',
            get updatePoint(){
                return this._updatePoint;
            },
            set updatePoint(newVal){
                that.getReportCommentData();
                this._updatePoint = newVal;
            },
        }


        //顶部阴影
        $('.report-container').scroll(function () {
            if ($('.report-container').scrollTop() > 50) {
                $('.toolbar-fixed').addClass('scroll-top')
            } else {
                $('.toolbar-fixed').removeClass('scroll-top')
            }
        })


        //点击指定元素外  -- 顶部编辑
        $(document).bind('click', (e) => {
            var event = e || window.event; //浏览器兼容性
            var elem = event.target || event.srcElement;

            while (elem && elem !== '') { //循环判断至跟节点，防止点击的是div子元素
                if (
                    (
                        elem.className &&
                        typeof (elem.className) == 'string' &&
                        elem.className.indexOf('top-item-list-edit') >= 0 &&
                        elem.className.indexOf('active-tab') >= 0
                    )
                    ||
                    (
                        elem.className &&
                        typeof (elem.className) == 'string' &&
                        elem.className.indexOf('edit-modal') >= 0
                    )

                ) {
                    return;
                }
                elem = elem.parentNode;
            }
            if (this.state.isEdit) {
                this.setState({
                    isEdit: false,
                })
            }
        });


        //点击指定元素外  -- 表格添加与删除行
        $(document).bind('click', (e) => {
            var event = e || window.event; //浏览器兼容性
            var elem = event.target || event.srcElement;

            while (elem && elem !== '') { //循环判断至跟节点，防止点击的是div子元素
                if (
                    // (
                    elem.className &&
                    typeof (elem.className) == 'string' &&
                    elem.className.indexOf('contr-btn-box') >= 0
                // )
                ) {
                    return;
                }
                elem = elem.parentNode;
            }
            $('.contr-btn-box').removeClass('checked');
        });


        //网页关闭前

        $(window).on('beforeunload', function () {
            if (that.state.savaState != '3' && that.state.savaState != '4') {

                let reportDetail = that.state.reportDetail;

                reportDetail.meeting_time = that.state.time2 ? moment(that.state.time2).format('YYYY-MM-DD') : null;
                reportDetail.meeting_place = that.state.address ? that.state.address : null;
                reportDetail.meeting_participants = that.state.tableData;


                reportDetail.title = that.state.title;
                reportDetail.meeting_participants = that.state.tableData;
                // reportDetail.quotation_plans = clone(that.state.quotation_plans);
                reportDetail.quotation_plans = that.state.quotation_plans;
                reportDetail.show_plan = that.state.show_plan;
                reportDetail.show_company_about = that.state.show_company_about;
                reportDetail.show_company_clients = that.state.show_company_clients;
                reportDetail.main_content = quill.getContents();
                reportDetail.main_content_text = quill.getText();
                reportDetail.main_content_html = $('.ql-editor').html();

                reportDetail.return_page = that.state.return_page;
                reportDetail.leave_page = true;
                reportDetail.page_view_uuid = PageData.page_view_uuid;
                reportDetail.quotation_plan_price_unit = "万";

                let url = '/api/reports/' + PageData.reportData.uid + '/edit';

                /*for(let i = 0 ; i<reportDetail.quotation_plans.length;i++){
                    if(reportDetail.quotation_plans[i].price && reportDetail.quotation_plans[i].price!=''){
                        reportDetail.quotation_plans[i].price = reportDetail.quotation_plans[i].price+'万'
                    }
                }*/
                $.ajax({
                    type: "POST",
                    url: url,
                    contentType: 'application/json',
                    data: JSON.stringify(reportDetail),
                    success: function (data) {
                    },
                    error: function (err) {
                    }
                });
            }


            // return false;
        });
    }

    //pusher方法
    pusherFun() {
        let that = this;
        let channelName = 'report-' + PageData.reportData.id + '-channel';
        //编辑及查看报告的用户数据改变
        GearPusher.receiveMessage(channelName, 'editable_data_update', function (data) {
            that.getEditUserLsit();
        });
        //报告数据更新的提醒
        GearPusher.receiveMessage(channelName, 'content-update', function (data) {
            if (data.page_view_uuid != PageData.page_view_uuid) {
                that.getRepoetDetail();
            }
        });
        //有新的全局评论
        GearPusher.receiveMessage(channelName, 'new-comment', function (data) {
            if (data.author_id != loggedUser.id) {
                that.setState({
                    isNewComment: true
                })
                that.child.updateList();
            }
        });
        //有新的操作记录
        GearPusher.receiveMessage(channelName, 'new-log', function (data) {
            that.getRecordData();
        });
    }

    //获取报告详情
    getRepoetDetail() {
        let url = '/api/reports/' + PageData.reportData.uid;
        commonRequest('GET', url, {}, (res) => {
            if (res.result) {
                if (res.data.meeting_participants.length <= 0) {
                    res.data.meeting_participants.push({
                        company: '',
                        name: '',
                        position: '',
                        contact: '',
                    })
                }

                this.setState({
                    reportDetail: res.data,

                    time2: res.data.meeting_time,
                    address: res.data.meeting_place,

                    title: res.data.title,
                    tableData: res.data.meeting_participants,
                    quotation_plans: res.data.quotation_plans,
                    show_plan: res.data.show_plan,
                    show_company_about: res.data.show_company_about,
                    show_company_clients: res.data.show_company_clients,
                }, () => {
                    this.initQuill();
                })

            } else {
            }
        })
    }

    //获取报告中所有评论点数量
    getReportCommentList() {
        return new Promise((resolve, reject) => {
            if (this.state.allCommentData == null) {
                let url = '/api/reports/' + PageData.reportData.uid + '/comment_points';
                commonRequest('GET', url, {}, (res) => {
                    if (res.result) {
                        let data = {};
                        for (let i = 0; i < res.data.length; i++) {
                            data[res.data[i].uid] = res.data[i].comments.length;
                        }
                        this.setState({
                            allCommentData: data
                        })
                        resolve(data)
                    } else {
                        reject('err')
                    }
                })
            } else {
                resolve(this.state.allCommentData)
            }
        });
    }

    //报告中所有评论点数据
    getReportCommentData() {
        let url = '/api/reports/' + PageData.reportData.uid + '/comment_points?ordering=created_at';
        commonRequest('GET', url, {}, (res) => {
            if (res.result) {
                let data = {};
                let pointCommentCount = 0;
                for (let i = 0; i < res.data.length; i++) {
                    pointCommentCount += res.data[i].comments.length
                    data[res.data[i].uid] = res.data[i].comments.length;
                }

                this.setState({
                    allCommentData: data,
                    pointCommentData: res.data,
                    pointCommentCount: pointCommentCount
                })
            } else {
            }
        })
    }

    // quill初始化
    initQuill() {

        Quill.register('modules/multi_cursors', QuillCursors);
        const toolbarOptions = {
            container: '#toolbar',
            handlers: {
                'wireframe-image-btn': true,
                'mindmap-image-btn': true,
                'image-model-btn': true,
                'insert-table-btn': true,
                'undo': function () {
                    this.quill.history.undo();
                },
                'redo': function () {
                    this.quill.history.redo();
                }
            }
        };
        quill = new Quill('#main-sections', {
            modules: {
                toolbar: toolbarOptions,
                history: {
                    delay: 1000,//多少毫秒数内发生的更改合并为单个更改
                    maxStack: 100,//撤销/重做堆栈的最大大小
                    userOnly: true //只有用户更改会被撤销或者重做
                },
                inline_comment: true,
                multi_cursors: true,
                gear_images: true,

                table: false,
                'better-table': {
                    operationMenu: {
                        items: {
                            insertColumnRight:{
                                text: '右侧插入'
                            },
                            insertColumnLeft:{
                                text: '左侧插入'
                            },
                            insertRowUp: {
                                text: '上方插入'
                            },
                            insertRowDown: {
                                text: '下方插入'
                            },
                            mergeCells: {
                                text: '合并单元格'
                            },
                            unmergeCells: {
                                text: '拆分单元格'
                            },
                            deleteColumn: {
                                text: '删除列'
                            },
                            deleteRow: {
                                text: '删除行'
                            },
                            deleteTable: {
                                text: '删除表格'
                            },
                        },
                        color: {
                            colors: ['green', 'red', 'yellow', 'blue', 'white'],
                            text: 'Background Colors:'
                        }
                    }
                },

                clipboard: {
                    matchers: [[Node.ELEMENT_NODE, function(node, delta) {
                        const opsList = [];
                        delta.ops.forEach(op => {
                            if (op.insert && typeof op.insert === 'string') {
                                opsList.push({
                                    insert: op.insert,
                                });
                            }
                        });
                        delta.ops = opsList;
                        return delta;
                    }]],
                },
            },
            theme: 'snow',
            placeholder: '请在此输入内容',
        });

        quill.setContents(this.state.reportDetail.main_content);

        //对应的图片评论
        $('#GearImageCommentBox').empty();
        this.getReportCommentList().then((res) => {
            $('#main-sections .gear-all-image').each(function () {
                // 根据图片的位置增加图片对应的评论框
                if ($(this).attr('comment_uid') && $(this).attr('comment_uid') != '') {
                    let top = $(this).position().top + 'px';
                    let className = 'img-' + $(this).attr('comment_uid');
                    // let nums = $(this).attr('nums') && $(this).attr('nums')!='' ? $(this).attr('nums') : 0;
                    let nums = res[$(this).attr('comment_uid')];

                    let commentDomPlan = `
                    <div class="gear-comment-box gear-comment-box-img ${className}"
                        comment_uid="${$(this).attr('comment_uid')}"
                        style="width: 270px;display: ${nums <= 0 ? 'none' : 'block'};left: -280px;top: ${top}"
                    >
                        <div style="display: flex;width: 100%;">
                            <div class="comment-box-num">
                                <div class="sanjiao"></div>
                                <span>${nums}</span>
                            </div>
                            <div class="comment-center">
                                <div style="display: flex;flex-direction: column">
                                    <div class="comment-center-list new-scroll-bar">
                                        
                                    </div>
                                    <div class="comment-center-text">
                                        <div class="gear-text-area"></div>
                                        <!--<textarea class="text-area"></textarea>-->
                                        <div class="text-foot clearfix">
                                            <button class="sed-btn">发送</button>
                                            <button class="cancel-btn" style="display: ${nums <= 0 ? 'inline' : 'none'}">删除</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    `;

                    $('#GearImageCommentBox').append($(commentDomPlan)[0]);
                }
            })
        })


        //quill输入时
        let that = this;
        quill.on('selection-change', function (range, oldRange, source) {
            //离开焦点
            if (!range) {
            } else {
                //对应的图片评论
                $('#GearImageCommentBox').empty();
                $('#main-sections .gear-all-image').each(function () {
                    // 根据图片的位置增加图片对应的评论框
                    if ($(this).attr('comment_uid') && $(this).attr('comment_uid') != '') {
                        let top = $(this).position().top + 'px';
                        let className = 'img-' + $(this).attr('comment_uid');
                        let nums = $(this).attr('nums') && $(this).attr('nums') != '' ? $(this).attr('nums') : 0;

                        let commentDomPlan = `
                            <div class="gear-comment-box gear-comment-box-img ${className}"
                                comment_uid="${$(this).attr('comment_uid')}"
                                style="width: 270px;display: ${nums <= 0 ? 'none' : 'block'};left: -280px;top: ${top}"
                            >
                                <div style="display: flex;">
                                    <div class="comment-box-num">
                                        <div class="sanjiao"></div>
                                        <span>${nums}</span>
                                    </div>
                                    <div class="comment-center">
                                        <div style="display: flex;flex-direction: column">
                                            <div class="comment-center-list new-scroll-bar">
                                                
                                            </div>
                                            <div class="comment-center-text">
                                                <div class="gear-text-area"></div>
                                                <!--<textarea class="text-area"></textarea>-->
                                                <div class="text-foot clearfix">
                                                    <button class="sed-btn">发送</button>
                                                    <button class="cancel-btn" style="display: ${nums <= 0 ? 'inline' : 'none'}">删除</button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            `;
                        $('#GearImageCommentBox').append($(commentDomPlan)[0]);
                    }
                })

                that.postData();
            }
        });

        initQuillIcon();
        initQuillKeyboard(quill);
    }

    // 调用获取当前报告编辑及查看用户列表的接口
    getEditUserLsit() {
        let that = this;
        let url = '/api/reports/pageview/users?report_uid=' + PageData.reportData.uid;
        commonRequest('GET', url, {}, (res) => {
            if (res.result) {
                that.setState({
                    editAndViewUsers: res.data,
                })
                if (!res.data.is_editable) {
                    that.setState({
                        savaState: '4'
                    })
                }
                setEdit(res.data.is_editable);
            } else {
            }
        })
    }


    //沟通时间
    communicateTime(value, dateString) {
        this.setState({
            time2: value.format("YYYY-MM-DD"),
        }, () => {
            this.postData();
        })
    }

    //沟通地点
    communicateAddres(e) {
        this.setState({
            address: $(e.target).val(),
        }, () => {
            this.postData();
        })
    }


    // 参会人员 右键菜单与操作
    historyVersion() {
        let that = this;
        $('.history-table').contextMenu({
            selector: '.edit-table-tr',
            items: {
                upInset: {
                    name: "上方插入一行",
                    callback: function (itemKey, opt, e) {
                        let tableData = that.state.tableData;
                        tableData.splice($(opt.$trigger).index(), 0, {
                            company: '',
                            name: '',
                            position: '',
                            contact: '',
                        });
                        that.setState({
                            tableData: tableData
                        })
                    }
                },
                downInset: {
                    name: "下方插入一行",
                    callback: function (itemKey, opt, e) {
                        let tableData = that.state.tableData;
                        tableData.splice($(opt.$trigger).index() + 1, 0, {
                            company: '',
                            name: '',
                            position: '',
                            contact: '',
                        });
                        that.setState({
                            tableData: tableData
                        })
                    }
                },
                del: {
                    name: "删除所在行",
                    callback: function (itemKey, opt, e) {
                        let tableData = that.state.tableData;
                        tableData.splice($(opt.$trigger).index(), 1);
                        that.setState({
                            tableData: tableData
                        }, () => {
                            that.postData();
                        })
                    },
                    disabled: function (key, opt) {
                        let tableData = that.state.tableData;
                        return tableData.length <= 1 ? true : false;
                    }
                },
            }
        });
    }

    //表格中的input改变
    histpryTrChange(key, index, e) {
        let tableData = this.state.tableData;
        tableData[index][key] = $(e.target).val();
        this.setState({
            tableData: tableData
        }, () => {
            this.postData();
        })
    }

    // 开关的点击
    clickSwitch(val) {
        let that = this;
        let keyObj = {};
        keyObj[val] = !this.state[val];
        that.setState(keyObj, () => {
            this.postData();
        })
    }


    //获取历史列表
    getHistoryData() {
        let url = '/api/reports/' + PageData.reportData.uid + '/histories';
        let that = this;
        commonRequest('GET', url, {}, (res) => {
            if (res.result) {
                that.setState({
                    historyData: res.data
                })

            } else {
            }
        })
    }

    //获取记录列表
    getRecordData() {
        let url = '/api/reports/' + PageData.reportData.uid + '/logs';
        let that = this;
        commonRequest('GET', url, {}, (res) => {
            if (res.result) {
                that.setState({
                    recordData: res.data
                })

            } else {
            }
        })
    }

    //标题
    changeTitle(e) {
        this.setState({
            title: $(e.target).val()
        }, () => {
            this.postData();
        })
    }


    //时间及金额预估 数据更新
    upDatePost(val) {
        let reportDetail = this.state.reportDetail;
        reportDetail.quotation_plans = val;
        this.setState({
            reportDetail: reportDetail,
            quotation_plans: val
        }, () => {
            this.postData();
        })
    }


    //点击编辑
    checkEdit() {
        this.setState({
            isEdit: !this.state.isEdit
        })
    }


    // 全局的tab切换与显示
    checkAllTab(val) {

        if (val == '1') {
            this.setState({
                isNewComment: false,
            })
            this.child.updateList()
        }

        if (val != this.state.showTab) {
            this.getHistoryData();
            this.getRecordData();
        }


        if (val != '2') {
            this.setState({
                activeHistoryId: '',
                showBox: false,
                showBoxDetail: '',
            })
        }

        this.setState({
            showTab: val,
        })
    }

    onRef(ref) {
        this.child = ref
    }

    onUpdateCommentList(commentCount) {
        this.setState({
            commentCount: commentCount
        })
    }


    // 提交所有数据
    postData() {

        this.setState({
            savaState: '1'
        })
        if (editTimeoutFun) {
            clearTimeout(editTimeoutFun);
        }
        editTimeoutFun = setTimeout(() => {

            let reportDetail = this.state.reportDetail;
            reportDetail.title = this.state.title;
            reportDetail.meeting_time = this.state.time2 ? moment(this.state.time2).format('YYYY-MM-DD') : null;
            reportDetail.meeting_place = this.state.address ? this.state.address : null;
            reportDetail.meeting_participants = this.state.tableData;

            // reportDetail.quotation_plans = clone(this.state.quotation_plans);
            reportDetail.quotation_plans = this.state.quotation_plans;
            reportDetail.show_plan = this.state.show_plan;
            reportDetail.show_company_about = this.state.show_company_about;
            reportDetail.show_company_clients = this.state.show_company_clients;
            reportDetail.main_content = quill.getContents();
            reportDetail.main_content_text = quill.getText();
            reportDetail.main_content_html = $('.ql-editor').html();

            reportDetail.return_page = this.state.return_page;
            // reportDetail.leave_page = this.state.leave_page;
            reportDetail.page_view_uuid = PageData.page_view_uuid;

            reportDetail.quotation_plan_price_unit = "万";


            this.setState({
                reportDetail: reportDetail,
            }, () => {
                let url = '/api/reports/' + PageData.reportData.uid + '/edit';
                let that = this;
                commonRequest('POST', url, this.state.reportDetail, (res) => {
                    // console.log('res',res)
                    if (res.result) {
                        that.setState({
                            return_page: false,
                            savaState: '2',
                            savaTime: res.data.updated_at,
                        })
                    } else {
                        if (res.status == 200) {
                            farmAlter(res.message, 2000);
                            that.getRepoetDetail();
                            /*that.setState({
                                savaState :'4'
                            })*/
                        } else {
                            that.setState({
                                savaState: '3'
                            })
                            farmAlter('网络或服务器错误', 2000);
                            that.getRepoetDetail();
                            setEdit(false)
                        }

                    }
                })
            })

        }, 1500);

    }


    // 点击历史的列表
    showBoxFun(item, e) {
        e.stopPropagation();
        e.preventDefault();

        this.setState({
            activeHistoryId: item.id,
            showBox: true,
            showBoxDetail: item.report_data,
        })
    }

    //点击还原
    revivification(item, e) {
        e.stopPropagation();
        e.preventDefault();

        let that = this;
        farmConfirm(
            '确认将报告还原到该版本吗？',
            function () {
                that.restoreHistory(item.id).then((res) => {

                    that.uploadData(res)

                    that.getRepoetDetail();
                    that.historyVersion();

                    that.setState({
                        showTab: '',
                        activeHistoryId: '',
                        showBox: false,
                        showBoxDetail: '',
                    })


                    // that.getReportCommentList();

                    // that.getHistoryData();
                    // that.getRecordData();
                })
            }
        )

    }

    //更新数据
    uploadData(data) {
        if (!data.meeting_participants || data.meeting_participants.length <= 0) {
            data.meeting_participants.push({
                company: '',
                name: '',
                position: '',
                contact: '',
            })
        }

        this.setState({
            reportDetail: data,

            title: data.title,
            tableData: data.meeting_participants,
            quotation_plans: data.quotation_plans,
            show_plan: data.show_plan,
            show_company_about: data.show_company_about,
            show_company_clients: data.show_company_clients,
        }, () => {
            this.initQuill();
        })
    }


    //还原该历史的报告
    restoreHistory(id) {
        return new Promise((resolve, reject) => {
            let url = '/api/reports/' + PageData.reportData.uid + '/histories/' + id + '/restore';
            commonRequest('POST', url, {
                page_view_uuid: PageData.page_view_uuid,
            }, (res) => {
                if (res.result) {
                    resolve(res.data)
                } else {
                    reject('err')
                }
            })

        });
    }


    //点击编辑弹框中的点击
    editModalClick(val) {
        if (val == '预览报告') {
            let openUrl = '/reports/' + PageData.reportData.uid + '/preview/';
            window.open(openUrl);
        }
        if (val == '克隆报告') {
            let createUrl1 = '/api/reports/create/lead_report/farm';
            let createReportData1 = {
                report_type: 'lead',
                lead: this.state.reportDetail.lead.id,
                source_report: PageData.reportData.id
            };
            commonRequest('POST', createUrl1, createReportData1, function (data) {
                if (data.result) {
                    let openUrl = '/reports/' + data.data.uid + '/edit/';
                    window.open(openUrl);
                } else {
                    farmAlter(data.message, 3000);
                }
            });
        }
        if (val == '删除报告') {
            farmConfirm(
                '确认删除该报告？不可还原',
                function () {
                    commonRequest('DELETE', "/api/reports/" + PageData.reportData.uid, {}, function (data) {
                        if (data.result) {
                            window.close();
                        } else {
                            farmAlter(data.message, 3000);
                        }
                    })
                }
            )
        }
        if (val == '撤销') {
            quill.focus();
            $('.ql-undo').click();
        }
        if (val == '重做') {
            quill.focus();
            $('.ql-redo').click();
        }

        if (val == '复制') {
        }
        if (val == '粘贴') {
        }
        if (val == '剪切') {
        }
        if (val == '全选') {
        }
    }

    onDateChange(index, date, dateStr) {
        let tableData = this.state.tableData;
        tableData[index]['date'] = dateStr;
        this.setState({
            tableData: tableData
        }, () => {
            this.postData();
        })
    }


    //显示添加与删除操作
    clickContrBtn(index, e) {
        $(e.target).parents('.contr-btn-box').parent().parent().siblings().find('.contr-btn-box').removeClass('checked');
        $(e.target).parents('.contr-btn-box').toggleClass('checked');
    }

    //添加与删除的操作
    contFun(index, flag) {
        let that = this;

        if (flag == 'upInset') {
            let tableData = that.state.tableData;
            tableData.splice(index, 0, {
                company: '',
                name: '',
                position: '',
                contact: '',
            });
            that.setState({
                tableData: tableData
            })
        }
        if (flag == 'downInset') {
            let tableData = that.state.tableData;
            tableData.splice(index + 1, 0, {
                company: '',
                name: '',
                position: '',
                contact: '',
            });
            that.setState({
                tableData: tableData
            })
        }
        if (flag == 'del') {
            let tableData = that.state.tableData;
            tableData.splice(index, 1);
            that.setState({
                tableData: tableData
            }, () => {
                that.postData();
            })
        }

        $('.contr-btn-box').removeClass('checked');
    }


    //
    showPublishReportModal() {
        this.setState({
            showPublishReportModal: true,
        })
    }

    closePublishModal() {
        this.setState({
            showPublishReportModal: false,
        })
    }

    publishReportSuccess(data) {
        this.setState({
            showPublishReportModal: false,
        });
        let reportUrl = data && data.report_url;
        window.location.href = reportUrl;
    }

    render() {
        //版本历史记录 - table
        let historyTrDom = this.state.tableData.map((item, index) => {
            return (
                <tr className="edit-table-tr" key={index}>
                    <td>
                        <div className='contr-btn-box'>
                            <div className='img-box' onClick={this.clickContrBtn.bind(this, index)}>
                                <img className='btn-click-contr' src="/static/new-report/img/btn-click-contr.svg"/>
                                <img className='btn-click-contr-active'
                                     src="/static/new-report/img/btn-click-contr-active.svg"/>
                            </div>
                            <div className='cont-list'>
                                <div onClick={this.contFun.bind(this, index, 'upInset')} className='cont-item'>上方插入一行
                                </div>
                                <div onClick={this.contFun.bind(this, index, 'downInset')}
                                     className='cont-item'>下方插入一行
                                </div>

                                {
                                    this.state.tableData.length <= 1
                                        ?
                                        <div className='cont-item disabled'>删除所在行</div>
                                        :
                                        <div onClick={this.contFun.bind(this, index, 'del')}
                                             className='cont-item'>删除所在行</div>
                                }

                            </div>
                        </div>
                        <input onChange={this.histpryTrChange.bind(this, 'company', index)}
                               className="table-input table-input-versions" type="text" value={item.company}
                               placeholder="公司名称"/>
                    </td>
                    <td>
                        <input onChange={this.histpryTrChange.bind(this, 'name', index)}
                               className="table-input table-input-versions" type="text" value={item.name}
                               placeholder="姓名"/>
                    </td>
                    <td>
                        <input onChange={this.histpryTrChange.bind(this, 'position', index)}
                               className="table-input table-input-name" type="text" value={item.position}
                               placeholder="职位"/>
                    </td>
                    <td>
                        <input onChange={this.histpryTrChange.bind(this, 'contact', index)}
                               className="table-input table-input-name" type="text" value={item.contact}
                               placeholder="请输入联系方式"/>
                    </td>
                </tr>
            )
        })

        //编辑人
        let editUserDom = ''
        if (this.state.editAndViewUsers && this.state.editAndViewUsers.editing_user && this.state.editAndViewUsers.editing_user != null) {
            editUserDom = (
                <div className="user-item">
                    {
                        this.state.editAndViewUsers.editing_user.avatar_url && this.state.editAndViewUsers.editing_user.avatar_url != ''
                            ? <AvatarImg size={30}
                                         imgUrl={this.state.editAndViewUsers.editing_user.avatar_url}/>
                            : <AvatarImg bgColor={this.state.editAndViewUsers.editing_user.avatar_color}
                                         size={30}
                                         text={
                                             this.state.editAndViewUsers.editing_user.username.substring(0, 1)
                                         }
                            />
                    }
                    <div className="user-info">
                        <div className="user-info-box">
                            {
                                this.state.editAndViewUsers.editing_user.avatar_url
                                    ? <AvatarImg size={40}
                                                 imgUrl={this.state.editAndViewUsers.editing_user.avatar_url}/>
                                    : <AvatarImg bgColor={this.state.editAndViewUsers.editing_user.avatar_color}
                                                 size={40}
                                                 text={this.state.editAndViewUsers.editing_user.username.substring(0, 1)}
                                    />
                            }
                            <div className="user-info-center">
                                <div className="user-info-name">
                                    {this.state.editAndViewUsers.editing_user.username}
                                </div>
                                <div className="user-info-email">
                                    {this.state.editAndViewUsers.editing_user.email}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )
        }


        // 观看用户列表
        let viewUsersData = (this.state.editAndViewUsers && this.state.editAndViewUsers.viewing_users && this.state.editAndViewUsers.viewing_users.length > 0) ? this.state.editAndViewUsers.viewing_users : [];
        let viewUsersDom = viewUsersData.map((item, index) => {
            return (
                <div className="user-item user-item-list" key={index} style={{zIndex: viewUsersData.length - index}}>
                    {
                        item.avatar_url
                            ? <AvatarImg size={30}
                                         imgUrl={item.avatar_url}/>
                            : <AvatarImg bgColor={item.avatar_color}
                                         size={30}
                                         text={item.username.substring(0, 1)}
                            />
                    }
                    <div className="user-info">
                        <div className="user-info-box">
                            {
                                item.avatar_url
                                    ? <AvatarImg size={40}
                                                 imgUrl={item.avatar_url}/>
                                    : <AvatarImg bgColor={item.avatar_color}
                                                 size={40}
                                                 text={item.username.substring(0, 1)}/>
                            }
                            <div className="user-info-center">
                                <div className="user-info-name">{item.username}</div>
                                <div className="user-info-email">{item.email}</div>
                            </div>
                        </div>
                    </div>
                </div>
            )
        })


        return (
            <div>

                {/*顶部*/}
                <div className="top-box clearfix">
                    <div className="top-box-left">
                        <span
                            className='top-proposal-name'>{PageData.reportData.lead ? PageData.reportData.lead.name : null}</span>

                        {
                            this.state.savaState == '1'
                                ?
                                <span className='save-loading'>
                                    <svg width="13px" height="13px" fill="#F7414A">
                                        <circle cx="6.5" cy="6.5" r="1.5"></circle>
                                        <path
                                            d="M12.9810552,7 C12.7257427,10.3562239 9.92161488,13 6.5,13 C3.07838512,13 0.274257251,10.3562239 0.0189448167,7 L1.02242151,7 C1.2750359,9.80325001 3.63097872,12 6.5,12 C9.36902128,12 11.7249641,9.80325001 11.9775785,7 L12.9810552,7 Z M12.9810552,6 L11.9775785,6 C11.7249641,3.19674999 9.36902128,1 6.5,1 C3.63097872,1 1.2750359,3.19674999 1.02242151,6 L0.0189448167,6 C0.274257251,2.64377614 3.07838512,0 6.5,0 C9.92161488,0 12.7257427,2.64377614 12.9810552,6 Z"></path>
                                    </svg>
                                    正在保存
                                </span>
                                : ''
                        }
                        {
                            this.state.savaState == '2'
                                ?
                                <span className='save-success'>
                                    <svg width="13px" height="13px" fill="none" stroke="#36B37E">
                                        <circle cy="6.5" r="6" cx="6.5"></circle>
                                        <path
                                            d="M4.3890873,6.59619408 L3.8890873,6.59619408 L4.3890873,7.09619408 L4.3890873,6.59619408 Z M4.3890873,6.59619408 L4.3890873,4.09619408 L3.8890873,4.59619408 L4.8890873,4.59619408 L4.3890873,4.09619408 L4.3890873,6.59619408 L9.8890873,6.59619408 L9.3890873,6.09619408 L9.3890873,7.09619408 L9.8890873,6.59619408 L4.3890873,6.59619408 Z"
                                            transform="translate(6.889087,6) rotate(-45.000000) translate(-6.889087, -5.596194) "></path>
                                    </svg>
                                    最近保存 {this.state.savaTime && this.state.savaTime != '' ? this.state.savaTime.split(' ')[1] : ''}
                                </span>
                                : ''
                        }
                        {
                            this.state.savaState == '3'
                                ?
                                <span className='save-err'>
                                    <svg width="13px" height="13px" fill="#F7414A">
                                        <path
                                            d="M0.196699141,2.19669914 C1.55393219,0.839466094 3.42893219,0 5.5,0 C7.57106781,0 9.44606781,0.839466094 10.8033009,2.19669914 L10.0961941,2.90380592 C8.91992544,1.72753728 7.29492544,1 5.5,1 C3.70507456,1 2.08007456,1.72753728 0.903805922,2.90380592 L0.196699141,2.19669914 Z M1.6109127,3.6109127 C2.60621694,2.61560847 3.98121694,2 5.5,2 C7.01878306,2 8.39378306,2.61560847 9.3890873,3.6109127 L8.68198052,4.31801948 C7.86764069,3.50367966 6.74264069,3 5.5,3 C4.25735931,3 3.13235931,3.50367966 2.31801948,4.31801948 L1.6109127,3.6109127 Z M3.02512627,5.02512627 C3.65850169,4.39175084 4.53350169,4 5.5,4 C6.46649831,4 7.34149831,4.39175084 7.97487373,5.02512627 L7.26776695,5.73223305 C6.81535594,5.27982203 6.19035594,5 5.5,5 C4.80964406,5 4.18464406,5.27982203 3.73223305,5.73223305 L3.02512627,5.02512627 Z M4.43933983,6.43933983 C4.71078644,6.16789322 5.08578644,6 5.5,6 C5.91421356,6 6.28921356,6.16789322 6.56066017,6.43933983 L5.5,7.5 L4.43933983,6.43933983 Z"
                                            transform="translate(1, 3)"></path>
                                    </svg>
                                    网络或服务器错误，请联系管理员
                                </span>
                                : ''
                        }

                        {
                            this.state.savaState == '4' && this.state.editAndViewUsers && this.state.editAndViewUsers.editing_user
                                ?
                                <span className='save-err'>
                                    <svg width="13px" height="13px" fill="#F7414A">
                                        <circle cx="6.5" cy="6.5" r="1.5"></circle>
                                        <path
                                            d="M12.9810552,7 C12.7257427,10.3562239 9.92161488,13 6.5,13 C3.07838512,13 0.274257251,10.3562239 0.0189448167,7 L1.02242151,7 C1.2750359,9.80325001 3.63097872,12 6.5,12 C9.36902128,12 11.7249641,9.80325001 11.9775785,7 L12.9810552,7 Z M12.9810552,6 L11.9775785,6 C11.7249641,3.19674999 9.36902128,1 6.5,1 C3.63097872,1 1.2750359,3.19674999 1.02242151,6 L0.0189448167,6 C0.274257251,2.64377614 3.07838512,0 6.5,0 C9.92161488,0 12.7257427,2.64377614 12.9810552,6 Z"></path>
                                    </svg>
                                    {this.state.editAndViewUsers.editing_user.username}正在编辑
                                </span>
                                : ''
                        }


                    </div>

                    <div className="top-box-right clearfix">


                        <div className="text-gray">
                            编辑人:
                        </div>

                        {editUserDom}

                        <div className='line'>|</div>

                        {
                            viewUsersData.length <= 5
                                ?
                                <div className='watch-user clearfix'>
                                    {viewUsersDom}
                                </div>
                                :
                                <div className='btn-more'>
                                    <div className='btn-more-pic'>
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                    </div>
                                    <div className='user-list-box'>
                                        {
                                            viewUsersData.map((item, index) => {
                                                return (
                                                    <div className='user-list-box-item' key={index}>
                                                        {
                                                            item.avatar_url
                                                                ? <AvatarImg size={24}
                                                                             imgUrl={item.avatar_url}/>
                                                                : <AvatarImg bgColor={item.avatar_color}
                                                                             size={24}
                                                                             text={item.username.substring(0, 1)}/>
                                                        }
                                                        {item.username}
                                                    </div>
                                                )
                                            })
                                        }
                                    </div>
                                </div>
                        }

                        <div
                            className="top-item-list yulan"
                            onClick={this.editModalClick.bind(this, '预览报告')}
                        >
                            预览报告
                        </div>

                        <div
                            className="top-item-list yulan"
                            onClick={this.showPublishReportModal.bind(this)}
                        >
                            发布报告
                        </div>


                        <div
                            className={this.state.isEdit ? "top-item-list top-item-list-edit active-tab" : "top-item-list top-item-list-edit"}
                            onClick={this.checkEdit.bind(this)}>
                            更多操作
                            {/*点击编辑时*/}
                            <ReactCSSTransitionGroup
                                transitionName="fadein"
                                transitionEnterTimeout={300}
                                transitionLeaveTimeout={200}>
                                {
                                    this.state.isEdit
                                        ?
                                        <div className='edit-modal'>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this, '克隆报告')}>
                                                <div className='left-text'>克隆报告</div>
                                                <div className='right-text'></div>
                                            </div>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this, '删除报告')}>
                                                <div className='left-text'>删除报告</div>
                                                <div className='right-text'></div>
                                            </div>
                                            <div className='edit-line'></div>
                                            <div className='edit-list' onClick={this.checkAllTab.bind(this, 2)}>
                                                <div className='left-text'>报告历史</div>
                                                <div className='right-text'></div>
                                            </div>
                                            <div className='edit-line'></div>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this, '撤销')}>
                                                <div className='left-text'>撤销</div>
                                                <div className='right-text'>⌘+Z</div>
                                            </div>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this, '重做')}>
                                                <div className='left-text'>重做</div>
                                                <div className='right-text'>⌘+Y</div>
                                            </div>
                                            {/*<div className='edit-line'></div>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this,'复制')}>
                                                <div className='left-text'>复制</div>
                                                <div className='right-text'>⌘+C</div>
                                            </div>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this,'粘贴')}>
                                                <div className='left-text'>粘贴</div>
                                                <div className='right-text'>⌘+V</div>
                                            </div>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this,'剪切')}>
                                                <div className='left-text'>剪切</div>
                                                <div className='right-text'>⌘+X</div>
                                            </div>
                                            <div className='edit-list' onClick={this.editModalClick.bind(this,'全选')}>
                                                <div className='left-text'>全选</div>
                                                <div className='right-text'>⌘+A</div>
                                            </div>*/}
                                        </div>
                                        : null
                                }
                            </ReactCSSTransitionGroup>

                        </div>

                        <div className={this.state.showTab == 1 ? "top-item-list active-tab" : "top-item-list"}
                             onClick={this.checkAllTab.bind(this, 1)}>
                            评论
                            {
                                this.state.isNewComment
                                    ?
                                    <div className='tip'></div>
                                    : ''
                            }


                        </div>
                        <div className={this.state.showTab == 3 ? "top-item-list active-tab" : "top-item-list"}
                             onClick={this.checkAllTab.bind(this, 3)}>记录
                        </div>
                    </div>

                </div>

                {/*顶部工具栏*/}
                <div className="toolbar-fixed">

                    <div id="toolbar" className="disabled">
                        <div className="tip-box">
                            <button className="ql-undo"></button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>撤销</div>
                                    <div>⌘+Z</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box">
                            <button className="ql-redo"></button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>重做</div>
                                    <div>⌘+Shift+Z</div>
                                </div>
                            </div>
                        </div>
                        <div className="vertical-line"></div>
                        <div className="tip-box long-btn">
                            <button className="ql-header ql-main long-btn" value="">正文</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>正文</div>
                                    <div>⌘+Shift+1</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box long-btn">
                            <button className="ql-header ql-title long-btn" value="2">标题</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>标题</div>
                                    <div>⌘+Shift+2</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box long-btn">
                            <button className="ql-header ql-title-small long-btn" value="3">小标题</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>小标题</div>
                                    <div>⌘+Shift+3</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box">
                            <button className="ql-bold">B</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>加粗</div>
                                    <div>⌘+B</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box">
                            <button type="button" className="ql-list ql-bullet" value="bullet"></button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>无序列表</div>
                                    <div>⌘+Shift+7</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box">
                            <button type="button" className="ql-list ql-ordered" value="ordered"></button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>有序列表</div>
                                    <div>⌘+Shift+L</div>
                                </div>
                            </div>
                        </div>
                        <div className="vertical-line"></div>
                        <div className="text">插入：</div>
                        <div className="tip-box">
                            <button className="ql-wireframe-image-btn">3</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>项目框架图</div>
                                    <div>空白行插入@</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box">
                            <button className="ql-mindmap-image-btn">4</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>项目思维导图</div>
                                    <div>空白行插入@</div>
                                </div>
                            </div>
                        </div>
                        {/*<div className="tip-box">
                            <button className="ql-image">5</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>上传图片</div>
                                    <div>空白行插入@</div>
                                </div>
                            </div>
                        </div>*/}
                        <div className="tip-box">
                            <button className="ql-image-model-btn">6</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>上传图片</div>
                                    <div>空白行插入@</div>
                                </div>
                            </div>
                        </div>
                        <div className="tip-box">
                            <button className="ql-insert-table-btn">7</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>插入表格</div>
                                    <div>空白行插入@</div>
                                </div>
                            </div>
                        </div>
                        <div className="vertical-line"></div>
                        <div className="text">评论：</div>
                        <div className="tip-box">
                            <button className="ql-comment">6</button>
                            <div className="tip-box-bg">
                                <div className="tip-box-triangle"></div>
                                <div className="tip-box-text">
                                    <div>评论</div>
                                </div>
                            </div>
                        </div>

                        <div className="disabled-box"></div>
                    </div>
                </div>


                {/*内容*/}
                <div className='report-container new-scroll-bar'>
                    <div className="edit-report-container" style={{display: this.state.showBox ? 'none' : 'block'}}>

                        {/*标题*/}
                        <input className="edit-title" type="text" value={this.state.title}
                               onChange={this.changeTitle.bind(this)} placeholder="未命名反馈报告"/>

                        <div className="leads-info">
                            <span>
                                制作时间：
                                {simpleDateStr(this.state.reportDetail.created_date, true)}
                            </span>
                            <span className='communicate-time'>
                                沟通时间：
                                <ConfigProvider locale={zhCN}>
                                    <DatePicker
                                        placeholder="请选择时间"
                                        onChange={this.communicateTime.bind(this)}
                                        format={'YYYY.M.D'}
                                        value={isValidValue(this.state.time2) ? moment(this.state.time2) : null}
                                    />
                                </ConfigProvider>
                            </span>
                            <span className='communicate-addres'>
                                沟通地点：
                                <input type="text" placeholder='请输入地址'
                                       value={this.state.address && this.state.address != '' ? this.state.address : ''}
                                       onChange={this.communicateAddres.bind(this)}
                                />
                            </span>
                        </div>

                        <hr className="edit-hr"/>

                        {/*参与人员*/}
                        <div className="center-list-box history" id="version_content-section">
                            <div className="item-title">
                                <span className="text">参与人员</span>
                            </div>

                            <table className="edit-table history-table">
                                <thead>
                                <tr>
                                    <th style={{width: '270px'}}>公司名称</th>
                                    <th>姓名</th>
                                    <th style={{width: '164px'}}>职位</th>
                                    <th style={{width: '184px'}}>联系方式</th>
                                </tr>
                                </thead>
                                <tbody className="history-table-tbody">
                                {historyTrDom}
                                </tbody>
                            </table>
                        </div>

                        {/*富文本编辑器*/}
                        <div className="main-sections" id="main-sections"></div>

                        {/*时间及金额预估*/}
                        <div className="center-list-box time-money-estimate" id="TimePriceSection">

                            <TimePriceSection
                                reportTitle={this.state.title}
                                allCommentData={this.state.allCommentData}
                                show_plan={this.state.show_plan}
                                quotation_plans={this.state.quotation_plans}
                                clickSwitch={this.clickSwitch.bind(this, 'show_plan')}
                                upDatePost={this.upDatePost.bind(this)}
                                reportDetail={this.state.reportDetail}
                            />
                        </div>

                        {/*关于齿轮*/}
                        <div className="center-list-box service-scope" id="service-scope-section">
                            <div className="item-title clearfix">
                                <span className="text">关于齿轮</span>
                                <div className="switch-container">
                                    <input type="checkbox" className="switch-input"
                                           checked={this.state.show_company_about}
                                           onChange={this.clickSwitch.bind(this, 'show_company_about')}/>
                                    <div className="switch-bg"
                                         onClick={this.clickSwitch.bind(this, 'show_company_about')}></div>
                                    <div className="switch-tip">
                                        <div className="switch-tip-triangle"></div>
                                        <div className="switch-tip-text">
                                            在报告中{this.state.show_company_about ? '隐藏' : '显示'}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div>
                                <p>
                                    齿轮易创为企业提供一体化产品技术解决方案，从商业诉求、行业态势、用户行为等不同角度，帮助客户进行需求梳理和产品规划，将互联网技术与客户实际业务相结合，推动产品等快速落地，满足企业多样化需求。目前齿轮易创已为包括亚马逊、印象笔记、格理集团、Visa等200+企业提供软件定制服务与产品咨询
                                </p>
                                <div className="service-items">
                                    <div className="service-item">
                                        <div className="about-item">
                                            <img src="/static/new-report/img/tdhzz.svg"/>
                                            <p>团队和资质</p>
                                            <div>齿轮易创团队来自大数据、人工智能IT咨询、产品开发等多个行业，具有资深的产品和项目开发经验</div>
                                        </div>
                                    </div>
                                    <div className="service-item">
                                        <div className="about-item">
                                            <img src="/static/new-report/img/djtzjg.svg"/>
                                            <p>顶级投资机构投资</p>
                                            <div>真格基金、青锐创投</div>
                                        </div>
                                    </div>
                                    <div className="service-item">
                                        <div className="about-item">
                                            <img src="/static/new-report/img/zzrz.svg"/>
                                            <p>资质认证</p>
                                            <div>高新技术企业、IOS国际质量认证、软件著作权</div>
                                        </div>
                                    </div>
                                    <div className="service-item">
                                        <div className="about-item">
                                            <img src="/static/new-report/img/jxry.svg"/>
                                            <p>奖项荣誉</p>
                                            <div>福布斯30U30精英、达沃斯经济论坛杰出青年、新锐企业服务商</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {
                                this.state.show_company_about
                                    ?
                                    null
                                    :
                                    <div className="masking-bg"></div>
                            }
                        </div>

                        {/*我们的客户*/}
                        <div className="center-list-box next-plan" id="next-step-section">
                            <div className="item-title clearfix">
                                <span className="text">我们的客户</span>
                                <div className="switch-container">
                                    <input type="checkbox" className="switch-input"
                                           checked={this.state.show_company_clients}
                                           onChange={this.clickSwitch.bind(this, 'show_company_clients')}/>
                                    <div className="switch-bg"
                                         onClick={this.clickSwitch.bind(this, 'show_company_clients')}></div>
                                    <div className="switch-tip">
                                        <div className="switch-tip-triangle"></div>
                                        <div className="switch-tip-text">
                                            在报告中{this.state.show_company_clients ? '隐藏' : '显示'}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <section className="clearfix next-section">
                                <img className='client-img' src="/static/reports/images/report-view/demo-img-pc.png"/>
                            </section>

                            {
                                this.state.show_company_clients
                                    ?
                                    null
                                    :
                                    <div className="masking-bg"></div>
                            }
                        </div>

                    </div>
                </div>


                {/*思维导图弹框*/}
                <div id="MindMapComment">
                    <MindMapComment title={this.state.title}/>
                </div>

                {/*全部的弹框*/}
                <div className='all-modal-div' style={{display: this.state.showTab != '' ? 'block' : 'none'}}>
                    <div className='all-modal-bg' onClick={this.checkAllTab.bind(this, '')}></div>
                    <div className='all-modal'>
                        <div className='modal-tab-div'>
                            <div className='modal-tab-div-center clearfix'>
                                {
                                    this.state.showTab == 2
                                        ?
                                        <div className={this.state.showTab == 2 ? "tab-list active" : "tab-list"}
                                             onClick={this.checkAllTab.bind(this, 2)}>
                                            <div className="tab-item">报告历史</div>
                                        </div>
                                        :
                                        <div>
                                            <div className={this.state.showTab == 1 ? "tab-list active" : "tab-list"}
                                                 onClick={this.checkAllTab.bind(this, 1)}>
                                                <div className="tab-item">评论(<span>{this.state.commentCount}</span>)
                                                </div>
                                            </div>
                                            <div className={this.state.showTab == 3 ? "tab-list active" : "tab-list"}
                                                 onClick={this.checkAllTab.bind(this, 3)}>
                                                <div className="tab-item">记录</div>
                                            </div>
                                        </div>
                                }


                                <div className="close-tab-btn" onClick={this.checkAllTab.bind(this, '')}>✕</div>
                            </div>
                        </div>
                        <div className='modal-center'>
                            <div style={{display: this.state.showTab == 2 ? 'block' : 'none'}}>
                                <div className='history-div new-scroll-bar'>
                                    {
                                        this.state.historyData.map((item, index) => {
                                            return (
                                                <div
                                                    className={this.state.activeHistoryId == item.id ? 'h-item-list active' : 'h-item-list'}
                                                    key={index} onClick={this.showBoxFun.bind(this, item)}>
                                                    <div className='h-time'>{simpleDateStr(item.created_at, true)}</div>
                                                    <div className='h-name'>{item.author.username} 第{item.number}版</div>
                                                    {
                                                        item.remarks && item.remarks != ''
                                                            ? <div className='h-name'>{item.remarks}</div>
                                                            : null
                                                    }
                                                    <div className='h-btn'
                                                         onClick={this.revivification.bind(this, item)}>还原
                                                    </div>
                                                </div>
                                            )
                                        })
                                    }
                                </div>
                            </div>

                            <div style={{display: this.state.showTab == 1 ? 'block' : 'none'}}>
                                {/*报告全局评论*/}
                                <Review
                                    pointCommentData={this.state.pointCommentData}
                                    ref='reviewDom'
                                    objectName={'报告：' + PageData.reportData.title}
                                    urlList={{getListUrl: '/api/comments/', submitUrl: '/api/comments/'}}
                                    params={{
                                        app_label: 'reports',
                                        model: 'report',
                                        object_id: PageData.reportData.id,
                                        order_by: 'created_at',
                                        order_dir: 'desc'
                                    }}
                                    requestData={{
                                        app_label: 'reports',
                                        model: 'report',
                                        object_id: PageData.reportData.id,
                                    }}
                                    onUpdateCommentList={this.onUpdateCommentList.bind(this)}
                                    onRef={this.onRef.bind(this)}
                                />
                            </div>

                            <div style={{display: this.state.showTab == 3 ? 'block' : 'none'}}>
                                <RecordBox
                                    recordData={this.state.recordData}
                                />
                                {/*<div className='record-div'>

                                    {
                                        this.state.recordData.map((item, index) => {
                                            var comment = null;
                                            if(item.content_data.comment){
                                                comment = (<div className='flag-left'>备注:{item.content_data.comment}</div>)
                                            }
                                            return (
                                                <div className='record-list' key={index}>
                                                    <div className='record-list-user clearfix'>
                                                        {
                                                            item.operator.avatar_url
                                                                ? <AvatarImg style={{top: '-1px'}} size={20}
                                                                             imgUrl={item.operator.avatar_url}/>
                                                                : <AvatarImg bgColor={item.operator.avatar_color}
                                                                             style={{top: '-1px'}}
                                                                             size={24}
                                                                             text={item.operator.username.substring(0, 1)}/>
                                                        }
                                                        <span className='name'>{item.operator.username}</span>
                                                        <span
                                                            className='time'>{simpleDateStr(item.updated_at, true)}</span>
                                                    </div>
                                                    <div className='center-text'>
                                                        <div className='flag-text clearfix'>
                                                            <div className='flag-left'>{item.content_data.title}:{item.content_data.subtitle}</div>
                                                            {comment}
                                                        </div>
                                                        {
                                                            item.content_data.fields.map((item2, index2) => {
                                                                return (
                                                                    <RecordList data={item2} key={index2} num={index2}/>
                                                                )
                                                            })
                                                        }

                                                    </div>
                                                </div>
                                            )
                                        })
                                    }

                                </div>*/}
                            </div>
                        </div>
                    </div>
                </div>


                {/*报告展示*/}
                {
                    this.state.showBoxDetail && this.state.showBoxDetail != ''
                        ?
                        <div className='show-box' style={{display: this.state.showBox ? 'block' : 'none'}}>
                            <div className='title'>{this.state.showBoxDetail.title}</div>

                            <div className="leads-info">
                                <span>
                                    制作时间：
                                    {/*{this.state.time1}*/}
                                    {simpleDateStr(this.state.showBoxDetail.created_date, true)}
                                </span>
                                <span className='communicate-time'>
                                    沟通时间：
                                    {simpleDateStr(this.state.showBoxDetail.meeting_time, true)}
                                    {/*<ConfigProvider locale={zhCN}>
                                        <DatePicker
                                            showTime
                                            placeholder="请选择时间"
                                            onChange={this.communicateTime.bind(this)}
                                            format={'YYYY-MM-DD'}
                                            value={isValidValue(this.state.time2) ? moment(this.state.time2, 'YYYY.M.D') : null}
                                        />
                                    </ConfigProvider>*/}
                                </span>
                                <span className='communicate-addres'>
                                    沟通地点：
                                    {this.state.showBoxDetail.meeting_place}
                                    {/*<input type="text" placeholder='请输入地址'
                                           onChange={this.communicateAddres.bind(this)}
                                           value={this.state.address}
                                    />*/}
                                </span>
                            </div>

                            <hr className="edit-hr"/>

                            <div className="center-list-box history" id="version_content-section">
                                <div className="item-title"><span className="text">历史版本</span></div>
                                <table className="edit-table">
                                    <thead>
                                    <tr>
                                        <th>公司名称</th>
                                        <th>姓名</th>
                                        <th>职位</th>
                                        <th>联系方式</th>
                                    </tr>
                                    </thead>
                                    <tbody className="history-table-tbody">
                                    {
                                        this.state.showBoxDetail.meeting_participants.map((item, index) => {
                                            return (
                                                <tr className="edit-table-tr" key={index}>
                                                    <td>{item.company}</td>
                                                    <td>{item.name}</td>
                                                    <td>{item.position}</td>
                                                    <td>{item.contact}</td>
                                                </tr>
                                            )
                                        })
                                    }

                                    </tbody>
                                </table>
                            </div>

                            <div className='edit-center'>
                                <div
                                    dangerouslySetInnerHTML={{__html: this.state.showBoxDetail.main_content_html}}></div>
                            </div>

                            {
                                this.state.showBoxDetail.show_plan
                                    ?
                                    <div className="center-list-box time-money-estimate">
                                        <div>
                                            <div className="item-title clearfix"><span className="text">时间及金额预估</span>
                                            </div>
                                            {
                                                this.state.showBoxDetail.quotation_plans.map((item, index) => {
                                                    return (
                                                        <div className="estimate-box" key={index}>
                                                            <div className="estimate-item">
                                                                <div className="estimate-item-title">{item.title}</div>
                                                                <div className="estimate-item-list">
                                                                    <div className="estimate-item-list-left">报价估算：</div>
                                                                    <div
                                                                        className="estimate-item-list-right">{item.price}</div>
                                                                </div>
                                                                <div className="estimate-item-list">
                                                                    <div className="estimate-item-list-left">预计工期：</div>
                                                                    <div
                                                                        className="estimate-item-list-right">{item.period}</div>
                                                                </div>
                                                                <div className="estimate-item-list">
                                                                    <div className="estimate-item-list-left">项目包含：</div>
                                                                    <div
                                                                        className="estimate-item-list-right">{item.projects}</div>
                                                                </div>
                                                                <div className="estimate-item-list">
                                                                    <div className="estimate-item-list-left">服务范围：</div>
                                                                    <div
                                                                        className="estimate-item-list-right">{item.services}</div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    )
                                                })
                                            }


                                        </div>
                                    </div>
                                    : ''
                            }

                            {
                                this.state.showBoxDetail.show_company_about
                                    ?
                                    <div className="center-list-box service-scope" id="service-scope-section">
                                        <div className="item-title clearfix">
                                            <span className="text">关于齿轮</span>
                                        </div>

                                        <div>
                                            <p>
                                                齿轮易创为企业提供一体化产品技术解决方案，从商业诉求、行业态势、用户行为等不同角度，帮助客户进行需求梳理和产品规划，将互联网技术与客户实际业务相结合，推动产品等快速落地，满足企业多样化需求。目前齿轮易创已为包括亚马逊、印象笔记、格理集团、Visa等200+企业提供软件定制服务与产品咨询
                                            </p>
                                            <div className="service-items">
                                                <div className="service-item">
                                                    <div className="about-item">
                                                        <img src="/static/new-report/img/tdhzz.svg"/>
                                                        <p>团队和资质</p>
                                                        <div>齿轮易创团队来自大数据、人工智能IT咨询、产品开发等多个行业，具有资深的产品和项目开发经验</div>
                                                    </div>
                                                </div>
                                                <div className="service-item">
                                                    <div className="about-item">
                                                        <img src="/static/new-report/img/djtzjg.svg"/>
                                                        <p>顶级投资机构投资</p>
                                                        <div>真格基金、青锐创投</div>
                                                    </div>
                                                </div>
                                                <div className="service-item">
                                                    <div className="about-item">
                                                        <img src="/static/new-report/img/zzrz.svg"/>
                                                        <p>资质认证</p>
                                                        <div>高新技术企业、IOS国际质量认证、软件著作权</div>
                                                    </div>
                                                </div>
                                                <div className="service-item">
                                                    <div className="about-item">
                                                        <img src="/static/new-report/img/jxry.svg"/>
                                                        <p>奖项荣誉</p>
                                                        <div>福布斯30U30精英、达沃斯经济论坛杰出青年、新锐企业服务商</div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                    </div>
                                    : ''
                            }

                            {
                                this.state.showBoxDetail.show_company_clients
                                    ?
                                    <div className="center-list-box next-plan" id="next-step-section">
                                        <div className="item-title clearfix">
                                            <span className="text">我们的客户</span>
                                        </div>

                                        <section className="clearfix next-section">
                                            <img className='client-img' src="/static/reports/images/report-view/demo-img-pc.png"/>
                                        </section>

                                    </div>
                                    : ''
                            }


                        </div>
                        : null
                }
                {
                    this.state.showPublishReportModal &&
                    <ReportTagsModal
                        title={'发布报告'}
                        closeModal={this.closePublishModal.bind(this)}
                        onSuccess={this.publishReportSuccess.bind(this)}
                        visible={this.state.showPublishReportModal}
                        data={this.state.reportDetail}
                        flag={"publishReport"}
                    />
                }
                <GuideModal/>


            </div>
        )
    }
}

//记录列表
class RecordBox extends React.Component {
    constructor() {
        super();
        this.state = {}
    }

    componentDidMount() {
    }

    componentDidUpdate() {
        this.refs.recordDiv.scrollTop = this.refs.recordDiv.scrollHeight;
    }


    render() {
        return (
            <div className='record-div' ref='recordDiv'>
                {
                    this.props.recordData.map((item, index) => {
                        var comment = null;
                        if (item.content_data.comment) {
                            comment = (<div className='flag-left'>备注:{item.content_data.comment}</div>)
                        }
                        return (
                            <div className='record-list' key={index}>
                                <div className='record-list-user clearfix'>
                                    {
                                        item.operator.avatar_url
                                            ? <AvatarImg style={{top: '-1px'}} size={20}
                                                         imgUrl={item.operator.avatar_url}/>
                                            : <AvatarImg bgColor={item.operator.avatar_color}
                                                         style={{top: '-1px'}}
                                                         size={24}
                                                         text={item.operator.username.substring(0, 1)}/>
                                    }
                                    <span className='name'>{item.operator.username}</span>
                                    <span
                                        className='time'>{simpleDateStr(item.updated_at, true)}</span>
                                </div>
                                <div className='center-text'>
                                    <div className='flag-text clearfix'>
                                        <div
                                            className='flag-left'>{item.content_data.title}:{item.content_data.subtitle}</div>
                                        {comment}
                                    </div>
                                    {
                                        item.content_data.fields.map((item2, index2) => {
                                            return (
                                                <RecordList data={item2} key={index2} num={index2}/>
                                            )
                                        })
                                    }

                                </div>
                            </div>
                        )
                    })
                }

            </div>
        );
    }
}

//列表中记录
class RecordList extends React.Component {
    constructor() {
        super();
        this.state = {
            height: 0
        }
    }

    componentDidMount() {
        this.setState({
            height: this.refs.selfdom && this.refs.selfdom.offsetHeight ? this.refs.selfdom.offsetHeight : 0
        })
    }

    componentDidUpdate() {
        let height = this.refs.selfdom && this.refs.selfdom.offsetHeight ? this.refs.selfdom.offsetHeight : 0
        if (this.state.height != height) {
            this.setState({
                height: this.refs.selfdom && this.refs.selfdom.offsetHeight ? this.refs.selfdom.offsetHeight : 0
            })
        }

    }

    setBgDiv() {
        $(this.refs.selfdom).toggleClass('is-bg');
    }

    render() {
        let op_dict = {'update': '修改', 'insert': '新增', 'delete': '删除'};
        let item2 = this.props.data;
        let dom = (<div>null</div>);
        let typeName = item2.name;
        let verboseName = item2.verbose_name;
        let isBgClass = this.state.height >= 80 ? 'is-bg' : '';
        let title = op_dict[item2.type] + ' ' + verboseName;
        let plan_fields = [{'name': 'price', 'verbose_name': '报价估算'}, {
            'name': 'period',
            'verbose_name': '预计工期'
        }, {'name': 'projects', 'verbose_name': '项目包含'}, {'name': 'services', 'verbose_name': '服务范围'}];
        if (typeName == 'title') {
            dom = (
                <div className={'item-text record-list-text ' + isBgClass} ref='selfdom'>
                    {
                        this.state.height >= 80
                            ? <div className='xianshi-ben' onClick={this.setBgDiv.bind(this)}></div>
                            : ''
                    }
                    <div className='list-title'>
                        {title}
                    </div>
                    {
                        item2.type == 'update'
                            ?
                            <div>
                                <span className='new-text'>{item2.new_value}</span>
                                <div className='old-text'>{item2.old_value}</div>
                            </div>
                            :
                            <div>
                                <span className={item2.type == 'insert' ? 'new-text' : 'old-text'}>{item2.value}</span>
                            </div>
                    }
                    <div className='bg-div'></div>
                </div>
            )
        } else if (typeName == 'main_content_html') {
            dom = (
                <div className={'item-text record-list-text ' + isBgClass} ref='selfdom'>
                    {
                        this.state.height >= 80
                            ? <div className='xianshi-ben' onClick={this.setBgDiv.bind(this)}></div>
                            : ''
                    }
                    <div className='list-title'>
                        {title}
                    </div>
                    <div dangerouslySetInnerHTML={{__html: item2.diff_result}}></div>

                    <div className='bg-div'></div>
                </div>

            )
        }

        /*else if (typeName == 'meeting_participants') {
            dom = (
                <RecordHistoryVersion data={item2}/>
            )
        }*/

        else if (typeName == 'quotation_plan') {
            dom = (
                <div className={'item-text record-list-plan ' + isBgClass} ref='selfdom'>
                    {
                        this.state.height >= 80
                            ? <div className='xianshi-ben' onClick={this.setBgDiv.bind(this)}></div>
                            : ''
                    }
                    <div className='plan-center'>
                        <div className='center-align'>
                            {
                                item2.type == 'update'
                                    ?
                                    <div>
                                        <span className='new-text'>{item2.new_value.title}</span>
                                        <span className='old-text'>{item2.old_value.title}</span>
                                    </div>
                                    :
                                    <span
                                        className={item2.type == 'insert' ? 'new-text' : 'old-text'}>{item2.value.title}</span>
                            }

                        </div>
                        {
                            plan_fields.map((item, index) => {
                                var name = item['name'];
                                var verbose_name = item['verbose_name'];
                                return (
                                    <div className='item-plan' key={index}>
                                        <div className='item-p-l'>{verbose_name}：</div>
                                        <div className='item-p-r'>
                                            {
                                                item2.type == 'update'
                                                    ? item2.old_value[name] != item2.new_value[name] ?
                                                    <div>
                                                        <span className='new-text'>{item2.new_value[name]}</span>
                                                        <span className='old-text'>{item2.old_value[name]}</span>
                                                    </div>
                                                    : <div>
                                                        <span className=''>{item2.new_value[name]}</span>
                                                    </div>
                                                    :
                                                    <span
                                                        className={item2.type == 'insert' ? 'new-text' : 'old-text'}>{item2.value[name]}</span>
                                            }
                                        </div>
                                    </div>
                                )
                            })
                        }
                    </div>

                    <div className='bg-div'></div>
                </div>
            )
        } else if (['show_company_clients', 'show_company_about', 'show_plan', 'show_company_about', 'show_company_clients'].includes(typeName)) {
            dom = (
                <div className={'item-text record-list-text ' + isBgClass} ref='selfdom'>
                    {
                        this.state.height >= 80
                            ? <div className='xianshi-ben' onClick={this.setBgDiv.bind(this)}></div>
                            : ''
                    }
                    <span>{item2.new_value ? '显示' : '隐藏'}</span>
                    <span>{item2.verbose_name}</span>
                </div>
            )
        } else if (typeName == 'image') {
            typeName = '图片';
            if (item2.value.flag == 'mindmap') {
                verboseName = '思维导图'
            }
            if (item2.value.flag == 'wireframe') {
                verboseName = '框架图'
            }
            title = op_dict[item2.type] + ' ' + verboseName;
            dom = (
                <div className={'item-text record-list-image ' + isBgClass} ref='selfdom'>
                    {
                        this.state.height >= 80
                            ? <div className='xianshi-ben' onClick={this.setBgDiv.bind(this)}></div>
                            : ''
                    }

                    <div className='list-title'>
                        {title}
                    </div>

                    <img className='image-pic' src={item2.value.src}/>
                    <div className='bg-div'></div>
                </div>
            )
        } else {
            dom = (
                <div className={'item-text record-list-text ' + isBgClass} ref='selfdom'>
                    {
                        this.state.height >= 80
                            ? <div className='xianshi-ben' onClick={this.setBgDiv.bind(this)}></div>
                            : ''
                    }
                    <div className='list-title'>
                        {title}
                    </div>
                    {
                        item2.type == 'update'
                            ?
                            <div>
                                <span className='new-text'>{item2.new_value}</span>
                                <div className='old-text'>{item2.old_value}</div>
                            </div>
                            :
                            <div>
                                <span className={item2.type == 'insert' ? 'new-text' : 'old-text'}>{item2.value}</span>
                            </div>
                    }
                    <div className='bg-div'></div>
                </div>
            )
        }

        return dom;

    }
}

//列表中记录 历史版本
class RecordHistoryVersion extends React.Component {
    constructor() {
        super();
        this.state = {
            height: 0
        }
    }

    componentDidMount() {
        this.setState({
            height: this.refs.selfdom && this.refs.selfdom.offsetHeight ? this.refs.selfdom.offsetHeight : 0
        })
    }

    componentDidUpdate() {
        let height = this.refs.selfdom && this.refs.selfdom.offsetHeight ? this.refs.selfdom.offsetHeight : 0
        if (this.state.height != height) {
            this.setState({
                height: this.refs.selfdom && this.refs.selfdom.offsetHeight ? this.refs.selfdom.offsetHeight : 0
            })
        }
    }

    setBgDiv() {
        $(this.refs.selfdom).toggleClass('is-bg');
    }

    render() {
        let data = this.props.data;
        let trList = [];
        let version_fields = ['version', 'date', 'author'];
        let field_styles = {
            'version': {width: '36px', wordWrap: 'break-word'},
            'date': {width: '75px', wordWrap: 'break-word'},
            'author': {width: '65px', wordWrap: 'break-word'}
        };
        var new_value = data.new_value;
        var old_value = data.old_value;
        var max_length = new_value.length > old_value.length ? new_value.length : old_value.length;
        if (data.type == "update") {
            for (var index = 0; index < max_length; index++) {
                var td_lists = [];
                for (var i = 0; i < version_fields.length; i++) {
                    var field_name = version_fields[i];
                    var field_new_value = isValidValue(new_value[index]) && isValidValue(new_value[index][field_name]) ? new_value[index][field_name] : '';
                    var field_old_value = isValidValue(old_value[index]) && isValidValue(old_value[index][field_name]) ? old_value[index][field_name] : '';
                    var td_item = null;
                    if (field_new_value == field_old_value) {
                        td_item = (<td key={i}>
                            <div style={field_styles[field_name]}>
                                <span className=''>{field_new_value}</span>
                            </div>
                        </td>)
                    } else {
                        td_item = (<td key={i}>
                            <div style={field_styles[field_name]}>
                                <span className='new-text'>{field_new_value}</span>
                                <span className='old-text'>{field_old_value}</span>
                            </div>
                        </td>)
                    }
                    td_lists.push(td_item)
                }
                var version_data = (
                    <tr key={index}>
                        {td_lists}
                    </tr>
                );
                trList.push(version_data)
            }

        } else {
            trList = data.value.map((item, index) => {
                return (
                    <tr key={index}>
                        <td>
                            <div style={{width: '36px', wordWrap: 'break-word'}}>
                                <span
                                    className={data.type == 'insert' ? 'new-text' : 'old-text'}>{isValidValue(item.version) ? item.version : ''}</span>
                            </div>
                        </td>
                        <td>
                            <div style={{width: '75px', wordWrap: 'break-word'}}>
                                <span
                                    className={data.type == 'insert' ? 'new-text' : 'old-text'}>{isValidValue(item.date) ? item.date : ''}</span>
                            </div>
                        </td>
                        <td>
                            <div style={{width: '65px', wordWrap: 'break-word'}}>
                                <span
                                    className={data.type == 'insert' ? 'new-text' : 'old-text'}>{isValidValue(item.author) ? item.author : ''}</span>
                            </div>
                        </td>
                    </tr>
                )
            })
        }


        let isBgClass = this.state.height >= 80 ? 'is-bg' : '';
        return (
            <div className={'item-text record-list-history ' + isBgClass} ref='selfdom'>
                {
                    this.state.height >= 80
                        ?
                        <div className='xianshi-ben' onClick={this.setBgDiv.bind(this)}></div>
                        : ''
                }

                <div className='history-center'>
                    <div className='list-title'>
                        {data.type == 'update' ? '更改 版本历史' : ''}
                        {data.type == 'insert' ? '新增 版本历史' : ''}
                        {data.type == 'delete' ? '删除 版本历史' : ''}
                    </div>
                    <table>
                        <thead>
                        <tr>
                            <th>版本</th>
                            <th>日期</th>
                            <th>制作人</th>
                        </tr>
                        </thead>
                        <tbody>
                        {trList}
                        </tbody>
                    </table>
                </div>

                <div className='bg-div'></div>
            </div>
        )
    }
}

//思维导图弹框
class MindMapComment extends React.Component {
    constructor(props) {
        super(props);
        this.state = {

            nums: 0, //评论个数
            uid: '',

        };
    }

    componentDidMount() {

        let that = this;

        $('#main-sections').on('click', '.img-tip-type-mindmap .tip-show-big', function (e) {
            let uid = $('.gear-all-image.active').attr('comment_uid');
            if (!uid || uid == '') {

                //获取UID
                let url = '/api/reports/' + PageData.reportData.uid + '/comment_points';
                commonRequest('POST', url, {}, (res) => {
                    if (res.result) {
                        //根据UID获取评论列表
                        let url = '/api/reports/comment_points/' + res.data.uid;
                        commonRequest('GET', url, {}, (res) => {
                            if (res.result) {
                                that.setState({
                                    uid: res.data.uid
                                })
                                $('.gear-all-image.active').attr('comment_uid', res.data.uid);

                                //图片添加颜色标示
                                $('.gear-all-image.active').attr('class', 'gear-all-image normal-image active tag-select-yellow');
                                $('.check-tag').attr('class', 'check-tag tag-select-yellow');
                                $('.tag-item.tag-select-yellow').addClass('active').siblings().removeClass('active');

                            }
                        })

                    }
                })

            } else {
                that.setState({
                    uid: $('.gear-all-image.active').attr('comment_uid')
                })
                that.child.getCommentList()
            }
        })
    }

    onRef(ref) {
        this.child = ref
    }

    onUpdateCommentList(val) {
        this.setState({
            nums: val
        });
        $('.gear-all-image.active').attr('nums', val);
        let className = 'img-' + $('.gear-all-image.active').attr('comment_uid');
        $('.gear-comment-box-img.' + className).find('.comment-box-num span').html(val);
    }

    render() {
        let commentListUrl = '/api/reports/comment_points/' + this.state.uid + '/comments';
        let commentSubmitUrl = '/api/reports/comment_points/' + this.state.uid + '/comments';
        return (
            <div className="mind-map-preview-modal">
                <div className="mind-map-preview-svg">
                    <div className="mind-map-svg-top">
                        <div className="svg-name">{this.props.title}：项目思维导图</div>
                        <div className="svg-size">
                            <span className="modal-svg-btn modal-svg-subtract">-</span>
                            <span className="svg-size-num">100%</span>
                            <span className="modal-svg-btn modal-svg-add">+</span>
                        </div>
                        <div className="svg-close">✕</div>
                    </div>
                    <div className="mind-map-svg-center"></div>
                </div>
                <div className="mind-map-preview-comment">
                    <div className="fold-btn">
                    </div>
                    <div className='mind-map-comment-top-box'>
                        <div className="mind-map-comment-top clearfix">
                            <div className="left-tab clearfix">
                                <div className="tab-item active">评论(<span>{this.state.nums}</span>)</div>
                                <div className='tab-item-icon active'>
                                    <img src="/static/new-report/img/icon-right-comment.svg" alt=""/>
                                </div>
                            </div>

                        </div>
                    </div>
                    <div className="mind-map-comment-center">

                        {
                            this.state.uid && this.state.uid != ''
                                ?
                                <Review
                                    ref='reviewDom'
                                    objectName={'报告：' + PageData.reportData.title + ' 思维导图'}
                                    urlList={{getListUrl: commentListUrl, submitUrl: commentSubmitUrl}}
                                    requestData={null}
                                    params={{order_by: 'created_at', order_dir: 'desc'}}
                                    onUpdateCommentList={this.onUpdateCommentList.bind(this)}
                                    onRef={this.onRef.bind(this)}
                                />
                                : ''
                        }
                    </div>
                </div>
            </div>
        )
    }
}

const CALC_DEFAULT_DATA = [
    {
        name: '项目经理',
        cost: 20000,
        time: 2,
    },
    {
        name: '产品经理',
        cost: 20000,
        time: 2,
    },
    {
        name: '测试',
        cost: 15000,
        time: 2,
    },
    {
        name: '设计',
        cost: 20000,
        time: 2,
    },
]

//时间及其金额预估
class TimePriceSection extends React.Component {
    constructor(props) {
        super(props);
        this.state = {

            //全部数据
            data: [],

            showModal: false,

            //当前选中的方案
            activeUid: null,
            activeDataIndex: null,
            activeDataName: '',
            activeData: {},

            userList: '',

        }
    }

    componentDidMount() {
        this.getUserList();

        //点击时间及金额预估
        $('#TimePriceSection').on('click', '.estimate-box', (e) => {

            let that = this;
            if (
                e.target && e.target.className && typeof (e.target.className) == 'string'
                &&
                e.target.className.indexOf('estimate-data-btn') < 0
                &&
                e.target.localName != 'input'
                &&
                e.target.type != 'textarea'
                &&
                e.target.className != 'sed-btn'
                &&
                e.target.className != 'estimate-item-list-right'
                &&
                !matchingStr(e.target.className, 'atwho-inserted')
                &&
                !matchingStr(e.target.className, 'gear-user-box')

            ) {
                if ($(e.target).parents('.estimate-box').hasClass('checked')) {
                    return false;
                }
                $(e.target).parents('.estimate-box').addClass('checked').siblings().removeClass('checked');

                if ($('.estimate-box.checked').length > 0) {

                    if ($('.estimate-box.checked').attr('comment_uid') && $('.estimate-box.checked').attr('comment_uid') != '') {
                        that.getComments($('.estimate-box.checked').attr('comment_uid')).then((res) => {
                            let className = 'pl-' + res.uid;
                            //显示对应的评论框
                            $('.' + className).parent().siblings().find('.gear-comment-box-plan').removeClass('active');
                            $('.' + className).addClass('active');
                            that.addListCommentsPlan(res, true);
                        });
                    } else {
                        //创建评论点
                        let url = '/api/reports/' + PageData.reportData.uid + '/comment_points';
                        let data = {
                            "content_type_app": "reports",
                            "content_type_model": "quotationplan",
                            "object_id": $('.estimate-box.checked').attr('data_id')
                        }
                        commonRequest('POST', url, data, (res) => {
                            $('.estimate-box.checked').attr('comment_uid', res.data.uid);
                            $('.estimate-box.checked .gear-comment-box-plan').addClass('pl-' + res.data.uid);
                            $('.estimate-box.checked .gear-comment-box-plan').attr('comment_uid', res.data.uid);
                            $('.estimate-box.checked .gear-comment-box-plan').show();
                            that.getComments(res.data.uid).then((res) => {
                                let className = 'pl-' + res.uid;

                                let data = that.state.data;
                                data[$('.estimate-box.checked').index() - 1].uid = res.uid;
                                that.setState({
                                    data: data
                                }, () => {
                                    that.props.upDatePost(data)
                                })
                                //显示对应的评论框
                                $('.' + className).parent().siblings().find('.gear-comment-box-plan').removeClass('active');
                                $('.' + className).addClass('active');
                                that.addListCommentsPlan(res);
                            });
                        })
                    }

                }
            }

        })

        //点击发送 -- 时间及金额预估
        $('#TimePriceSection').on('click', '.sed-btn', (e) => {

            let that = this
            let val = $('.gear-comment-box-plan.active .gear-at-textarea').html();
            if (val == '') {
                return false;
            }

            let uid = $('.estimate-box.checked').attr('comment_uid');

            let url = '/api/reports/comment_points/' + uid;
            let data = {
                content: val,
                page_title: document.title.trim(),
                page_url: window.location.href,
            }
            commonRequest('POST', url, data, (res) => {
                if (res.result) {
                    if(window.pointState){
                        window.pointState.updatePoint = Math.random()
                    }
                    // $('.text-area').val('');
                    that.addListCommentsPlan(res.data, true);
                }
            })


        })


        //点击回复 -- 时间及金额预估
        $('#TimePriceSection').on('click', '.btn-huifu', (e) => {
            var val = $(e.target).attr('user_name');

            let that = this;
            that.getUserList().then((res) => {
                let userData = '';
                let htmls = ''
                for (let i = 0; i < res.length; i++) {
                    if (val.trim() == res[i].username.trim()) {
                        userData = res[i];
                        break;
                    }
                }
                if (userData != '') {
                    htmls = '<span class="atwho-inserted" data-atwho-at-query="@" contenteditable="false">' +
                        '<div id="' + userData.id + '" username="' + userData.username + '" avatarurl="' + userData.avatar_url + '" color="' + userData.avatar_color + '" name="' + userData.username + '" email="' + userData.email + '" class="gear-user-box" href="javascript:;">' + userData.username + '</div>' +
                        '</span>&nbsp;'
                } else {
                    htmls = val;
                }
                that.initTextCommenText(htmls);
            })
        })
        //点击删除 -- 时间及金额预估
        $('#TimePriceSection').on('click', '.btn-sahnchu', (e) => {
            let that = this
            let comment_id = $(e.target).attr('comment_id')
            let url = '/api/comments/' + comment_id;
            commonRequest('DELETE', url, {}, (res) => {
                if (res.result) {
                    $(e.target).parent().parent().remove();

                    $('.gear-comment-box-plan.active .comment-box-num span').html(Number($('.gear-comment-box-plan.active .comment-box-num span').html()) - 1);
                    if ($('.gear-comment-box-plan.active .item-list').length <= 0) {
                        $('.gear-comment-box-plan.active').hide();
                    }
                }
            })
        })

        //点击指定元素外
        $(document).bind('click', (e) => {
            var event = e || window.event; //浏览器兼容性
            var elem = event.target || event.srcElement;

            while (elem && elem !== '') { //循环判断至跟节点，防止点击的是div子元素
                if (
                    (
                        elem.className &&
                        typeof (elem.className) == 'string' &&
                        elem.className.indexOf('estimate-box') >= 0 &&
                        elem.className.indexOf('checked') >= 0

                    )
                    ||
                    (elem.className && typeof (elem.className) == 'string' && matchingStr(elem.className, 'atwho-inserted'))
                    ||
                    (elem.className && typeof (elem.className) == 'string' && matchingStr(elem.className, 'gear-user-box'))
                /*||
                (
                    elem.className &&
                    typeof (elem.className) == 'string' &&
                    elem.className.indexOf('gear-comment-box-plan') >= 0 &&
                    elem.className.indexOf('active') >= 0
                )*/

                ) {
                    return;
                }
                elem = elem.parentNode;
            }
            $('.gear-comment-box-plan.active').removeClass('active');
            $('.estimate-box.checked').removeClass('checked');
        });

    }

    componentWillReceiveProps(nextProps) {
        if (nextProps.quotation_plans && nextProps.quotation_plans != '') {
            let data = nextProps.quotation_plans;
            for (let i = 0; i < data.length; i++) {
                if (!isValidValue(data[i].price_detail)) {
                    data[i].price_detail = {
                        tax: 20, //个人所得税
                        cost: 6000, //固定成本
                        deduction: 25, //提成
                        referral: 0, //介绍费
                        listData: copyJsonObj(CALC_DEFAULT_DATA)
                    };
                }
            }
            this.setState({
                data: data
            })
        }

    }


    getUserList() {
        let that = this;
        return new Promise((resolve, reject) => {
            if (this.state.userList == '') {
                let url = '/api/users';
                commonRequest('GET', url, {}, (res) => {
                    that.setState({
                        userList: res.data
                    })
                    resolve(res.data)
                })
            } else {
                resolve(that.state.userList)
            }
        });
    }

    getReportQuotationPlan() {
        let that = this;
        let url = '/api/reports/' + PageData.reportData.uid + '/plans';
        commonRequest('GET', url, null, (res) => {
            if (res.result) {
                let data = res.data;
                that.setState({
                    data: data
                }, () => {
                    that.props.upDatePost(data)
                })
            }
        })
    }

    //添加解决方案
    addEstimate() {
        let that = this;
        let url = '/api/reports/' + PageData.reportData.uid + '/plans';
        let data = {
            page_view_uuid: PageData.page_view_uuid,
            title: "报价方案",
            price_detail: {
                tax: 20, //个人所得税
                cost: 6000, //固定成本
                deduction: 25, //提成
                referral: 0, //介绍费
                listData: copyJsonObj(CALC_DEFAULT_DATA)
            }
        }
        commonRequest('POST', url, data, (res) => {
            if (res.result) {
                that.getReportQuotationPlan()
            } else {
                farmAlter(res.message, 3000);
            }
        })

    }

    //删除解决方案
    deleteQuotationPlan(item, index) {
        let that = this;
        farmConfirm(
            '是否删除该报价方案？',
            function () {
                let url = '/api/reports/' + PageData.reportData.uid + '/plans/' + item.id;
                commonRequest('delete', url, {}, function (res) {
                    if (res.result) {
                        that.getReportQuotationPlan();
                        $('.estimate-box.checked').removeClass('checked');
                    } else {
                        farmAlter(res.message, 3000);
                    }
                })

            }
        )
    }


    //上移方案
    moveUpQuotationPlan(item, index) {
        let that = this;
        farmConfirm(
            '是否上移该报价方案？',
            function () {
                let url = '/api/reports/' + PageData.reportData.uid + '/plans/' + item.id + '/move_up';
                ;
                commonRequest('post', url, {}, function (res) {
                    if (res.result) {
                        that.getReportQuotationPlan();
                        $('.estimate-box.checked').removeClass('checked');
                    } else {
                        farmAlter(res.message, 3000);
                    }
                })

            }
        )
    }

    //下移
    moveDownQuotationPlan(item, index) {
        let that = this;
        farmConfirm(
            '是否下移该报价方案？',
            function () {
                let url = '/api/reports/' + PageData.reportData.uid + '/plans/' + item.id + '/move_down';
                commonRequest('post', url, {}, function (res) {
                    if (res.result) {
                        that.getReportQuotationPlan();
                        $('.estimate-box.checked').removeClass('checked');
                    } else {
                        farmAlter(res.message, 3000);
                    }
                })
            }
        )
    }


    //点击显示计算器
    clickShowJiSuan(item, index) {
        let that = this;

        if (

            item.comment_points && item.comment_points[0] && item.comment_points[0] != '' && item.comment_points[0].uid && item.comment_points[0].uid != ''

        // (item.comment_points && item.comment_points[0] && item.comment_points[0] != '' && item.comment_points[0].uid && item.comment_points[0].uid != '') ||
        // ($('.estimate-box.checked').attr('comment_uid') && $('.estimate-box.checked').attr('comment_uid') != '')
        ) {
            //有uid dom上可能也有
            let data = that.state.data;

            let uid = '';
            if (item.comment_points && item.comment_points[0] && item.comment_points[0] != '' && item.comment_points[0].uid && item.comment_points[0].uid != '') {
                uid = item.comment_points[0].uid
            }
            /*if ($('.estimate-box.checked').attr('comment_uid') && $('.estimate-box.checked').attr('comment_uid') != '') {
                uid = $('.estimate-box.checked').attr('comment_uid')
                data[index].comment_points = [{uid: uid}];
            }*/

            //计算器中的初始数据
            let activeData = data[index].price_detail;

            that.setState({
                // data: data,
                activeUid: uid,
                activeDataIndex: index,
                activeDataName: data[index].title,
                activeData: activeData,
            }, () => {
                $('body').addClass('modal-open');
                that.setState({
                    showModal: true,
                })
                // that.props.upDatePost(that.state.data)
            })
        } else {
            //没有uid 创建评论点uid
            let url = '/api/reports/' + PageData.reportData.uid + '/comment_points';
            let data = {
                "content_type_app": "reports",
                "content_type_model": "quotationplan",
                "object_id": item.id
            }
            commonRequest('POST', url, data, (res) => {

                let data = that.state.data;
                //计算器中的初始数据
                let activeData = data[index].price_detail;

                data[index].comment_points = [{uid: res.data.uid}];
                that.setState({
                    data: data,
                    activeUid: res.data.uid,
                    activeDataIndex: index,
                    activeDataName: data[index].title,
                    activeData: activeData,
                }, () => {
                    $('body').addClass('modal-open');
                    that.setState({
                        showModal: true,
                    })
                    that.props.upDatePost(that.state.data)
                })
            })
        }

    }

    //关闭计算器弹框
    closeModal() {
        $('body').removeClass('modal-open');
        this.setState({
            showModal: false,
        })
    }


    //input改变
    valueChange(val, index, e) {
        let data = this.state.data;
        if (val == 'price') {
            data[index][val] = $(e.target).val().replace(/[^0-9.—-]/g, "");
        } else {
            data[index][val] = $(e.target).val()
        }
        this.setState({
            data: data
        }, () => {
            this.props.upDatePost(this.state.data)
        })
    }

    //项目包含
    valueChangeProjects(index, val) {
        let data = this.state.data;
        // console.log(1,val,index)
        data[index]['projects'] = val.join(' + ');
        this.setState({
            data: data
        }, () => {
            this.props.upDatePost(this.state.data)
        })
    }

    //服务范围
    valueChangeServices(index, val) {
        let data = this.state.data;
        // console.log(1,val,index)
        data[index]['services'] = val.join(' + ');
        this.setState({
            data: data
        }, () => {
            this.props.upDatePost(this.state.data)
        })
    }

    valueInput(val, index, e) {
        // val, index, e
    }


    //计算器中的值改变
    setValData(data) {
        let datas = this.state.data;
        datas[this.state.activeDataIndex].price_detail = data;
        this.setState({
            data: datas
        }, () => {
            this.props.upDatePost(this.state.data)
        })
    }


    //计算器中 选择 与 添加 方案
    setCalculatorData(flag) {
        if (flag == 'add') {

            let that = this;

            let initData = {
                tax: 20, //个人所得税
                cost: 6000, //固定成本
                deduction: 25, //提成
                referral: 0, //介绍费
                listData: copyJsonObj(CALC_DEFAULT_DATA)
            };

            //创建方案
            let url = '/api/reports/' + PageData.reportData.uid + '/plans';
            let data = {
                page_view_uuid: PageData.page_view_uuid,
                title: "",
            }

            commonRequest('POST', url, data, (res) => {
                if (res.result) {
                    let obj = res.data;
                    obj.price_detail = initData;

                    //获取评论点uid
                    let url = '/api/reports/' + PageData.reportData.uid + '/comment_points';
                    let data = {
                        "content_type_app": "reports",
                        "content_type_model": "quotationplan",
                        "object_id": res.data.id
                    }
                    commonRequest('POST', url, data, (res) => {
                        obj.comment_points = [{uid: res.data.uid}];

                        let data = [...that.state.data, obj];

                        that.setState({
                            data: data,
                            activeUid: res.data.uid,
                            activeDataIndex: data.length - 1,
                            activeDataName: '',
                            activeData: initData,
                        }, () => {
                            that.props.upDatePost(that.state.data)
                        })
                    })
                }

            })
        } else {
            let that = this;
            let data = this.state.data;

            let index = this.state.activeDataIndex + flag;

            if (index <= -1) {
                index = 0;
            }
            if (index >= (data.length - 1)) {
                index = data.length - 1;
            }

            let initData = {
                tax: 20, //个人所得税
                cost: 6000, //固定成本
                deduction: 25, //提成
                referral: 0, //介绍费
                listData: copyJsonObj(CALC_DEFAULT_DATA)
            };

            if (data[index].comment_points && data[index].comment_points[0] && data[index].comment_points[0] != '' && data[index].comment_points[0].uid && data[index].comment_points[0].uid != '') {
                // 有uid
                that.setState({
                    data: data,
                    activeUid: data[index].comment_points[0].uid,
                    activeDataIndex: index,
                    activeDataName: data[index].title,
                    activeData: data[index].price_detail && data[index].price_detail != '' && data[index].price_detail != null ? data[index].price_detail : initData,
                }, () => {
                    $('body').addClass('modal-open');
                    that.setState({
                        showModal: true,
                    })
                })
            } else {
                //没有uid 创建评论点uid
                let url = '/api/reports/' + PageData.reportData.uid + '/comment_points';
                let dataPost = {
                    "content_type_app": "reports",
                    "content_type_model": "quotationplan",
                    "object_id": data[index].id
                }
                commonRequest('POST', url, dataPost, (res) => {
                    data[index].comment_points = [{uid: res.data.uid}];
                    that.setState({
                        data: data,
                        activeUid: res.data.uid,
                        activeDataIndex: index,
                        activeDataName: data[index].title,
                        activeData: data[index].price_detail && data[index].price_detail != '' && data[index].price_detail != null ? data[index].price_detail : initData,
                    }, () => {
                        $('body').addClass('modal-open');
                        that.setState({
                            showModal: true,
                        })
                        that.props.upDatePost(that.state.data)
                    })
                })
            }
        }
    }


    //根据UID获取评论列表
    getComments(UID) {
        return new Promise((resolve, reject) => {
            let url = '/api/reports/comment_points/' + UID;
            commonRequest('GET', url, {}, (res) => {
                if (res.result) {
                    resolve(res.data)
                } else {
                    reject('err')
                }
            })

        });
    }

    //时间及金额预估 根据评论列表详情 判断是否有评论列表 将评论列表添加到评论框中
    addListCommentsPlan(res, isScroll = false) {
        if (res.comments.length <= 0) {
            $('.gear-comment-box-plan.active .comment-box-num span').html(0);
            $('.gear-comment-box-plan.active .comment-center-list').hide();
            this.initTextCommenText('');
        } else {
            $('.gear-comment-box-plan.active').show();
            $('.gear-comment-box-plan.active .comment-box-num span').html(res.comments.length);
            $('.gear-comment-box-plan.active .comment-center-list').show();
            let listDom = '';
            for (let item of res.comments) {
                var strs = item.content;
                /*var activeStr = strs.match(/@(\S*) /g);
                if (activeStr && activeStr.length > 0) {
                    for (var list of activeStr) {
                        strs = strs.replace(list, "<a class='user'>" + list + "</a>");
                    }
                }*/
                listDom += `
                            <div class="item-list">
                                <div class="item-list-user">
                                    <img src="${item.author.avatar_url}" 
                                     color='${item.author.avatar_color}'
                                     name='${item.author.username}'
                                     widthSize='24'
                                     fontSize='12'
                                     onerror="userAvatarImgError(this)"
                                    />
                                    <span class="user-name">${item.author.username}</span>
                                    <span class="user-time">${item.created_at}</span>
                                    <span class="user-btn btn-huifu" user_name="${item.author.username}">回复</span>
                                    <span class="user-btn btn-sahnchu" comment_id="${item.id}">删除</span>
                                </div>
                                <div class="item-list-text">
                                    ${strs}
                                </div>
                            </div>
                        `
            }
            let divDom = `<div class="comment-center-scroll">${listDom}</div>`;
            $('.gear-comment-box-plan.active .comment-center-list').html(divDom);

            if (isScroll) {
                $('.gear-comment-box-plan.active .comment-center-list').scrollTop($('.gear-comment-box-plan.active .comment-center-scroll').height())
            }
            this.initTextCommenText('');

        }
    }

    //初始化评论中的文本输入 -- 时间金额预估
    initTextCommenText(val) {
        let that = this;
        that.getUserList().then((res) => {
            var params = {
                userList: res,
                placeholder: '请输入评论',
                defValue: val,
                //按回车键 -- 时间金额预估
                enterCallbick: function () {
                    let val = $('.gear-comment-box-plan.active .gear-at-textarea').html();
                    if (val == '') {
                        return false;
                    }
                    let uid = $('.estimate-box.checked').attr('comment_uid');

                    let url = '/api/reports/comment_points/' + uid;
                    let data = {
                        content: val,
                        page_title: document.title.trim(),
                        page_url: window.location.href,
                    }
                    commonRequest('POST', url, data, (res) => {
                        if (res.result) {
                            that.addListCommentsPlan(res.data, true);
                        }
                    })

                },
            }
            $('.gear-comment-box-plan.active .gear-text-area').JqMention(params);
        })
    }


    render() {

        let listDom = '';
        let that = this;
        if (this.state.data.length > 0) {
            listDom = this.state.data.map((item, index) => {
                item.price = item.price != null ? item.price.replace(/[^0-9.—-]/g, "") : '';
                let sumNum = 0;
                // 个人所得税
                let taxNum = 0;
                // 固定成本
                let cost = 0;
                //齿轮提成
                let deductionNum = 0;
                //介绍费
                let referralNum = 0;
                if (item.price_detail != null) {
                    let data = item.price_detail;
                    cost = data.cost;

                    // 个人所得税 总金额
                    let taxSumNum = 0;
                    for (let item2 of data.listData) {
                        taxSumNum += Math.round(item2.cost / 4.3 * item2.time);
                    }
                    taxNum = Math.round(taxSumNum * (data.tax / (100 - data.tax)));

                    //齿轮提成 总金额
                    let deductionSumNum = taxSumNum + taxNum + data.cost;
                    deductionNum = Math.round(deductionSumNum * (data.deduction / (100 - data.deduction)));

                    //介绍费 总金额
                    let referralSumNum = deductionSumNum + deductionNum;
                    referralNum = Math.round(referralSumNum * (data.referral / (100 - data.referral)));

                    //总报价
                    sumNum = referralSumNum + referralNum;
                }

                let comment_uid = '';
                if (item.comment_points && item.comment_points[0] && item.comment_points[0] != '' && item.comment_points[0].uid && item.comment_points[0].uid != '') {
                    comment_uid = item.comment_points[0].uid;
                }


                /*if(!item.projects || item.projects==''){
                    item.projects = 'iOS App + Android App + 微信小程序 + 移动端H5网站 + 微信服务号 + PC端Web网站 + PC端Web管理后台 + Pad端 iOS App + Pad端 Android App'
                }*/

                if (!item.services || item.services == '') {
                    item.services = '产品咨询 + 原型制作 + UI设计 + 功能开发 + 功能测试'
                }

                let planProjectList = item.projects ? item.projects.split('+') : [];
                planProjectList = planProjectList.map((item, index) => {
                    return (item.trim())
                });
                let planServiceList = item.services ? item.services.split('+') : [];
                planServiceList = planServiceList.map((item, index) => {
                    return (item.trim())
                });
                return (
                    <div className="estimate-box"
                         key={index}
                         data_id={item.id}
                         comment_uid={comment_uid}
                    >

                        <div className={
                            comment_uid && comment_uid != ''
                                ? "gear-comment-box gear-comment-box-plan pl-" + comment_uid
                                : "gear-comment-box gear-comment-box-plan"
                        }
                             comment_uid={comment_uid}
                             style={{
                                 display:
                                     comment_uid && comment_uid != '' && this.props.allCommentData && this.props.allCommentData[comment_uid] && this.props.allCommentData[comment_uid] > 0
                                         // comment_uid && comment_uid != ''
                                         ? 'block'
                                         : 'none',
                                 width: 'auto', left: '-280px', top: '0px'
                             }}
                        >
                            <div style={{display: 'flex'}}>
                                <div className="comment-box-num">
                                    <div className="sanjiao"></div>
                                    <span className='span-nums'>
                                        {
                                            this.props.allCommentData != null
                                                ? this.props.allCommentData[comment_uid] ? this.props.allCommentData[comment_uid] : 0
                                                : 0
                                        }
                                    </span>
                                </div>
                                <div className="comment-center">
                                    <div style={{display: 'flex', flexDirection: 'column'}}>
                                        <div className="comment-center-list new-scroll-bar">

                                        </div>
                                        <div className="comment-center-text">
                                            <div className="gear-text-area"></div>
                                            <div className="text-foot clearfix">
                                                <button className="sed-btn">发送</button>
                                                {/*<button className="cancel-btn">删除</button>*/}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className='estimate-box-buttons'>
                            {
                                index != 0 ?
                                    <span className="box-button"
                                          onClick={this.moveUpQuotationPlan.bind(this, item, index)}>
                                        <Icon type="arrow-up" style={{fontSize: '18px'}}/>
                                    </span>
                                    : null
                            }
                            {
                                index + 1 != this.state.data.length ?
                                    <span className="box-button"
                                          onClick={this.moveDownQuotationPlan.bind(this, item, index)}>
                                        <Icon type="arrow-down" style={{fontSize: '18px'}}/>
                                    </span>
                                    : null
                            }
                            <span className="box-button" onClick={this.deleteQuotationPlan.bind(this, item, index)}>
                                <svg width="20" height="20">
                                    <defs>
                                        <path id={"删除-a2" + index}
                                              d="M14,6 L6,6 L6,16 L14,16 L14,6 Z M16,6 L16,16 L16,18 L4,18 L4,16 L4,6 L2,6 L2,4 L18,4 L18,6 L16,6 Z M8,8 L9,8 L9,14 L8,14 L8,8 Z M11,8 L12,8 L12,14 L11,14 L11,8 Z M7,1 L13,1 L13,3 L7,3 L7,1 Z"/>
                                    </defs>
                                    <g fill="none" fillRule="evenodd">
                                        <mask id={"删除-b2" + index} fill="#fff">
                                            <use xlinkHref={"#删除-a2" + index}/>
                                        </mask>
                                        <g fill="currentColor" mask={"url(#删除-b2" + index + ")"}>
                                            <rect width="20" height="20"/>
                                        </g>
                                    </g>
                                </svg>
                            </span>
                        </div>
                        <div className="estimate-item">
                            <div className="estimate-item-title">
                                <input className="estimate-input" type="text"
                                       onChange={this.valueChange.bind(this, 'title', index)}
                                       value={item.title ? item.title : ''} placeholder="请输入报价方案名称"/>
                            </div>
                            <div className="estimate-item-list">
                                <div className="estimate-item-list-left">
                                    报价估算：
                                </div>
                                <div className="estimate-item-list-right" style={{
                                    position: 'relative',
                                }}>
                                    <input className="estimate-input" type="text"
                                           onChange={this.valueChange.bind(this, 'price', index)}
                                           onInput={this.valueInput.bind(this, 'price', index)}
                                           value={item.price ? item.price : ''} placeholder="请输入报价范围 如:10-20万"/>
                                    <div
                                        className='estimate-input-text'
                                        style={{
                                            position: 'absolute',
                                            top: 0,
                                            left: 0,
                                        }}><span
                                        style={{opacity: 0}}>{item.price}</span><span>{item.price || item.price != '' ? '万' : ''}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="estimate-item-list">
                                <div className="estimate-item-list-left">
                                    预计工期：
                                </div>
                                <div className="estimate-item-list-right">
                                    <input className="estimate-input" type="text"
                                           onChange={this.valueChange.bind(this, 'period', index)}
                                           value={item.period ? item.period : ''} placeholder="请输入预计工期"/>
                                </div>
                            </div>
                            <div className="estimate-item-list">
                                <div className="estimate-item-list-left">
                                    项目包含：
                                </div>
                                <div className="estimate-item-list-right">
                                    <Select
                                        mode="tags"
                                        style={{width: '100%', marginBottom: '8px'}}
                                        value={planProjectList ? planProjectList : []}
                                        onChange={this.valueChangeProjects.bind(this, index)}
                                    >
                                        {
                                            PlanProjectSelect.map((item, index) => {
                                                return (
                                                    <Option key={item}>{item}</Option>
                                                )
                                            })
                                        }
                                    </Select>
                                    {/*<input className="estimate-input" type="text"
                                           onChange={this.valueChange.bind(this, 'projects', index)}
                                           value={item.projects ? item.projects : ''} placeholder="请输入项目包含"/>*/}
                                </div>
                            </div>
                            <div className="estimate-item-list">
                                <div className="estimate-item-list-left">
                                    服务范围：
                                </div>
                                <div className="estimate-item-list-right">
                                    <Select
                                        mode="tags"
                                        style={{width: '100%', marginBottom: '8px'}}
                                        value={planServiceList ? planServiceList : []}
                                        onChange={this.valueChangeServices.bind(this, index)}
                                    >
                                        {
                                            PlanSeverSelect.map((item, index) => {
                                                return (
                                                    <Option key={item}>{item}</Option>
                                                )
                                            })
                                        }
                                    </Select>
                                    {/*<input className="estimate-input" type="text"
                                           onChange={this.valueChange.bind(this, 'services', index)}
                                           value={item.services ? item.services : ''} placeholder="请输入服务范围"/>*/}
                                </div>
                            </div>
                        </div>
                    </div>
                )
            })
        }

        let latest_lead_quotation = this.props.reportDetail ? this.props.reportDetail.latest_lead_quotation : null;
        let quotation_list = latest_lead_quotation && latest_lead_quotation.quotation_list ? latest_lead_quotation.quotation_list : [];
        let leadId = latest_lead_quotation && latest_lead_quotation.lead && latest_lead_quotation.lead.id;
        let latest_lead_quotation_id = latest_lead_quotation && latest_lead_quotation.id;
        return (
            <div>

                <div className="item-title clearfix">
                    <span className="text">时间及金额预估</span>
                    <div className="switch-container">

                        <input type="checkbox" className="switch-input" checked={this.props.show_plan}
                               onChange={this.props.clickSwitch}/>
                        <div className="switch-bg" onClick={this.props.clickSwitch}></div>
                        <div className="switch-tip">
                            <div className="switch-tip-triangle"></div>
                            <div className="switch-tip-text">
                                在报告中{this.props.show_plan ? '隐藏' : '显示'}
                            </div>
                        </div>
                    </div>
                    <button className="add-estimate" onClick={this.addEstimate.bind(this)}><span>+</span>添加方案</button>
                </div>
                {
                    quotation_list && quotation_list.length > 0 && this.props.show_plan &&
                    <div className='quotation-div'>
                        <div>
                            {
                                quotation_list.map((item, index) => {
                                    return <span key={index}>{item.title ? item.title + ' :' : ''} {item.content}</span>
                                })
                            }
                        </div>
                        <a href={'/clients/leads/detail/' + '?lead_id={lead_id}&quotation_id={quotation_id}'.replace('{lead_id}', leadId).replace('{quotation_id}', latest_lead_quotation_id)}
                           target='_blank'>查看详情</a>
                    </div>
                }

                {listDom}

                {
                    this.props.show_plan
                        ?
                        null
                        :
                        <div className="masking-bg"></div>
                }

            </div>
        )
    }
}

//控制编辑器是否可以编辑SHOW_PARENT
function setEdit(flag) {
    if (flag) {
        $('.edit-report-container').css({'pointer-events': 'auto'})
        $('.top-item-list-edit').css({'pointer-events': 'auto'})
    } else {
        $('.edit-report-container').css({'pointer-events': 'none'})
        $('.top-item-list-edit').css({'pointer-events': 'none'})
    }

}


//渲染项目页面
ReactDOM.render(
    <NewReports/>,
    document.getElementById('NewReports')
);


