import React from "react";
import {Button, Checkbox, Form, message, Modal, Spin, Select, TreeSelect, Input} from "antd";
import AvatarImg from './AvatarImg';

const {SHOW_PARENT, SHOW_ALL} = TreeSelect;
const TextArea = Input.TextArea;


/**报告标签编辑、报告发布组件
 * import ReportTagsModal from 'path/components/ReportTagsModal'
 * <ReportTagsModal
 title='编辑标签'  //发布报告  申请发布报告
 visible={this.state.isShowEditTagsModel}
 closeModal={this.closeEditTagsModal}     //关闭的回调
 onSuccess={this.onSuccess}   //成功的回调
 data={this.state.currentReport}    //报告的数据
 flag='editTags'   //标志  editTags、 publishReportReviewRequired、publishReport    编辑标签、 发布报告需要被审核、直接发布报告
 />
 *
 *
 */

class Index extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            submitting: false,
            userGroup: [],
            isLoading: false,

            value: undefined,
            application_platforms: [],
            product_types: [],
            industries: [],

        };
    }

    componentDidMount() {
        this.initDate();
        if (this.props.flag === 'publishReportReviewRequired') {
            this.getReviewersList();
        }
    }


    //获取报告列表的标签
    getReportTags() {
        this.setState({
            isLoading: true
        });

        let that = this;
        let url = `/api/reports/tags`;
        commonRequest('get', url, {}, function (res) {
            that.setState({
                isLoading: false
            });
            if (res.result) {
                let treeData = [];
                let product_types = res.data.product_types || [];
                product_types.forEach((item, index) => {
                    let treeItem = {};
                    treeItem.title = item.name;
                    treeItem.value = item.id;
                    treeItem.key = item.id;

                    if (item.children && item.children.length > 0) {
                        treeItem.disabled = true;
                    }


                    let children = [];

                    item.children.forEach((it, i) => {
                        let childItem = {};
                        childItem.title = it.name;
                        childItem.value = it.id;
                        childItem.key = it.id;
                        children.push(childItem);
                    });

                    treeItem.children = children;

                    treeData.push(treeItem);
                });
                that.setState({
                    application_platforms: res.data.application_platforms, //产品形态
                    product_types: treeData,   //产品分类
                    industries: res.data.industries,    //所属行业
                })
            }

        })
    };

    // 获取默认报告数据
    getLatestReportTags() {
        let objectId = this.props.data && this.props.data.uid;
        let that = this;
        let url = `/api/reports/${objectId}/tags/default`;
        commonRequest('get', url, {}, function (res) {
            if (res.result) {
                let tags = {};
                let application_platforms = [];
                let industries = [];
                let product_types = [];
                if (res.data) {
                    if (res.data.application_platforms) {
                        for (let i = 0; i < res.data.application_platforms.length; i++) {
                            application_platforms.push(res.data.application_platforms[i].id)
                        }
                    }
                    if (res.data.industries) {
                        for (let i = 0; i < res.data.industries.length; i++) {
                            industries.push(res.data.industries[i].id)
                        }
                    }
                    if (res.data.product_types) {
                        for (let i = 0; i < res.data.product_types.length; i++) {
                            product_types.push(res.data.product_types[i].id)
                        }
                    }
                    tags.application_platforms = application_platforms;
                    tags.industries = industries;
                    tags.product_types = product_types;

                    // console.log(tags);
                    that.props.form.setFieldsValue(tags)

                    /*this.setState({
                        defaultTags:tags,
                    })*/
                }
            }

        })

    };

    //获取审核人列表
    getReviewersList() {
        let that = this;
        let url = `/api/reports/reviewers`;
        commonRequest('get', url, {}, function (res) {
            if (res.result) {
                that.setState({
                    userGroup: res.data
                })
            }
        })
    };

    initDate() {
        Promise.all([this.getReportTags()]).then((result) => {
            this.getLatestReportTags()
        }).catch((error) => {
        })
    }


    //生成报告
    generateReport() {
        if (this.props.flag === 'publishReport') {
            this.publicReport();
        } else if (this.props.flag === 'publishReportReviewRequired') {
            this.submitReviewer();
        }
    };

    //直接发布报告
    publicReport() {
        let reportId = this.props.data && this.props.data.uid;
        this.props.form.validateFields((err, values) => {
            if (!err) {
                this.setState({
                    submitting: true,
                });
                let that = this;
                let url = `/api/reports/${reportId}/publish`;
                commonRequest('POST', url, values, function (res) {
                    that.setState({
                        submitting: false,
                    });
                    if (res.result) {
                        that.props.onSuccess(res.data);
                        let reportUrl = res.data && res.data.report_url;
                        window.open(reportUrl);
                    } else {
                        farmAlter(res.message, 3000);
                    }
                })
            }
        });
    };

    //提交审核
    submitReviewer() {
        let reportUid = this.props.data && this.props.data.uid;
        this.props.form.validateFields((err, values) => {
            if (!err) {
                this.setState({
                    submitting: true,
                });

                let that = this
                let url = `/api/reports/${reportUid}/publish/review`;
                commonRequest('POST', url, values, function (res) {
                    that.setState({
                        submitting: false,
                    });
                    if (res.result) {
                        that.props.onSuccess(res.data);
                    } else {
                        farmAlter(res.message, 3000);
                    }
                })
            }
        });

    };

    onChange(value, label, extra) {
        console.log(value, label, extra);
    };

    onCancel(){
        if(!this.state.submitting){
            this.props.closeModal();
        }
    }

    render() {

        const {getFieldDecorator} = this.props.form;

        const tProps = {
            treeData: this.state.product_types,
            value: this.state.value,
            onChange: this.onChange.bind(this),
            treeCheckable: true,
            showCheckedStrategy: SHOW_PARENT,
            placeholder: '请选择产品分类',
            style: {
                width: '100%',
            },
            showArrow: true,
            dropdownClassName: 'tree-drop-down'
        };
        return (
            <React.Fragment>
                <Modal
                    width={600}
                    visible={this.props.visible}
                    title={this.props.title}
                    onCancel={this.props.closeModal}
                    className='report-tags-modal'
                    footer={[
                        <Button
                            key="cancel"
                            type="default"
                            onClick={this.onCancel.bind(this)}
                        >取消
                        </Button>,
                        <Button
                            key="submit"
                            type="primary"
                            disabled={this.state.submitting}
                            onClick={this.generateReport.bind(this)}
                        >
                            {
                                this.props.flag === 'publishReport' ? '发布' : "确认"
                            }
                        </Button>,
                    ]}
                >
                    <Spin spinning={this.state.isLoading}>
                        <div className='creat-report-modal-center'>
                            <Form
                                className='label-left-form'
                                ref={this.formRef}
                            >
                                <Form.Item
                                    label="产品形态"
                                    className='row-checkbox-form-item'
                                    rules={[{required: true, message: '请选择产品形态'}]}
                                >
                                    {getFieldDecorator('application_platforms', {
                                        rules: [{required: true,}],
                                        initialValue: undefined
                                    })(
                                        <Checkbox.Group>
                                            {
                                                this.state.application_platforms && this.state.application_platforms.map((item, index) => {
                                                    return <Checkbox
                                                        key={item.index}
                                                        value={item.id}
                                                    >{item.name}</Checkbox>
                                                })
                                            }
                                        </Checkbox.Group>
                                    )}
                                </Form.Item>
                                <Form.Item
                                    label="所属行业"
                                    className='row-checkbox-form-item'
                                >
                                    {getFieldDecorator('industries', {
                                        rules: [{required: true,}],
                                        initialValue: undefined
                                    })(
                                        <Checkbox.Group>
                                            {
                                                this.state.industries && this.state.industries.map((item, index) => {
                                                    return <Checkbox
                                                        key={item.index}
                                                        value={item.id}
                                                    >{item.name}</Checkbox>
                                                })
                                            }
                                        </Checkbox.Group>
                                    )}
                                </Form.Item>
                                <Form.Item
                                    label="产品分类"
                                >
                                    {getFieldDecorator('product_types', {
                                        rules: [{required: true,}],
                                        initialValue: undefined
                                    })(
                                        <TreeSelect {...tProps}/>
                                    )}
                                </Form.Item>

                                {
                                    this.props.flag === 'publishReportReviewRequired' &&
                                    <Form.Item
                                        label="审核人"
                                    >
                                        {getFieldDecorator('reviewer', {
                                            rules: [{required: true, message: '需选择一位审核人审核，通过后即可完成发布'}],
                                            initialValue: undefined
                                        })(
                                            <Select
                                                allowClear={false}
                                                showSearch
                                                dropdownMatchSelectWidth={false}
                                                showArrow={true}
                                                style={{width: '100%'}}
                                                optionLabelProp='label'
                                                optionFilterProp='label'
                                                placeholder='请选择审核人'
                                            >
                                                {
                                                    this.state.userGroup.map((item, index) => {
                                                        return (
                                                            <Select.Option
                                                                label={item.username}
                                                                value={item.id}
                                                                key={index}
                                                            >
                                                                {
                                                                    item.avatar_url ?
                                                                        <AvatarImg
                                                                            key={item.id}
                                                                            imgUrl={item.avatar_url}/>
                                                                        :
                                                                        <AvatarImg
                                                                            key={item.id}
                                                                            bgColor={item.avatar_color}
                                                                            text={item.username && item.username.substring(0, 1)}
                                                                        />
                                                                }
                                                                <span style={{marginLeft: '8px'}}>{item.username}</span>
                                                            </Select.Option>
                                                        )
                                                    })
                                                }
                                            </Select>
                                        )}
                                    </Form.Item>
                                }
                                {
                                    this.props.flag === 'publishReportReviewRequired' &&
                                    <Form.Item
                                        label="备注"
                                    >
                                        {getFieldDecorator('comment', {
                                            rules: [{required: true, message: '请填写备注'}],
                                            initialValue: undefined
                                        })(
                                            <TextArea rows={3} placeholder='请输入'/>
                                        )}

                                    </Form.Item>
                                }
                            </Form>
                        </div>
                    </Spin>
                </Modal>
            </React.Fragment>
        )
    }
}

export default Index = Form.create({})(Index);
