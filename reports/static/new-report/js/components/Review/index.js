import React from 'react';
import './index.scss';
import {Mention} from 'antd';
import AvatarImg from '../AvatarImg';
import GearMention from '../GearMention';
import moment from 'moment';
import 'moment/locale/zh-cn';

const {toString, toContentState} = Mention;

/**修改项目关键点示例
 *
 * import Review from '@components/Review'
 <Review
 key='key'
 objectName={"项目：" + currentProject.name}
 urlList={{getListUrl: '/api/comments/', submitUrl: '/api/comments/'}}
    requestData={ {app_label: 'proposals',model: 'proposal', object_id: 1}}
    params={{app_label: 'proposals',model: 'proposal', object_id: 1,order_by: 'created_at', order_dir: 'desc'}}
    onUpdateCommentList={this.getRemarksList.bind(this)}
    ref='reviewDom'

    size="small"
    class="remark-modal"
    style={null}
    showEmptyIcon={true}
 />
 */


export default class Index extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            commentList: [],
            pointCommentList: [],
            userList: [],
            renderUsersList: [],
            commentMsg: toContentState(''),

            currentItemData: '',
        }
    }

    componentDidMount() {
        //声明副组件的方法
        if (this.props.onRef) {
            this.props.onRef(this);
        }
        this.getCommentList();
        this.commentsGetUserList();
    }

    componentWillReceiveProps(nextProps) {
        if (!deepCompare(nextProps.urlList, this.props.urlList) || !deepCompare(nextProps.params, this.props.params)) {
            this.getCommentList(nextProps);
        }
    }

    //父组件触发更新数据
    updateList() {
        let that = this;
        this.getCommentList(this.props, function () {
            // that.showLastComment(that.props)
        });
        this.commentsGetUserList();
    }

    // 获取评论人 提示人列表
    commentsGetUserList() {
        let that = this;
        let url = '/api/users/';
        commonRequest('get', url, null, function (data) {
            let userList = [];
            for (let i in data.data) {
                userList.push(data.data[i].username);
            }
            that.setState({
                userList: userList
            });
        })
    }

    getCommentList(props, func) {
        let that = this;
        props = props ? props : this.props;
        let params = props.params ? props.params : {};
        let url = props.urlList.getListUrl;
        commonRequest("GET", url, params, function (result) {
            if (result.result) {
                let commentList = result.data;
                let commentCount = commentList ? commentList.length : 0;
                that.setState({
                    commentList: commentList
                });
                if (func) {
                    func(commentCount)
                }
                if (that.props.onUpdateCommentList) {
                    that.props.onUpdateCommentList(commentList.length)
                }
            }

        })
    }

    getPointCommentList(){
        return new Promise((resolve, reject) => {
            if (this.state.allCommentData == null) {

            } else {
                resolve(this.state.allCommentData)
            }
        });
    }

    showLastComment(props) {
        props = props ? props : this.props;
        let commentListSection = this.refs.commentListContent;
        if (commentListSection) {
            if (props.size == 'small') {
                commentListSection.scrollTop = 0
            } else if (commentListSection.scrollHeight && commentListSection.scrollHeight > 0) {
                commentListSection.scrollTop = commentListSection.scrollHeight
            }
        }
    }


    submitComment(content, content_text, userList, func) {
        let that = this;
        let url = this.props.urlList.submitUrl;
        let subData = this.props.requestData ? this.props.requestData : {};
        subData.content = content;
        subData.content_text = content_text;
        if(this.state.currentItemData && this.state.currentItemData.id){
            subData.parent = this.state.currentItemData.id;
        }
        commonRequest('POST', url, subData, function (data) {
            if (data.result) {
                that.getCommentList(that.props, function (commentCount) {
                    if (that.props.onUpdateCommentList) {
                        that.props.onUpdateCommentList(commentCount)
                    }
                    if (userList.length > 0) {
                        that.sendNotification(content_text, userList);
                    }
                    // that.showLastComment(that.props);
                    func()
                });
                that.setState({
                    currentItemData: ''
                })
            } else {
                alert(data.message)
            }

        })
    }

    sendNotification(content_text, userList) {
        let setData = {};
        let contentTemplate = '{user} 在【{object}】中进行了评论：{content}';
        let content = contentTemplate.replace('{user}', loggedUser.username);
        let objectName = this.props.objectName ? this.props.objectName : '页面：' + document.title;
        content = content.replace('{object}', objectName).replace('{content}', content_text);
        setData.url = this.props.notificationUrl ? this.props.notificationUrl : window.location.href;
        setData.content = content;
        setData.users = userList;
        commonRequest('POST', '/api/notifications/send', setData, function () {
        })
    }


    deleteComment(id) {
        let that = this;
        let url = '/api/comments/' + id;
        commonRequest('DELETE', url, {}, function (data) {
            if (data.result) {
                that.getCommentList(that.props, function (commentCount) {
                    if (that.props.onUpdateCommentList) {
                        that.props.onUpdateCommentList(commentCount)
                    }
                });
            } else {
                alert(data.message)
            }
        })
    }

    stickComment(id) {
        let that = this;
        let url = '/api/comments/' + id + '/stick';
        commonRequest('POST', url, {}, function (data) {
            if (data.result) {
                that.getCommentList()
            } else {
                alert(data.message)
            }
        })
    }

    cancelTheTopOfComment(id) {
        let that = this;
        let url = '/api/comments/' + id + '/stick/cancel';
        commonRequest('POST', url, {}, function (data) {
            if (data.result) {
                that.getCommentList()
            } else {
                alert(data.message)
            }
        })
    }

    reply(name,itemData) {
        this.setState({
            currentItemData: itemData,
        })
        this.child.changeInputRef(name + ' ')
    }

    onRef(ref) {
        this.child = ref
    }

    seletPointComment(uid){
        setTimeout(()=>{
            let height = $('#version_content-section').height()+$('.version-info').height()+$('.edit-title').height()+154;
            if( PageData.reportData.report_type == 'lead'){
                height = $('#version_content-section').height()+$('.leads-info').height()+$('.edit-title').height()+154;
            }
            if($(`.annotation[comment_uid="${uid}"]`).length>0){
                $(`.annotation[comment_uid="${uid}"]`).click()
                $('.report-container').scrollTop($(`.annotation[comment_uid="${uid}"]`).position().top+height)
            }else if($(`.gear-all-image[comment_uid="${uid}"]`).length>0){
                setTimeout(()=>{
                    $(`.gear-all-image[comment_uid="${uid}"]`).click()
                },200)
                console.log(uid,$(`.gear-all-image[comment_uid="${uid}"]`).position().top + height);
                $('.report-container').scrollTop($(`.gear-all-image[comment_uid="${uid}"]`).position().top+height)
            }else if($(`.estimate-box[comment_uid="${uid}"]`).length>0){
                $(`.gear-comment-box-plan[comment_uid="${uid}"]`).click()
                let height2 = $('.main-sections').height()+20
                $('.report-container').scrollTop($(`.estimate-box[comment_uid="${uid}"]`).position().top+height+height2)
            }
        },200)
    }

    render() {
        let CommonItemList = this.state.commentList.map((commentItem, index) => {
            return <CommentItem
                reply={this.reply.bind(this)}
                key={index}
                comment={commentItem}
                deleteComment={this.deleteComment.bind(this)}
                stickComment={this.stickComment.bind(this)}
                cancelTheTopOfComment={this.cancelTheTopOfComment.bind(this)}
            />
        });

        let PointCommonItemList = this.props.pointCommentData && this.props.pointCommentData.map((item, index) => {
            if(item.comments && item.comments.length>0){
                return <div className='point-comment-list' data-uid={item.uid} key={item.id} onClick={()=>this.seletPointComment(item.uid)}>
                    {
                        item.comments.map((item2,index2)=>{
                            return (
                              <CommentItem
                                isPoint={true}
                                reply={this.reply.bind(this)}
                                key={item2.id}
                                comment={item2}
                                deleteComment={this.deleteComment.bind(this)}
                                stickComment={this.stickComment.bind(this)}
                                cancelTheTopOfComment={this.cancelTheTopOfComment.bind(this)}
                              />
                            )
                        })
                    }
                </div>
            }else{
                return null
            }

        });
        return (
            <div className={this.props.class ? "comments-container " + this.props.class : "comments-container"}
                 style={this.props.style ? this.props.style : null}>
                {
                    this.props.size == 'small' ?
                        <NewCommentInputComponentDefault
                            size='small'
                            userList={this.state.userList}
                            commentList={this.state.commentList}
                            onRef={this.onRef.bind(this)}
                            submitComment={this.submitComment.bind(this)}
                        /> : null
                }

                {
                    this.props.size != 'small' ?
                        <NewCommentInputComponentDefault
                            size='default'
                            userList={this.state.userList}
                            commentList={this.state.commentList}
                            onRef={this.onRef.bind(this)}
                            submitComment={this.submitComment.bind(this)}
                        /> : null
                }

                {
                    this.state.commentList.length <= 0 && (this.props.pointCommentData && this.props.pointCommentData.length <= 0)
                      ? ''
                      :
                      <div className="comments-list" ref="commentListContent">
                          {CommonItemList}
                          {PointCommonItemList}
                      </div>
                }

                {
                    this.state.commentList.length <= 0 && (this.props.pointCommentData && this.props.pointCommentData.length <= 0) && this.props.showEmptyIcon !== false
                        ?
                        this.props.size != 'small' ?
                            <div className='no-reviews'>
                                <img src={require('./Icon-noReviews.svg')} alt=""/>
                                <div>没有评论和备注</div>
                            </div> :
                            <div className='no-reviews' style={{padding: '0px 16px 16px'}}>
                                <div>没有评论和备注</div>
                            </div>
                        : null
                }
            </div>
        )
    }
}


