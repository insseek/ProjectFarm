function commonUploadFile(url, formData, func){
    $.ajax({
        url: url,
        method: "POST",
        data: formData,
        async:true,
        processData: false,
        contentType: false,
        dataType: "json",
        // timeout:'15000',
        success: function (data) {
            func(data);
        },
        error:function(jqXHR, textStatus, errorThrown){
            if(jqXHR.status == '500'){
                func('网络异常，请检查网络');
            }else{
                func('上传失败，请重新上传');
            }
        }
    });
}

//图片报错时的回掉 -- 用于头像
function userAvatarImgError(e){
    let widthSize = $(e).attr('widthSize') && $(e).attr('widthSize')!='' ? $(e).attr('widthSize')+'px' : '20px';
    let fontSize = $(e).attr('fontSize') && $(e).attr('fontSize')!='' ? $(e).attr('fontSize')+'px' : '20px';
    let name = $(e).attr('name').substring(0, 1);
    let color = $(e).attr('color') && $(e).attr('color')!=''? $(e).attr('color') : '#9199ab';

    let spanDom = '';
    if(!$(e).attr('src') || $(e).attr('src')=='' || $(e).attr('src')==null || $(e).attr('src')=='null' || $(e).attr('src')==undefined || $(e).attr('src')=='undefined'){
        spanDom = `
            <span class="m-span" style="font-size: ${fontSize}; width: ${widthSize}; height: ${widthSize}; line-height: ${widthSize}; background-color: ${color};">
                <div class="m-border"></div>
                ${name}
            </span>
        `
    }else{
        spanDom = '<img src="/static/new-report/img/default_avatar_img.svg">';
    }
    $(e).replaceWith($(spanDom)[0]);
}

// 判断弹窗提示
var farmConfirm = function (msg, successFun) {
    var modalDom = `
        <div id="farmConfirm">
            <div class="confirm-dialog">
                <div class="dialog-body">
                    <span class="dialog-message">${msg}</span>
                </div>
                <div class="dialog-footer">
                    <button type="button" class="gear-btn-new gray-btn" id="farmConfirmCancel">取消</button>
                    <button type="button" class="gear-btn-new def-btn" id="farmConfirmConfirm">确认</button>
                </div>
            </div>
        </div>
    `;
    $('body').append(modalDom);

    // 确定按钮
    $('#farmConfirmConfirm').click(function () {
        successFun();
        $('#farmConfirm').remove()
    });
    // 取消按钮
    $('#farmConfirmCancel').click(function () {
        $('#farmConfirm').remove()
    });


};


