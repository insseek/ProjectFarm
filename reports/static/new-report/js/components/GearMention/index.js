import React from 'react';
import './index.scss';

/** 提及组件
 *
 *
 */
export default class Index extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            placeholder: this.props.placeholder && this.props.placeholder != '' ? this.props.placeholder : '请输入',
            addUserList: [],
            userNameData: [],
        };
    }

    componentDidMount() {
        // 将子组件的this通过父组件的方法返回给父组件
        this.props.onRef(this)


        this.commentsGetUserList();

        let elem = $(this.refs.gearAtDiv);
        let that = this;


        elem.on('input', '.gear-at-textarea', function () {
            $(that.refs.userInfo).hide();
            if ($(that.refs.gearAt).text() == '' && $(that.refs.gearAt).html() == '') {
                that.setState({
                    placeholder: that.props.placeholder,
                })
            } else {
                that.setState({
                    placeholder: '',
                })
            }


            let userNameDom = $(that.refs.gearAtDiv).find('.atwho-inserted');
            var userNameData = [];
            if (userNameDom.length > 0) {
                userNameDom.each(function () {
                    userNameData.push($(this).text())
                })
            }
            that.setState({
                userNameData: userNameData,
            })
            that.props.changeVal($(that.refs.gearAt).html(), $(that.refs.gearAt).text(), userNameData);
            // this.props.onChange
        })
        elem.on('change', '.gear-at-textarea', function () {
            $(that.refs.userInfo).hide();


            let userNameDom = $(that.refs.gearAtDiv).find('.atwho-inserted');
            var userNameData = [];
            if (userNameDom.length > 0) {
                userNameDom.each(function () {
                    userNameData.push($(this).text())
                })
            }
            that.setState({
                userNameData: userNameData,
            });
            that.props.changeVal($(that.refs.gearAt).html(), $(that.refs.gearAt).text(), userNameData);
        });
        elem.on('click', '.gear-user-box', function () {
            // elem.find('.user-info').hide()
        })
        /*elem.on('mouseover','.gear-user-box',function(e){
            let left = $(e.target).position().left;
            let top = $(e.target).position().top;
            let width = $(e.target).width();
            let height = $(e.target).height();


            let imgDom = "<img onerror='userAvatarImgError(this)' color='"+$(e.target).attr('color')+"' name='"+$(e.target).attr('username')+"' widthSize='40' fontSize='18' src='"+$(e.target).attr('avatarUrl')+"' />"
            elem.find('.imgbox').html(imgDom);

            elem.find('.user-info-name').html($(e.target).attr('userName'));
            elem.find('.user-info-email').html($(e.target).attr('email'));


            let user_info_top = top+height+4;
            let user_info_left = left;

            //所在位置杯右侧边界遮住
            if( $(e.target).offset().left + 240 > $(window).width() ){
                user_info_left = left - 240 + width;
            }

            //所在位置超过网页的高度
            if( $(e.target).offset().top + elem.find('.user-info').height() > $(window).height() ){
                user_info_top = top - elem.find('.user-info').height()
            }
            elem.find('.user-info').css({
                top: user_info_top,
                left: user_info_left
            }).show();
        })
        elem.on('mouseout','.gear-user-box',function(e){
            elem.find('.user-info').hide();
        })*/

    }

    componentWillReceiveProps(nextProps) {
    }

    //设置默认评论人
    setUserValue(val) {
        let that = this;
        var url = '/api/users/';

        if (val && val != '') {
            if (this.state.addUserList.length > 0) {
                let userData = '';
                let htmls = '';

                for (let i = 0; i < this.state.addUserList.length; i++) {
                    if (val.trim() == this.state.addUserList[i].username.trim()) {
                        userData = this.state.addUserList[i];
                        break;
                    }
                }

                if (userData != '') {
                    htmls = `<span 
                                class="atwho-inserted" 
                                data-atwho-at-query="@" 
                                contenteditable="false"><div 
                                    id="{id}" 
                                    username="{username}" 
                                    avatarurl="{avatar_url}" 
                                    color="{avatar_color}" 
                                    name="{username}" 
                                    email="{email}" 
                                class="gear-user-box" 
                                href="javascript:;">@{username}</div></span>&nbsp;`
                    let fields = ['username', 'id', 'avatar_url', 'avatar_color', 'email'];
                    for (let field_name of fields) {
                        let replaceStr = '{' + field_name + '}';
                        htmls = htmls.replace(new RegExp(replaceStr, 'g'), userData[field_name])
                    }
                } else {
                    htmls = val;
                }
                that.props.changeVal(htmls, $(htmls).text(), [val]);
                that.setState({
                    placeholder: '',
                    userNameData: [val],
                });
                $(that.refs.gearAt).focus().html(htmls);
                var range = window.getSelection();//创建range
                range.selectAllChildren(that.refs.gearAt);//range 选择obj下所有子内容
                range.collapseToEnd();//光标移至最后
            } else {
                $.ajax({
                    url: url,
                    dataType: 'json',
                    success: (data) => {

                        let userData = '';
                        let htmls = '';
                        for (let i = 0; i < data.data.length; i++) {
                            if (val.trim() == data.data[i].username.trim()) {
                                userData = data.data[i];
                                break;
                            }
                        }
                        if (userData != '') {
                            htmls = `<span 
                                class="atwho-inserted" 
                                data-atwho-at-query="@" 
                                contenteditable="false">
                                <div 
                                    id="{id}" 
                                    username="{username}" 
                                    avatarurl="{avatar_url}" 
                                    color="{avatar_color}" 
                                    name="{username}" 
                                    email="{email}" 
                                class="gear-user-box" 
                                href="javascript:;">
                                @{username}
                                </div>
                                </span>&nbsp;`;
                            let fields = ['username', 'id', 'avatar_url', 'avatar_color', 'email'];
                            for (let field_name of fields) {
                                let replaceStr = '{' + field_name + '}';
                                htmls = htmls.replace(new RegExp(replaceStr, 'g'), userData[field_name])
                            }
                        } else {
                            htmls = val;
                        }

                        that.props.changeVal(htmls, $(htmls).text(), [val]);

                        that.setState({
                            placeholder: '',
                            userNameData: [val],
                        })
                        $(that.refs.gearAt).focus().html(htmls);
                        var range = window.getSelection();//创建range
                        range.selectAllChildren(that.refs.gearAt);//range 选择obj下所有子内容
                        range.collapseToEnd();//光标移至最后

                    },
                });
            }
        } else {
            $(that.refs.gearAt).html('');
            that.props.changeVal('', '', []);
            that.setState({
                placeholder: this.props.placeholder,
                userNameData: [],
            })
        }

    }

    // 获取评论人 提示人列表
    commentsGetUserList() {
        let that = this;
        var url = '/api/users/';
        $.ajax({
            url: url,
            dataType: 'json',
            success: (data) => {

                that.setState({
                    addUserList: data.data,
                })

                let opt = {
                    userList: data.data,
                    enterCallbick: function () {
                        that.props.enterCall($(that.refs.gearAt).html(), $(that.refs.gearAt).text(), that.state.userNameData);

                        $(that.refs.gearAt).html('');
                        that.setState({
                            placeholder: that.props.placeholder
                        })
                    }
                }
                $(that.refs.gearAt).atwho({
                    at: "@",
                    data: opt.userList,
                    displayTpl: "<li><img color='${avatar_color}' name='${username}' widthSize='24' fontSize='12' src='${default_avatar}' onerror='userAvatarImgError(this)'/>${username}</li>",
                    insertTpl: "<div id='${id}' userName='${username}' avatarUrl='${avatar_url}' color='${avatar_color}' name='${username}' email='${email}' class='gear-user-box' href='javascript:;'>@${username}</div>",
                    limit: 40,
                    searchKey: "username",
                    sendFun: function (val) {
                        opt.enterCallbick(val)
                    }
                });

            },
        });
    }

    render() {
        return (
            <div className="gear-at-div" ref='gearAtDiv'>
                <div className="gear-at-textarea"
                     ref='gearAt'
                     contentEditable="true"
                     data-beforeContent={this.state.placeholder}></div>

                {/*<div className="user-info" ref='userInfo'>
                    <div className="user-info-box">
                        <div className="imgbox">
                            <img src=""/>
                        </div>
                        <div className="user-info-center">
                            <div className="user-info-name"></div>
                            <div className="user-info-email"> </div>
                        </div>
                    </div>
                </div>*/}
            </div>
        );
    }
}


