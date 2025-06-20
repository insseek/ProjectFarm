
/*
    import GuideModal from 'path/GuideModal';
     <GuideModal/>
*/


import React from "react";
import {Button, Modal} from "antd";
import './index.scss'
//引导Modal
const modalData = {
    1:{
        title:'协同操作，实时保存',
        dec:"报告可同时被一人编辑，多人浏览。任何修改会实时同步给所有人",
        img:require("./image/step-01.png"),
    },
    2:{
        title:'查看操作记录，复原历史版本',
        dec:"系统记录每一次的修改内容，可以还原到自动保存的任意历史版本",
        img:require("./image/step-02.png"),
    },
    3:{
        title:'添加评论，即时反馈',
        dec:"报告可标记某一部分的内容或整体添加评论，@项目组成员提醒及时查看",
        img:require("./image/step-03.png"),
    },
    4:{
        title:'添加插件，丰富报告',
        dec:(<div><p>在编辑内容时输入@，可插入多种内容插件</p><p>根据企业需求，齿轮易创能为您<strong>「定制标准插件」</strong>（如地图、视频、商品展示等）</p></div>),
        img:require("./image/step-04.png"),
    },
    5:{
        title:'灵活配置模块，创建多种报告',
        dec:(<div><p>用户可根据实际情况，选择显示或者隐藏某一模块内容</p> <p>根据企业需求，齿轮能为您<strong>「定制标准模块」</strong></p></div>),
        img:require("./image/step-05.png"),
    }
}
export default class GuideModal extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            step: 1,
            total: 5,
            isShowGuideModal:false,
        }
    }

    componentDidMount() {
        this.checkIsGuide();
    }
    //用户是否需要引导
    checkIsGuide() {
        let that = this;
        let url = `/api/users/guidance/status`;
        commonRequest('GET', url, {}, (res) => {
            that.setState({
                isShowGuideModal: res.data && res.data.need_guidance
            })
        })
    }

    //关闭
    closedModal() {
        this.setState({
            isShowGuideModal: false,
        })
    }

    //上一页
    prePage() {
        let page = this.state.step - 1;
        this.setState({
            step: page
        })
    }

    //下一页
    nextPage() {
        let page = this.state.step + 1;
        this.setState({
            step: page
        })
    }

    //完成
    finished() {
        let url = `/api/users/guidance/done`;
        let that = this;
        commonRequest('POST', url, {}, (res) => {
            if (res.result) {
                that.closedModal();
            }
        })
    }

    render() {
        let footerDom = <div className={"footer-div"}>
            <p>共{this.state.total}页，当前为第{this.state.step}页</p>
            <div className='btn-group'>
                {
                    this.state.step != 1 &&
                    <Button onClick={this.prePage.bind(this)} className='first-btn'>上一页</Button>
                }
                <Button type='primary' onClick={this.nextPage.bind(this)}>下一页</Button>

            </div>
        </div>
        if (this.state.step === 5) {
            footerDom = <div className={"footer-div"}>
                <p>共{this.state.total}页，当前为第{this.state.step}页</p>
                <div className='btn-group'>
                    <Button onClick={this.prePage.bind(this)} className='first-btn'>上一页</Button>
                    <Button type='primary' onClick={this.finished.bind(this)}>完成</Button>
                </div>
            </div>
        }
        return <React.Fragment>
            {
                this.state.isShowGuideModal ?
                <Modal
                    visible={this.state.isShowGuideModal}
                    title=''
                    width={600}
                    className='guide-modal'
                    footer={footerDom}
                    centered={true}
                    maskClosable={false}
                    closable={false}
                >
                    <p className={`guide-modal-title guide-modal-title${this.state.step}`}>{modalData[this.state.step].title}</p>
                    <p className={`dec-text dec-text${this.state.step}`}>{modalData[this.state.step].dec}</p>
                    <div className={`img-div${this.state.step}`}><img className='' src={modalData[this.state.step].img}/> </div>
                </Modal>
                    :null
            }
        </React.Fragment>
    }
}