// 评论区域
class NewCommentInputComponentDefault extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            commentMsg: toContentState(''),
            notificationList: [],
            buttonDisabled: true,

            isFocus: false, //离焦
            value: '',  //输入框中返回的值
            text: '',
            userList: [],
        }
    }

    componentDidMount() {
        if (this.props.onRef && this.props.onRef != '') {
            this.props.onRef(this);
        }
    }


    onFocus() {
        this.setState({
            isFocus: true
        })
    }

    onBlur() {
        setTimeout(() => {
            this.setState({
                isFocus: false
            })
        }, 200)
    }

    //提交发送
    handelSetComment() {
        let that = this;
        let content = this.state.value;
        let content_text = this.state.text;
        if (content && content.trim()) {
            let atUserList = [];
            for (let i = 0; i < this.state.userList.length; i++) {
                let userItem = this.state.userList[i];
                let username = userItem.replace(/@*/, '');
                if (username != loggedUser.username) {
                    atUserList.push(username)
                }
            }
            this.props.submitComment(content, content_text, atUserList, function () {
                that.setState({
                    commentMsg: toContentState(''),
                    buttonDisabled: true,
                });
                that.child.setUserValue('');
            })
        }
    }

    //点击取消
    handelCancel() {
        this.setState({
            commentMsg: toContentState(''),
            value: '',
            buttonDisabled: true,
        });
        this.child.setUserValue('');
    }

    //父级触发的回复
    changeInputRef(val) {
        this.setState({
            commentMsg: toContentState('@' + val),
        });
        this.refs.GearMentionRef.setUserValue(val);
    }

    //返回值
    changeVal(htmls, text, users) {
        this.setState({
            value: htmls,  //
            text: text,
            userList: users,
        });

        if (htmls.trim()) {
            this.setState({
                buttonDisabled: false,
            });
        } else {
            this.setState({
                buttonDisabled: true,
            });
        }
    }

    //回车
    enterCall(htmls, text, users) {
        this.setState({
            value: htmls,  //
            text: text,  //输入框中返回的值
            userList: users,
        }, () => {
            this.handelSetComment()
        })
    }

    onRef(ref) {
        this.child = ref;
    }

    render() {
        let styleFlex = {
            flex: 'initial'
        }
        if (this.props.commentList > 0) {
            styleFlex = {
                flex: '1'
            }
        }
        return (
            <div
                className={this.props.size == 'small' ? "edit-comments-area small-size" : 'edit-comments-area'}
                style={this.props.size == 'small' ? null : styleFlex}
            >
                <GearMention
                    ref='GearMentionRef'
                    onRef={this.onRef.bind(this)}
                    userList={this.props.userList}
                    changeVal={this.changeVal.bind(this)}
                    enterCall={this.enterCall.bind(this)}
                    placeholder='请输入评论'
                />
                <div className='edit-comments-area-bottom'>
                    {
                        this.props.size == 'small' ? null :
                            <button
                                type='submit'
                                onClick={this.handelCancel.bind(this)}
                                className="btn-type btn-gray comment-set-btn"
                            >取消
                            </button>
                    }
                    <button
                        type='submit'
                        onClick={this.handelSetComment.bind(this)}
                        className={this.state.buttonDisabled ? "btn-type btn-blue comment-sub-btn disable-btn" : "btn-type btn-blue comment-sub-btn"}
                        disabled={this.state.buttonDisabled}>{this.props.size == 'small' ? '评论' : '发送'}
                    </button>
                </div>
            </div>

        )
    }
}