// 弹窗提示New
var farmAlter = function (msg, speed) {
    var showSpeed = speed ? speed : 1500;

    if ($('#messageAlert').length <= 0) {
    } else {
        $('#messageAlert').remove();
    }

    var modalDom = `
        <div id="messageAlert" style="
            position: fixed;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            z-index: 1050;"
        >
            <div style="
                position: absolute;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.3);
            "></div>
            <div style="
                width: 400px;
                min-height: 56px;
                padding: 16px;
                margin: 120px auto;
                background: #333333;
                border-radius: 5px;
                font-size: 16px;
                color: #fafafa;
                position: relative;
            ">${msg}</div>
        </div>
    `;

    $('body').append(modalDom);
    setTimeout(function () {
        $('#messageAlert').remove()
    }, showSpeed);
};
//评论中@用户
;(function ($) {
    $(function () {

        $('section.sidebar-mini li').hover(function () {
            $('section.sidebar-mini').width('300px')
        }, function () {
            $('section.sidebar-mini').width('50px')
        })


        var dom = `
            <div id="gearUserInfo" class="user-info">
                <div class="user-info-box">
                    <div class="imgbox">
                        <img src=""/>
                    </div>
                    <div class="user-info-center">
                        <div class="user-info-name"></div>
                        <div class="user-info-email"> </div>
                    </div>
                </div>
            </div>
        `;
        $('body').append(dom);


        var userList = [];


        if (userList.length <= 0) {
            let url = '/api/users';
            commonRequest('get', url, '', (res) => {
                userList = res.data;
                $('body').on('mouseover', '.gear-user-box', function (e) {
                    var left = $(e.target).offset().left;
                    var top = $(e.target).offset().top - $(document).scrollTop();
                    var width = $(e.target).width();
                    var height = $(e.target).height();

                    var windowWidth = $(window).width();
                    var windowHeight = $(window).height();

                    var activeUser = null;
                    for (var i = 0; i < userList.length; i++) {
                        if ($(e.target).attr('id') == userList[i].id) {
                            activeUser = userList[i];
                            break;
                        }
                    }
                    if (!activeUser) {
                        return
                    }
                    let imgDom = '<img src="/static/new-report/img/default_avatar_img.svg">';
                    if (activeUser.avatar_url) {
                        imgDom = "<img onerror='userAvatarImgError(this)' src='" + activeUser.avatar_url + "' />"
                    } else if (activeUser.avatar_color) {
                        let color = activeUser.avatar_color;
                        let name = activeUser.username.substring(0, 1);
                        imgDom = `<span class="m-span" style="font-size: 18px; width: 40px; height: 40px; line-height: 40px; background-color: ${color};">
                                        <div class="m-border"></div>
                                        ${name}
                                        </span>`
                    }


                    var elem = $('#gearUserInfo');

                    elem.find('.imgbox').html(imgDom);

                    elem.find('.user-info-name').html(activeUser.username);
                    elem.find('.user-info-email').html(activeUser.email);


                    let user_info_top = top + height;
                    let user_info_left = left;

                    //所在位置杯右侧边界遮住
                    if (left + 240 > windowWidth) {
                        user_info_left = left - 240 + width;
                    }

                    //所在位置超过网页的高度
                    if (top + elem.height() > windowHeight) {
                        user_info_top = top - elem.height()
                    }

                    elem.css({
                        top: user_info_top,
                        left: user_info_left
                    }).show();

                })
                $('body').on('mouseout', '.gear-user-box', function (e) {
                    $('#gearUserInfo').hide();
                })
            })
        } else {
            $('body').on('mouseover', '.gear-user-box', function (e) {
                var left = $(e.target).offset().left;
                var top = $(e.target).offset().top - $(document).scrollTop();
                var width = $(e.target).width();
                var height = $(e.target).height();

                var windowWidth = $(window).width();
                var windowHeight = $(window).height();

                var activeUser = null;
                for (var i = 0; i < userList.length; i++) {
                    if ($(e.target).attr('id') == userList[i].id) {
                        activeUser = userList[i];
                        break;
                    }
                }

                if (!activeUser) {
                    return
                }

                let imgDom = '<img src="/static/new-report/img/default_avatar_img.svg">';
                if (activeUser.avatar_url) {
                    imgDom = "<img onerror='userAvatarImgError(this)' src='" + activeUser.avatar_url + "' />"
                } else if (activeUser.avatar_color) {
                    let color = activeUser.avatar_color;
                    let name = activeUser.username.substring(0, 1);
                    imgDom = `<span class="m-span" style="font-size: 18px; width: 40px; height: 40px; line-height: 40px; background-color: ${color};">
                                        <div class="m-border"></div>
                                        ${name}
                                        </span>`
                }

                var elem = $('#gearUserInfo');

                elem.find('.imgbox').html(imgDom);

                elem.find('.user-info-name').html(activeUser.username);
                elem.find('.user-info-email').html(activeUser.email);


                let user_info_top = top + height;
                let user_info_left = left;

                //所在位置杯右侧边界遮住
                if (left + 240 > windowWidth) {
                    user_info_left = left - 240 + width;
                }

                //所在位置超过网页的高度
                if (top + elem.height() > windowHeight) {
                    user_info_top = top - elem.height()
                }

                elem.css({
                    top: user_info_top,
                    left: user_info_left
                }).show();

            })
            $('body').on('mouseout', '.gear-user-box', function (e) {
                $('#gearUserInfo').hide();
            })
        }

        $(document).bind('click', (e) => {
            $('#gearUserInfo').hide();
        })


    })


})(jQuery);
