$(document).on('ready', function () {
    function alignModal() {
        var modalDialog = $(this).find('.modal-dialog');
        // Applying the top margin on modal dialog to align it vertically center
        modalDialog.css('margin-top', Math.max(0, ($(window).height() - 138) / 2));
    }

    // Align modal when it is displayed
    $('.modal').on('shown.bs.modal', alignModal);
    // Align modal when user resize the window
    $(window).on('resize', function () {
        $('.modal:visible').each(alignModal);
    });

    $('.modal').each(alignModal);

    var displayRigthButton = function () {
        var w = $(document).width();
        var y = $(window).scrollTop();
        var wMain = 980 //$('.main-content').width();
        if (w >= wMain + 600) {
            var right = (w - wMain) / 2 - 200;
            $('.right-btn').css('right', right)
            // $('.content-nav').css('visibility','visible')
        } else if (w < wMain + 600 && w >= wMain + 280) {
            var right = ((w - wMain) / 2 - 100) / 2;
            $('.right-btn').css('right', right)
            // $('.content-nav').css('visibility','visible')
        } else {
            // $('.content-nav').css('visibility','hidden')
        }
    };

    var displayNextImage = function () {
        var w = $(document).width();
        if (w >= 768) {
            $('.next-img').attr('src', '/static/reports/images/next@2x.png');
        } else
            $('.next-img').attr('src', '/static/reports/images/next-sm@2x.png');
    };

    var displayNav = function () {
        var w = $(document).width();
        var y = $(window).scrollTop();
        var wMain = 980 //$('.main-content').width();
        if (w >= wMain + 600) {
            var right = (w - wMain) / 2 - 200;
            $('.content-nav').css('right', right)
            // $('.content-nav').css('visibility','visible')
        } else if (w < wMain + 600 && w >= wMain + 280) {
            var right = ((w - wMain) / 2 - 100) / 2;
            $('.content-nav').css('right', right)
            // $('.content-nav').css('visibility','visible')
        } else {
            $('.content-nav').css('right', 0)
            // $('.content-nav').css('visibility','hidden')
        }
    };
    var smWidth = $(document).width();
    if (smWidth <= 414) {
        $('#content-scrollspy').css({'position': 'fixed'});
    }
    $(window).scroll(function () {
        if ($(window).scrollTop() == 0) {
            $('.nav-stacked').css({'padding-top': 0});
        }
        displayRigthButton();
        displayNextImage();
        displayNav();
    });

    displayNav();
    displayRigthButton();
    $(window).resize(function () {
        displayRigthButton();
        displayNextImage();
        displayNav();
    });
    //折叠菜单栏按钮
    FastClick.attach(document.getElementById('nav-taggle-btn'));
    $('#nav-taggle-btn').click(function () {
        $('.icon-bar').toggleClass('blue');
        if (smWidth <= 414) {
            $('body').toggleClass('body-hidden');
        }
        $('.logo-bar').toggleClass('opcity-none');
    });

    $('.ph-read-more').click(function () {
        $('.ph-screen').fadeOut();
    });
    $('.ph-screen-btn').click(function () {
        $('.ph-screen').fadeOut();
        $('body').removeClass('face-hidden');
    });

    $('section p').has('img').addClass('img-border');

    $('.ph-read-more').click(function () {
        $('body').removeClass('face-hidden');
    });

    //手机端禁用图片点击预览
    if (smWidth <= 414) {
        $('.img-border a').removeAttr('data-toggle');
        $('.img-border a').removeAttr('href');
        $('.img-border a').click(function (e) {
            e.preventDefault();
        });
    }
    // 目录点击事件
    var w = $(document).width();
    $('.nav-stacked').on('click', 'li > a', function () {
        $('.icon-bar').toggleClass('blue');
        $('.content-nav').removeClass('in');
        if (w <= 414) {
            $('body').toggleClass('body-hidden');
        }
        $('.logo-bar').toggleClass('opcity-none');
    });
    $('body').on('click', '.modal-backdrop', function () {
        $(this).css({'display': 'none'});
    });

    // 生成uuid
    function guid() {
        function s4() {
            return Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1);
        }

        return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
    }

    // 报告评分
    function reportRate() {
        var commentUid = guid();
        var ratingValue = 0;
        var filledStarUrl = '/static/reports/images/star.png';
        var emptyStarUrl = '/static/reports/images/star_outline.png';
        $('#report-rating').rating({
            hoverOnClear: false,
            showCaption: false,
            showClear: false,
            clearCaption: '',
            step: 1,
            filledStar: '<i><image width="40px" src="' + filledStarUrl + '"></i>',
            emptyStar: '<i><image width="40px" src="' + emptyStarUrl + '"></i>'
        });

        $('#report-rating').on('rating.change', function (event, value, caption) {
            ratingValue = value;
            $('#rate-ok-btn').attr({'disabled': false});
            $('.rate-btn').css('display', 'inline-block');
        });

        var rateSub = function () {
            let url = '/reports/' + PageData.reportData.uid + '/grade';
            let subData = {rate: ratingValue, uid: commentUid, report_uid: PageData.reportData.uid};
            commonRequest('POST', url, subData, function () {
                $('#report-rating').rating('refresh', {readonly: true});
                var ratingData = {
                    value: ratingValue,
                    uid: commentUid
                };
                localStorage.setItem(PageData.reportData.uid, JSON.stringify(ratingData));
                $('#rate-cancel-btn').css('display', 'none');
                $('#rate-tip').text('感谢您的打分');

            })

        };

        var clearRate = function () {
            var w = $(document).width();
            // if(w <= 414){
            // $('#rate-cancel-btn').css('display', 'inline-block');
            // }else{
            $('#rate-cancel-btn').css('display', 'none');
            // }
            $('#rate-ok-btn').attr({'disabled': true});
            ratingValue = 0;
            $('#report-rating').rating('update', ratingValue);
        };

        $('#rate-ok-btn').click(rateSub);
        $('#rate-cancel-btn').click(clearRate);
        var ratingData = localStorage.getItem(PageData.reportData.uid) || null;
        if (ratingData) {
            ratingData = JSON.parse(ratingData);
        }
        if (ratingData) {
            ratingValue = ratingData.value;
            commentUid = ratingData.uid;
            $('#rate-tip').text('感谢您的打分');
            $('#report-rating').rating('update', ratingValue);
            $('#report-rating').rating('refresh', {readonly: true});
        }
    }

    reportRate()


    //小屏时显示隐藏导航
    $('.header-taggle').click(function () {
        $(".nav-box").toggleClass("ishide");
    })



    //获取缓存中本报告的评论信息
    let report_comment_key = PageData.reportData.uid+'_COMMENT';
    let commentData = localStorage.getItem(report_comment_key) && JSON.parse(localStorage.getItem(report_comment_key)) ? JSON.parse(localStorage.getItem(report_comment_key)) : {};
    if( commentData.level ){
        $('.comment-box-init-pc').hide();
        $('.comment-box-over-pc').show();

        $('.comment-box-init').hide();
        $('.comment-box-over').show();
    }


});