// 评论单个组件
class CommentItem extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            showCommentButtons: false,
            showCancelTopButton: false,
        }
    }

    reply(name) {
        this.props.reply(name,this.props.comment)
    }

    deleteComment() {
        let that = this;
        that.props.deleteComment(that.props.comment.id)
    }

    stickComment() {
        this.props.stickComment(this.props.comment.id)
    }

    cancelTheTopOfComment() {
        this.props.cancelTheTopOfComment(this.props.comment.id)
    }

    showCommentButtons() {
        this.setState({
            showCommentButtons: true,
        });
    }

    hideCommentButtons() {
        this.setState({
            showCommentButtons: false,
        });
    }

    showCancelTopButton() {
        this.setState({
            showCancelTopButton: true,
        });
    }

    closeCancelTopButton() {
        this.setState({
            showCancelTopButton: false,
        });
    }

    render() {
        var commentData = this.props.comment;
        var showCommentButtons = this.state.showCommentButtons;
        var showCancelTopButton = this.state.showCancelTopButton;
        return (
            <div className="media comment-item" onMouseEnter={this.showCommentButtons.bind(this)}
                 onMouseLeave={this.hideCommentButtons.bind(this)}>
                <div className="media-left" style={{marginRight: '8px'}}>
                    {
                        commentData.author.avatar_url
                            ? <AvatarImg style={{fontSize: '16px'}} size={24} imgUrl={commentData.author.avatar_url}/>
                            : <AvatarImg bgColor={commentData.author.avatar_color} style={{fontSize: '16px'}} size={24}
                                         text={commentData.author.username.substring(0, 1)}/>
                    }
                </div>
                <div className="media-body comments-content">
                    <p className="comments-time">
                        <span className='text-name'>{commentData.author.username}</span>
                        <span
                          style={this.props.isPoint?{display:'inline'}:{}}
                            className='text-time'>{getWaitDuration(commentData.created_at, moment().format('YYYY-MM-DD HH:mm'))}</span>
                        {
                            !this.props.isTwo && !this.props.isPoint
                              ?
                              <span className="user-btn"
                                    onClick={showCommentButtons ? this.reply.bind(this, commentData.author.username) : null}>回复</span>
                              :''
                        }
                        {
                            commentData.child_comments.length <= 0 && !this.props.isPoint &&
                            <span className="user-btn"
                                  onClick={showCommentButtons ? this.deleteComment.bind(this) : null}>删除</span>
                        }

                    </p>
                </div>
                <div className="comments-msg" dangerouslySetInnerHTML={{__html: commentData.content}}>
                    {/*{commentData.content}*/}
                </div>
                {
                    commentData.child_comments && commentData.child_comments.length>0 &&
                    <div className='children-box'>
                        {
                            commentData.child_comments.map((item, index) => {
                                return <CommentItem
                                  isPoint={this.props.isPoint}
                                  isTwo={true}
                                  reply={this.props.reply}
                                  key={index}
                                  comment={item}
                                  deleteComment={this.props.deleteComment}
                                  stickComment={this.props.stickComment}
                                  cancelTheTopOfComment={this.props.cancelTheTopOfComment}
                                />
                            })
                        }
                    </div>
                }

            </div>
        )
    }
}

