$(document).on('ready', function () {

    $('h3').each(function () {
        if($(this).attr('id')){
            $(this).append("<span class='anchor-point-h2' id="+$(this).attr('id')+"></span>")
            $(this).attr('id','');
        }
    })


    //pc端左侧导航滚动条
    let scrollBoxHeight = $('.scroll-box').height();
    let scrollHeight = $('.scroll-box .nav-box').outerHeight();
    if(scrollHeight>scrollBoxHeight){
        $('.nav-item-center-scroll').show();
        $('.scroll-item').show();
        let itemHeight = scrollBoxHeight/scrollHeight*scrollBoxHeight
        $('.nav-item-center-scroll .scroll-item').height(itemHeight);

        let scrollTop = $('.scroll-box').scrollTop()/scrollHeight * scrollBoxHeight;
        $('.nav-item-center-scroll .scroll-item').css('top',scrollTop);
    }


    //PC端顶部滚动的高度
    let topBoxHeightPc = $('.project-box').outerHeight()+50
    if($('.info-box') && $('.info-box').outerHeight()){
        topBoxHeightPc += $('.info-box').outerHeight()+30;
    }
    if( $(window).scrollTop() >= topBoxHeightPc-78 ){
        //顶部导航固定展示
        $('.report-header-pc').show()
        $('.nav-item-top-logo').hide()

        $('.nav-item-box-pc').show()
        $('.nav-item-box-pc').css('visibility','visible')
    }else{
        $('.report-header-pc').hide()
        $('.nav-item-top-logo').show()

        $('.nav-item-box-pc').hide()
        $('.nav-item-box-pc').css('visibility','hidden')
    }
    $(window).scroll(function () {
        var offetHeight = $('.nav-item-box-pc .item-list.active') && $('.nav-item-box-pc .item-list.active').position() ? $('.nav-item-box-pc .item-list.active').position().top: 0 ;
        var cHeight = $('.nav-item-box-pc .item-list.active') ? $('.nav-item-box-pc .item-list.active').height() : 0;
        var scrolltops = $('.scroll-box').scrollTop()

        if( $(window).scrollTop() >= topBoxHeightPc-78 ){
            //顶部导航固定展示
            $('.report-header-pc').show()
            $('.nav-item-top-logo').hide()

            $('.nav-item-box-pc').show()
            $('.nav-item-box-pc').css('visibility','visible')



            if( offetHeight < 0 ){
                $('.scroll-box').scrollTop(scrolltops - ( 220- offetHeight+cHeight ))
            }
            if(offetHeight > 390){
                $('.scroll-box').scrollTop(offetHeight + 14 -220+scrolltops)
            }


        }else{
            $('.report-header-pc').hide()
            $('.nav-item-top-logo').show()

            $('.nav-item-box-pc').hide()
            $('.nav-item-box-pc').css('visibility','hidden')
        }
    });


    //异动端顶部滚动的高度
    let topBoxHeightPhone = $('.project-box').outerHeight() + 26
    if($('.info-box') && $('.info-box').outerHeight()){
        topBoxHeightPhone += $('.info-box').outerHeight() + 10;
    }
    if($(window).width()<900) {
        if( $(window).scrollTop() >= topBoxHeightPhone-44*2 ){
            //顶部导航固定展示
            // $('.report-header').show()
            $('.report-header').addClass('show-block')
        }else{
            // $('.report-header').hide()
            $('.report-header').removeClass('show-block')
        }
    }

    $(window).scroll(function () {
        if($(window).width()<900) {
            if( $(window).scrollTop() >= topBoxHeightPhone-44*2 ){
                //顶部导航固定展示
                // $('.report-header').show()
                $('.report-header').addClass('show-block')
            }else{
                // $('.report-header').hide()
                $('.report-header').removeClass('show-block')
            }
        }
    });



    //移动端默认显示封面图禁止滚动 滑动隐藏封面图时才允许滚动
    if($(window).width()<900){
        $('body').addClass('modal-open')
    }
    //屏幕滑动  隐藏封面
    var startY = 0, endY = 0;
    document.addEventListener('touchstart',touchstartHandle,false);
    document.addEventListener('touchend',touchendHandle,false);
    $('.report-cover-modal').click(function(){
        $('.report-cover-modal').hide();
        $('body').removeClass('modal-open');
        document.removeEventListener('touchstart',touchstartHandle);
        document.removeEventListener('touchend',touchendHandle);
    })
    function touchstartHandle(e){
        startY= e.touches[0].pageY;
    }
    function touchendHandle(e){
        endY= e.changedTouches[0].pageY;
        moveLoad();
    }
    function moveLoad(){
        var movY=endY-startY;
        if(movY < -10){
            //上滑手势
            if(!$('.report-cover-modal').is(":hidden")){
                $('.report-cover-modal').hide();
                $('body').removeClass('modal-open');
                document.removeEventListener('touchstart',touchstartHandle);
                document.removeEventListener('touchend',touchendHandle);
            }
        }
    }

    //移动端目录的点击
    $('.item-list .title-a').click(function(){
        hideNavTabs();
    })
    $('.item-list .title-group-a').click(function(){
        hideNavTabs();
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


    setTimeout(()=>{
        // 轮播图
        if($(window).width()<900){
            new Swiper('.swiper-container[data-tag-flag="gear-custom-module"]', {
                slidesPerView: 'auto',
                spaceBetween: 20,
                centeredSlides: true,
                centeredSlidesBounds: true,
                slidesOffsetBefore : 20,
                slidesOffsetAfter : 20,
            });
        }else{
            new Swiper('.swiper-container[data-tag-flag="gear-custom-module"]', {
                loop: true,
                loopPreventsSlide: true,
                navigation: {
                    nextEl: '.swiper-button-next-g',
                    prevEl: '.swiper-button-prev-g',
                },
                pagination: {
                    el: '.swiper-pagination',
                    clickable: true
                },
            });
        }

    },100)


    // 轮播图
    new Swiper('.case-swiper-box-pc', {
        slidesPerView: 3,
        spaceBetween: 30,
        slidesPerGroup: 3,
        // loop: true,
        loopFillGroupWithBlank: true,
        pagination: {
            el: '.swiper-pagination',
            clickable: true,
        },
        navigation: {
            nextEl: '.swiper-button-next',
            prevEl: '.swiper-button-prev',
        },
    });
    new Swiper('.case-swiper-box', {
        slidesPerView: 'auto',
        spaceBetween: 20,
        centeredSlides: true,
        centeredSlidesBounds: true,
        slidesOffsetBefore : 20,
        slidesOffsetAfter : 20,
    });


    //锚点动画
    $(".nav a").click(function () {
        $("html, body").animate({scrollTop: $($(this).attr("href")).offset().top +"px"}, 300);
        return false;
    });



    $('.scroll-box').scroll(()=>{
        let scrollBoxHeight = $('.scroll-box').height();
        let scrollHeight = $('.scroll-box .nav-box').outerHeight();
        if(scrollHeight>scrollBoxHeight){
            $('.nav-item-center-scroll').show();
            $('.scroll-box').show();
            let itemHeight = scrollBoxHeight/scrollHeight*scrollBoxHeight
            $('.nav-item-center-scroll .scroll-item').height(itemHeight);

            let scrollTop = $('.scroll-box').scrollTop()/scrollHeight * scrollBoxHeight;
            $('.nav-item-center-scroll .scroll-item').css('top',scrollTop);
        }
    })

});





//移动端目录的点击
function showNavTabs() {
    $('.nav-item-box').show();
    $('body').addClass('modal-open')
}
function hideNavTabs() {
    $('.nav-item-box').hide();
    $('body').removeClass('modal-open')
}

//目录折叠
function showDownHandle(event,el){
    // event.stopPropagation();
    // event.preventDefault();
    // $(el).parent().parent().parent().parent().toggleClass('showdown')
}



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