//评论 PC
// 好评
function commentPraisePc() {
    requestComment('helpful')
}
// 差评
function commentNegativePc() {
    $('.comment-box-init-pc').hide()
    $('.comment-box-change-pc').show()
}
//选择差评理由
function selectCommentPc(obj) {
    if($(obj).hasClass('active')){
        $(obj).removeClass('active');
    }else{
        $(obj).addClass('active');
    }
}
//提交差评信息
function commentConfimPc() {
    let data = [];
    $('.comment-selects-pc.active').each(function(){
        data.push($(this).attr('data-val'))
    })
    requestComment('not_helpful',data.join())

}


//评论 移动
// 好评
function commentPraise() {
    requestComment('helpful')
}
// 差评
function commentNegative() {
    $('.comment-box-init').hide()
    $('.comment-box-change').show()
}
//选择差评理由
function selectComment(obj) {
    if($(obj).hasClass('active')){
        $(obj).removeClass('active');
    }else{
        $(obj).addClass('active');
    }
}
//提交差评信息
function commentConfim() {
    let data = [];
    $('.comment-selects.active').each(function(){
        data.push($(this).attr('data-val'))
    })
    requestComment('not_helpful',data.join())

}



// 调用评论接口
function requestComment(level = 'helpful',remarks = ''){
    let params = {
        "uid": getCommentUid(), //前端生成一个评分UUID 标记一次评分
        "level": level, //helpful not_helpful
    }
    if(remarks){
        params.remarks = remarks
    }
    commonRequest('post',`/api/reports/${PageData.reportData.uid}/evaluations`,params,function (res){
        let report_comment_key = PageData.reportData.uid+'_COMMENT';
        localStorage.setItem(report_comment_key, JSON.stringify(params));
        //调用接成功后回调
        $('.comment-box-init-pc').hide()
        $('.comment-box-change-pc').hide()
        $('.comment-box-over-pc').show()

        $('.comment-box-init').hide()
        $('.comment-box-change').hide()
        $('.comment-box-over').show()
    })
}

//评论uid
function getCommentUid(){
    var commentUid = getUUID();
    return commentUid
}