(function () {
    var userList = [];

    getUserList();
    function getUserList(){
        return new Promise((resolve, reject) => {
            if (userList == '') {
                let url = '/api/users';
                commonRequest('GET', url, {}, (res) => {
                    userList = res.data;
                    resolve(res.data)
                })
            } else {
                resolve(userList)
            }
        });
    }


    let Inline = Quill.import('blots/inline');

    class CommentBlot extends Inline {
        static create(options) {
            let node = super.create(options);

            node.setAttribute('class', options['class']);
            node.setAttribute('comment_uid', options['comment_uid']);

            return node;

        }
        static formats(node) {
            let data = {
                'class':node.getAttribute('class'),
                'comment_uid':node.getAttribute('comment_uid'),
            };
            return data;
        }
    }

    CommentBlot.blotName = "comment";
    CommentBlot.tagName = "annotation";
    Quill.register({
        'formats/comment': CommentBlot
    });




    class InlineComment {
        constructor(quill) {
            this.quill = quill;
            this.range = null;


            // 评论框有三种 文本评论 图片评论 时间金额预估评论
            this.initTextCommentDom();
            this.initImageCommentDom();
            // this.initPlanCommentDom();

            this.bindHandles();


            this.toolbar = quill.getModule('toolbar');
            if (typeof this.toolbar != 'undefined'){
                this.toolbar.addHandler('comment', this.commentEventHanlder.bind(this));
            }


            //点击指定元素外 富文本中的
            $(document).bind('click', (e) => {
                var event = e || window.event; //浏览器兼容性
                var elem = event.target || event.srcElement;

                while (elem && elem !== '') { //循环判断至跟节点，防止点击的是div子元素
                    if (
                        (
                            elem.id && elem.id == 'GearCommentBox'
                        )
                            ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('ql-comment') >= 0
                        )
                            ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('annotation') >= 0
                        )
                            ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('atwho-container') >= 0
                        )
                            ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('atwho-inserted') >= 0
                        )
                            ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('gear-user-box') >= 0
                        )
                    ) {
                        return;
                    }
                    elem = elem.parentNode;
                }
                $('#GearCommentBox').hide();
                $('.annotation').removeClass('active');
            });

            //点击指定元素外 图片的
            $(document).bind('click', (e) => {
                var event = e || window.event; //浏览器兼容性
                var elem = event.target || event.srcElement;

                while (elem && elem !== '') { //循环判断至跟节点，防止点击的是div子元素
                    if (
                        /*(
                            elem.id &&
                            elem.id == 'MindMapComment'
                        )
                        ||*/
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('gear-all-image') >= 0
                        )
                        ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('img-tip') >= 0
                        )
                        ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('gear-comment-box-img') >= 0 &&
                            elem.className.indexOf('active') >= 0
                        )
                    ) {
                        return;
                    }
                    elem = elem.parentNode;
                }
                $('.gear-comment-box-img.active').removeClass('active');
            });

        }

        //文本评论 （ 所有文本评论只需要一个评论框 ）
        initTextCommentDom(){
            var that = this;
            //文本评论
            let commentDom = `
            <div id="GearCommentBox" class="gear-comment-box" style="width: 240px;display: none">
                <div class="comment-center">
                    <div class="comment-center-list new-scroll-bar">
                        <!--<div class="item-list">
                            <div class="item-list-user">
                                <img src=""/>
                                <span class="user-name"></span>
                                <span class="user-time"></span>
                                <span class="user-btn btn-huifu" user_name="">回复</span>
                                <span class="user-btn btn-sahnchu" comment_id="">删除</span>
                            </div>
                            <div class="item-list-text">
                            </div>
                        </div>-->
                    </div>
                    <div class="comment-center-text">
                        <div class="gear-text-area"></div>
                        <!--<textarea class="text-area"></textarea>-->
                        <div class="text-foot clearfix">
                            <div class="tag-box">
                                <div class="tag-box-div">
                                    <div class="check-tag tag-select-yellow"></div>
                                    <div class="check-flag"></div>
                                </div>
            
                                <div class="tag-list">
                                    <div flag="tag-select-yellow" class="tag-item tag-select-yellow active"></div>
                                    <div flag="tag-select-pink" class="tag-item tag-select-pink"></div>
                                    <div flag="tag-select-green" class="tag-item tag-select-green"></div>
                                    <div flag="tag-select-blur" class="tag-item tag-select-blur"></div>
                                    <div flag="tag-select-purple" class="tag-item tag-select-purple"></div>
                                </div>
                            </div>
                            <button class="sed-btn">发送</button>
                            <button class="cancel-btn" style="display: none">删除</button>
                        </div>
                    </div>
                </div>
            </div>
            `
            this.quill.addContainer($(commentDom)[0]);

            getUserList().then((res)=>{
                userList = res;
                that.initTextCommenText('')
            })


        }
        //初始化评论中的文本输入 -- 文本
        initTextCommenText(val){
            var that = this;
            var params = {
                userList:userList,
                placeholder:'请输入评论',
                defValue:val,
                //按回车键 -- 富文本
                enterCallbick:function(){
                    let val = $('#GearCommentBox .gear-at-textarea').html();
                    if(val==''){
                        return false;
                    }

                    let uid = $('.annotation.active').attr('comment_uid');
                    if(!uid || uid ==''){
                        uid = $('.gear-all-image.active').attr('comment_uid');
                    }

                    let url = '/api/reports/comment_points/'+uid;
                    let data = {
                        content :val,
                        page_title :document.title.trim(),
                        page_url :window.location.href,
                    }
                    commonRequest('POST',url, data, (res) => {
                        if(res.result){
                            if(window.pointState){
                                window.pointState.updatePoint = Math.random()
                            }
                            $('.text-area').val('');
                            that.addListComments(res.data,true);
                            if($('#GearCommentBox .item-list').length > 0){
                                $('#GearCommentBox .cancel-btn').hide();
                            }
                            that.initTextCommenText('');
                        }
                    })
                },
            }
            $('#GearCommentBox .gear-text-area').JqMention(params);
        }

        //图片评论 （ 所有图片评论外层的div ）
        initImageCommentDom(){
            let commentDomImageDiv = `
                <div id="GearImageCommentBox"></div>
            `;
            this.quill.addContainer($(commentDomImageDiv)[0]);
        }


        // 绑定事件
        bindHandles(){
            let that = this;


            //点击已经评论过的富文本 -- 文本
            $('#NewReports').on('click','.annotation',(e)=>{
                $(e.target).addClass('active').siblings().removeClass('active');


                /*let line = Quill.find($('.annotation.active')[0])
                let startIndex = that.quill.getIndex(line);
                let activeLength = line.length();
                that.quill.setSelection(startIndex,activeLength);*/

                //使用文字标签上的class
                let arr = $('.annotation.active')[0].className.split(' ');
                let className = '';
                for(let item of arr){
                    if(item.indexOf('tag-select')>=0){
                        className = item;
                        break;
                    }
                }
                $('.check-tag').attr('class','check-tag '+className);
                $('.tag-item.'+className).addClass('active').siblings().removeClass('active');


                let uid = $('.annotation.active').attr('comment_uid');
                that.getComments(uid).then((res)=>{
                    that.addListComments(res);
                    that.showComments(
                        $(e.target).position().top+$(e.target).height()+'px',
                        'auto',
                        $(e.target).position().left+$(e.target).width()+'px',
                        'auto'
                    )

                })


            })


            //点击图片上的评论
            $('#NewReports').on('click', '.tip-comment-inline', function (e) {
                let uid = $('.gear-all-image.active').attr('comment_uid');
                if(!uid || uid==''){
                    $('#GearCommentBox .comment-center-list').empty();
                    that.getUid().then((res)=>{
                        return that.getComments(res.uid);
                    }).then((res)=>{
                        $('.gear-all-image.active').attr('comment_uid',res.uid);
                        $('.gear-all-image.active').attr('nums',0);

                        let scrollTop = $('.report-container').scrollTop();
                        that.quill.focus();
                        that.quill.update();
                        $('.report-container').scrollTop(scrollTop);


                        /*//图片添加颜色标示
                        $('.gear-all-image.active').attr('class','gear-all-image normal-image active tag-select-yellow');
                        $('.check-tag').attr('class','check-tag tag-select-yellow');
                        $('.tag-item.tag-select-yellow').addClass('active').siblings().removeClass('active');*/

                        //创建图片评论框
                        let className = 'img-'+res.uid;

                        let top = $('.gear-all-image.active').position().top+'px';

                        let commentDomPlan = `
                            <div class="gear-comment-box gear-comment-box-img ${className}" 
                                comment_uid="${res.uid}"
                                style="width: 270px;display: block;left: -280px;top:${top}"
                            >
                                <div style="display: flex;">
                                    <div class="comment-box-num">
                                        <div class="sanjiao"></div>
                                        <span>0</span>
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
                                                    <button class="cancel-btn">删除</button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            `;
                        $('#GearImageCommentBox').append($(commentDomPlan)[0]);

                        setTimeout(()=>{
                            $('.'+className).addClass('active');
                            that.initTextCommenTextImage('');
                        },200)

                    })

                }else{
                    $('.gear-comment-box-img').removeClass('active');
                    if(uid && uid!=''){
                        that.getComments(uid).then((res)=>{
                            let className = 'img-'+$('.gear-all-image.active').attr('comment_uid');

                            //显示对应class下面的评论
                            $('.'+className).addClass('active');
                            that.addListCommentsImage(res);
                        })
                    }
                }

            })
            //插入后的图点击
            $('#NewReports').on('click', '.gear-all-image', (e) => {
                let uid = $('.gear-all-image.active').attr('comment_uid');
                let nums = $('.gear-all-image.active').attr('nums');
                $('.gear-comment-box-img').removeClass('active');
                if(uid && uid!='' && nums && nums>0){
                    that.getComments(uid).then((res)=>{
                        let className = 'img-'+$('.gear-all-image.active').attr('comment_uid');

                        //显示对应class下面的评论
                        $('.'+className).addClass('active');
                        that.addListCommentsImage(res,true);
                    })
                }


            })
            //图片评论中气泡的点击
            $('#NewReports').on('click', '.gear-comment-box-img .comment-box-num', function(e) {
                let uid = $(e.target).parents('.gear-comment-box-img').attr('comment_uid');
                $('#main-sections .gear-all-image').each(function(){
                    if( $(this).attr('comment_uid') == uid ){

                        setTimeout(()=>{
                            // console.log($(this))
                            $(this).click();
                        },10)

                    }
                })
            })





            //点击删除 -- 富文本
            $('#GearCommentBox').on('click','.cancel-btn',(e)=>{
                let line = Quill.find($('.annotation.active')[0])
                let startIndex = that.quill.getIndex(line);
                let activeLength = line.length();
                this.quill.formatText(startIndex, activeLength, 'comment', false);
                $('#GearCommentBox').hide();
            })
            //点击发送 -- 富文本
            $('#GearCommentBox').on('click','.sed-btn',(e)=>{

                let val = $('#GearCommentBox .gear-at-textarea').html();
                if(val==''){
                    return false;
                }

                let uid = $('.annotation.active').attr('comment_uid');
                if(!uid || uid ==''){
                    uid = $('.gear-all-image.active').attr('comment_uid');
                }

                console.log(1231,uid);

                let url = '/api/reports/comment_points/'+uid;
                let data = {
                    content :val,
                    page_title :document.title.trim(),
                    page_url :window.location.href,
                }
                commonRequest('POST',url, data, (res) => {
                    if(res.result){
                        if(window.pointState){
                            window.pointState.updatePoint = Math.random()
                        }

                        $('.text-area').val('');
                        that.addListComments(res.data,true);
                        if($('#GearCommentBox .item-list').length > 0){
                            $('#GearCommentBox .cancel-btn').hide();
                        }
                        that.initTextCommenText('');
                    }

                })


            })
            //点击回复 -- 富文本
            $('#GearCommentBox').on('click','.btn-huifu',(e)=>{
                var val = $(e.target).attr('user_name');
                getUserList().then((res)=>{
                    userList = res;
                    let userData = '';
                    let htmls = ''
                    for(let i = 0 ; i< userList.length;i++){
                        if(val.trim() == userList[i].username.trim()){
                            userData = userList[i];
                            break;
                        }
                    }
                    if(userData!=''){
                        htmls = '<span class="atwho-inserted" data-atwho-at-query="@" contenteditable="false">' +
                            '<div id="'+userData.id+'" username="'+userData.username+'" avatarurl="'+userData.avatar_url+'" color="'+userData.avatar_color+'" name="'+userData.username+'" email="'+userData.email+'" class="gear-user-box" href="javascript:;">'+userData.username+'</div>' +
                            '</span>&nbsp;'
                    }else{
                        htmls = val;
                    }
                    that.initTextCommenText(htmls);
                })
            })
            //点击删除 -- 富文本
            $('#GearCommentBox').on('click','.btn-sahnchu',(e)=>{

                let comment_id = $(e.target).attr('comment_id')
                let url = '/api/comments/'+comment_id;
                commonRequest('DELETE',url, {}, (res) => {
                    if(res.result){
                        if(window.pointState){
                            window.pointState.updatePoint = Math.random()
                        }
                        $(e.target).parent().parent().remove();
                        if($('#GearCommentBox .item-list').length <= 0){
                            $('#GearCommentBox .cancel-btn').show();
                        }
                    }
                })
            })



            //点击发送 -- 图片
            $('#GearImageCommentBox').on('click','.sed-btn',(e)=>{

                let val = $('.gear-comment-box-img.active .gear-at-textarea').html();
                if(val == ''){
                    return false;
                }

                let uid = $('.gear-comment-box-img.active').attr('comment_uid');

                let url = '/api/reports/comment_points/'+uid;
                let data = {
                    content :val,
                    page_title :document.title.trim(),
                    page_url :window.location.href,
                }
                commonRequest('POST',url, data, (res) => {
                    if(res.result){
                        if(window.pointState){
                            window.pointState.updatePoint = Math.random()
                        }

                        that.addListCommentsImage(res.data,true);

                        $('.gear-comment-box-img.active .comment-box-num span').html(res.data.comments.length);
                        $('.gear-all-image.active').attr('nums',res.data.comments.length);

                        $('.gear-comment-box-img.active').show();
                        $('.gear-comment-box-img.active .cancel-btn').hide();

                    }
                })


            })
            //点击删除按钮 -- 图片
            $('#GearImageCommentBox').on('click','.cancel-btn',(e)=>{
                $('.gear-comment-box-img.active').remove();
                $('.gear-all-image.active').removeAttr('comment_uid');
            })
            //点击回复 -- 图片
            $('#GearImageCommentBox').on('click','.btn-huifu',(e)=>{
                var val = $(e.target).attr('user_name');
                getUserList().then((res)=>{
                    userList = res;
                    let userData = '';
                    let htmls = ''
                    for(let i = 0 ; i< userList.length;i++){
                        if(val.trim() == userList[i].username.trim()){
                            userData = userList[i];
                            break;
                        }
                    }
                    if(userData!=''){
                        htmls = '<span class="atwho-inserted" data-atwho-at-query="@" contenteditable="false">' +
                            '<div id="'+userData.id+'" username="'+userData.username+'" avatarurl="'+userData.avatar_url+'" color="'+userData.avatar_color+'" name="'+userData.username+'" email="'+userData.email+'" class="gear-user-box" href="javascript:;">'+userData.username+'</div>' +
                            '</span>&nbsp;'
                    }else{
                        htmls = val;
                    }
                    that.initTextCommenTextImage(htmls);
                })
            })
            //点击删除 -- 图片
            $('#GearImageCommentBox').on('click','.btn-sahnchu',(e)=>{

                let comment_id = $(e.target).attr('comment_id')
                let url = '/api/comments/'+comment_id;
                commonRequest('DELETE',url, {}, (res) => {
                    if(res.result){
                        if(window.pointState){
                            window.pointState.updatePoint = Math.random()
                        }
                        $(e.target).parent().parent().remove()

                        $('.gear-comment-box-img.active .comment-box-num span').html( Number($('.gear-all-image.active').attr('nums'))-1 );
                        $('.gear-all-image.active').attr('nums', Number($('.gear-all-image.active').attr('nums'))-1 );

                        if( $('.gear-all-image.active').attr('nums') <= 0 ){
                            $('.gear-comment-box-img.active').hide();
                            $('.gear-comment-box-img.active .cancel-btn').show();
                        }

                    }
                })
            })





            //点击下拉选择tag
            $('#GearCommentBox').on('click','.tag-box-div',(e)=>{
                $('.tag-box').toggleClass('selected');
            })
            //点击选择tag
            $('#GearCommentBox').on('click','.tag-item',(e)=>{
                $('.check-tag').attr('class','check-tag '+$(e.target).attr('flag'));
                $(e.target).addClass('active').siblings().removeClass('active');
                $('.tag-box').removeClass('selected');

                //文字富文本
                $('.annotation.active').attr('class','annotation active '+$(e.target).attr('flag'));
                //图片富文本
                $('.gear-all-image.active').attr('class','gear-all-image normal-image active '+$(e.target).attr('flag'));
            })



        }


        //文本评论 显示富文本中评论框
        showComments(top,bottom,left,right){
            $('#gear-comment-box .text-area').val('');
            $('#GearCommentBox').css({
                top: top,
                bottom: bottom,
                left: left,
                right: right,
            }).show();


            $('#GearCommentBox .comment-center-list').scrollTop($('#GearCommentBox .comment-center-list .comment-center-scroll').height())
        }
        //文本评论 根据评论列表详情 判断是否有评论列表 将评论列表添加到评论框中
        addListComments(res,isScroll=false){
            $('#GearCommentBox .tag-box').removeClass('selected');
            if(res.comments.length<=0){
                $('#GearCommentBox .comment-center-list').hide();
                $('#GearCommentBox .cancel-btn').show();
            }else{
                $('#GearCommentBox .comment-center-list').show();
                $('#GearCommentBox .cancel-btn').hide();
                let listDom = '';
                for(let item of res.comments){
                    var strs = item.content;
                    /*var activeStr = strs.match(/@(\S*) /g);
                    if(activeStr && activeStr.length>0){
                        for(var list of activeStr){
                            strs = strs.replace(list,"<a class='user'>"+list+"</a>");
                        }
                    }*/
                    listDom += `
                            <div class="item-list">
                                <div class="item-list-user">
                                    <img 
                                     src="${item.author.avatar_url}"
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
                $('#GearCommentBox .comment-center-list').html(divDom);

                if(isScroll){
                    $('#GearCommentBox .comment-center-list').scrollTop($('#GearCommentBox .comment-center-scroll').height())
                }
            }
        }

        //图片评论 根据评论列表详情 判断是否有评论列表 将评论列表添加到评论框中
        addListCommentsImage(res,isScroll=false){

            if(res.comments.length<=0){
                $('.gear-comment-box-img.active .comment-center-list').hide();
                this.initTextCommenTextImage('');
            }else{
                $('.gear-comment-box-img.active .comment-center-list').show();
                let listDom = '';
                for(let item of res.comments){
                    var strs = item.content;
                    /*var activeStr = strs.match(/@(\S*) /g);
                    if(activeStr && activeStr.length>0){
                        for(var list of activeStr){
                            strs = strs.replace(list,"<a class='user'>"+list+"</a>");
                        }
                    }*/
                    listDom += `
                            <div class="item-list">
                                <div class="item-list-user">
                                    <img 
                                    src="${item.author.avatar_url}"
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
                $('.gear-comment-box-img.active .comment-center-list').html(divDom);

                if(isScroll){
                    $('.gear-comment-box-img.active .comment-center-list').scrollTop($('.gear-comment-box-img.active .comment-center-scroll').height())
                }

                this.initTextCommenTextImage('');

            }
        }

        //初始化评论中的文本输入 -- 图片
        initTextCommenTextImage(val){
            var that = this;
            getUserList().then((res)=>{
                userList = res;

                var params = {
                    userList:userList,
                    placeholder:'请输入评论',
                    defValue:val,
                    //按回车键 -- 富文本
                    enterCallbick:function(){
                        let val = $('.gear-comment-box-img.active .gear-at-textarea').html();
                        if(val == ''){
                            return false;
                        }
                        let uid = $('.gear-comment-box-img.active').attr('comment_uid');

                        let url = '/api/reports/comment_points/'+uid;
                        let data = {
                            content :val,
                            page_title :document.title.trim(),
                            page_url :window.location.href,
                        }
                        commonRequest('POST',url, data, (res) => {
                            if(res.result){
                                if(window.pointState){
                                    window.pointState.updatePoint = Math.random()
                                }

                                that.addListCommentsImage(res.data,true);

                                $('.gear-comment-box-img.active .comment-box-num span').html(res.data.comments.length);
                                $('.gear-all-image.active').attr('nums',res.data.comments.length);

                                $('.gear-comment-box-img.active').show();
                                $('.gear-comment-box-img.active .cancel-btn').hide();

                            }
                        })
                    },
                }
                $('.gear-comment-box-img.active .gear-text-area').JqMention(params);


            })
        }


        //时间及金额预估 根据评论列表详情 判断是否有评论列表 将评论列表添加到评论框中  -- 没用了
        /*addListCommentsPlan(res,isScroll=false){
            alert(2)
            if(res.comments.length<=0){
                $('.gear-comment-box-plan.active .comment-box-num span').html(0);
                $('.gear-comment-box-plan.active .comment-center-list').hide();
            }else{
                $('.gear-comment-box-plan.active .comment-box-num span').html(res.comments.length);
                $('.gear-comment-box-plan.active .comment-center-list').show();
                let listDom = '';
                for(let item of res.comments){
                    var strs = item.content;
                    var activeStr = strs.match(/@(\S*) /g);
                    if(activeStr && activeStr.length>0){
                        for(var list of activeStr){
                            strs = strs.replace(list,"<a class='user'>"+list+"</a>");
                        }
                    }
                    listDom += `
                            <div class="item-list">
                                <div class="item-list-user">
                                    <img
                                    src="${item.author.avatar_url}"
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

                if(isScroll){
                    $('.gear-comment-box-plan.active .comment-center-list').scrollTop($('.gear-comment-box-plan.active .comment-center-scroll').height())
                }
            }
        }*/



        //点击评论的事件
        commentEventHanlder() {
            let that = this;

            let range = {};
            let text = '';
            let atSignBounds = '';

            //选中时对选中的评论
            if(that.quill.getSelection().length>0){
                range = that.quill.getSelection();
                text = that.quill.getText(range.index, range.length);
                atSignBounds = that.quill.getBounds(range.index+range.length);
            }else{
                //对当前行评论
                // 当前行开头索引与行的长度
                let index = that.quill.getSelection().index;
                let [line, offset] = that.quill.getLine(index);


                /*// 获取行首的index  获取行的长度
                let startIndex = quill.getIndex(line);
                let length = line.length()-1;*/

                let startIndex = index - offset;
                let length = line.cache.length - 1;
                //将这行选中
                that.quill.setSelection(startIndex,length);


                range = {
                    index: startIndex,
                    length: length
                };
                text = that.quill.getText(range.index, range.length);
                atSignBounds = that.quill.getBounds(range.index+range.length);
            }

            that.range = range;

            //获取uid
            that.getUid().then((res)=>{
                return that.getComments(res.uid); //根据uid获取评论列表
            }).then((res)=>{

                let editor_comment = {
                    class : 'annotation tag-select-yellow active',
                    comment_uid : res.uid,
                };
                that.quill.format('comment', editor_comment);


                //文字富文本添加颜色标示
                // $('.annotation.active').attr('class','annotation active tag-select-yellow');
                $('.check-tag').attr('class','check-tag tag-select-yellow');
                $('.tag-item.tag-select-yellow').addClass('active').siblings().removeClass('active');

                that.addListComments(res);
                that.showComments(
                    atSignBounds.top+atSignBounds.height+'px',
                    'auto',
                    atSignBounds.left+'px',
                    'auto'
                )

            })


        }


        //点击评论按钮时获取富文本UID
        getUid(){
            return new Promise((resolve, reject) => {
                let url = '/api/reports/'+PageData.reportData.uid+'/comment_points';
                commonRequest('POST',url, {}, (res) => {
                    if(res.result){
                        resolve(res.data)
                    }else{
                        reject('err')
                    }
                })

            });
        }

        //根据UID获取评论列表
        getComments(UID){
            return new Promise((resolve, reject) => {
                let url = '/api/reports/comment_points/'+UID;
                commonRequest('GET',url, {}, (res) => {
                    if(res.result){
                        resolve(res.data)
                    }else{
                        reject('err')
                    }
                })

            });
        }





    }

    Quill.register('modules/inline_comment', InlineComment);

})();

