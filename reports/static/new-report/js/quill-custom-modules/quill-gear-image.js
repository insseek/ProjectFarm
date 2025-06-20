(function () {

    var activeSvgMap = '';


    QuillModule = Quill.import('core/module')

    class SelectWireframeImage extends QuillModule {
        constructor(quill) {
            super(quill);

            this.quill = quill;
            this.toolbar = quill.getModule('toolbar');

            this.imgFlag = null;  //wireframe 框架图 mindmap 思维导图  general 普通图片
            // this.quillIndex = null;
            this.quillIndex = {index: 0, length: 0};
            this.filter = [];
            this.imgFileUrl = null;

            this.init();
            this.initTipDom();
            this.initHandle();
            this.initShortcut();
            this.getTabData();
            this.getImgData();


            if (typeof this.toolbar != 'undefined') {
                this.toolbar.addHandler('wireframe-image-btn', this.frameImageHanlder.bind(this));
                this.toolbar.addHandler('mindmap-image-btn', this.mindMapImageHanlder.bind(this));
                this.toolbar.addHandler('image', this.generalImageHanlder.bind(this));
            }


        }

        //初始化
        init() {

            let frameDom = `    
            <div class="curent-modal frame-modal">
                <div class="curent-modal-bg"></div>
                <div class="curent-modal-box">
                    <div class="box-top">
                        <div class="box-top-tab active">选择标准框架图</div>
                        <div class="box-top-tab">上传框架图</div>
                        <div class="box-top-close">✕</div>
                    </div>
                    <div class="box-center">
                        <div class="tab-box change-box">
                            <div class="filter-box">
                                <div class="filter-label">筛选标签：</div>
                                <div class="filter-list">
                                
                                </div>
                            </div>
                            <div class="center-div">
                               
                            </div>
                        </div>
                        <div class="tab-box curt-box">
                            <div class="up-img-div up-img-box">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-farmeimg.svg"/>
                                </div>
                                <button class="btn-modal btn-primary btn-upimg-frame">自己上传框架图</button>
                            </div>
                            <div class="up-img-div up-img-loading">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-farmeimg.svg"/>
                                </div>
                                <div class="up-img-loading-item">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                            </div>
                            <div class="up-img-div up-img-err">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-farmeimg.svg"/>
                                </div>
                                <div class="err-text">未连接到网络</div>
                                <button class="btn-modal btn-primary btn-upimg-reset">重新上传</button>
                            </div>
                            <div class="up-img-div up-img-show">
                                <img src="/static/new-report/img/Illustration-farmeimg.svg"/>
                            </div>
                        </div>
                    </div>
                    <div class="box-bottom">
                        <button class="btn-modal btn-def btn-off">取消</button>
                        <button class="btn-modal btn-primary btn-comfim">确认</button>
                    </div>
                </div>
            
            </div>
            `;
            $('body').append(frameDom);

            let mindMapDom = `    
            <div class="curent-modal mind-map-modal">
                <div class="curent-modal-bg"></div>
                <div class="curent-modal-box">
                    <div class="box-top">
                        <div class="">插入思维导图</div>
                        <div class="box-top-close">✕</div>
                    </div>
                    <div class="box-center">
                        <div class="curt-box">
                            <div class="up-img-div up-img-box">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-mindmap.svg"/>
                                </div>
                                <div class="up-text-div">
                                    <p>1. 打开脑图制作软件（推荐MindNode）新建脑图，选择文件-导出至-opml </p>
                                    <p>2. 保存文件至电脑，点击上传思维导图按钮，选择该opml文件</p>
                                </div>
                                <button class="btn-modal btn-primary btn-upimg-mindmap">上传思维导图</button>
                            </div>
                            <div class="up-img-div up-img-loading">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-mindmap.svg"/>
                                </div>
                                <div class="up-img-loading-item">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                            </div>
                            <div class="up-img-div up-img-err">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-mindmap.svg"/>
                                </div>
                                <div class="err-text">未连接到网络</div>
                                <button class="btn-modal btn-primary btn-upimg-reset">重新上传</button>
                            </div>
                            <div class="up-img-div up-img-show">
                                <img src="/static/new-report/img/Illustration-mindmap.svg"/>
                            </div>
                        </div>
                    </div>
                    <div class="box-bottom">
                        <button class="btn-modal btn-def btn-off">取消</button>
                        <button class="btn-modal btn-primary btn-comfim">确认</button>
                    </div>
                </div>
            
            </div>
            `;
            $('body').append(mindMapDom);

            let generalDom = `    
            <div class="curent-modal general-modal">
                <div class="curent-modal-bg"></div>
                <div class="curent-modal-box">
                    <div class="box-top">
                        <div class="">插入图片</div>
                        <div class="box-top-close">✕</div>
                    </div>
                    <div class="box-center">
                        <div class="curt-box">
                            <div class="up-img-div up-img-box">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-image.svg"/>
                                </div>
                                <button class="btn-modal btn-primary btn-upimg-general">上传图片</button>
                            </div>
                            <div class="up-img-div up-img-loading">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-image.svg"/>
                                </div>
                                <div class="up-img-loading-item">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                            </div>
                            <div class="up-img-div up-img-err">
                                <div class="up-img-div-bg">
                                    <img src="/static/new-report/img/Illustration-image.svg"/>
                                </div>
                                <div class="err-text">未连接到网络</div>
                                <button class="btn-modal btn-primary btn-upimg-reset">重新上传</button>
                            </div>
                            <div class="up-img-div up-img-show">
                                <img src="/static/new-report/img/Illustration-image.svg"/>
                            </div>
                        </div>
                    </div>
                    <div class="box-bottom">
                        <button class="btn-modal btn-def btn-off">取消</button>
                        <button class="btn-modal btn-primary btn-comfim">确认</button>
                    </div>
                </div>
            
            </div>
            `;
            $('body').append(generalDom);

        }

        //插入框架图点击的tip
        initTipDom() {
            let tipDom = `
            <div class="img-tip clearfix">
                <div class="img-tip-type img-tip-type-frame">
                    <div class="img-tip-item tip-change-tem">
                        <div class="img-tip-icon">
                            <svg  width="20" height="20" fill="currentColor">
                                <path d="M11,6 L11,7 L9,5 L11,3 L11,4 L16,4 L16,6 L16,9 L17,9 L15,11 L13,9 L14,9 L14,6 L11,6 Z M9,14 L9,13 L11,15 L9,17 L9,16 L4,16 L4,14 L4,11 L3,11 L5,9 L7,11 L6,11 L6,14 L9,14 Z M4,8 L2,8 L2,2 L4,2 L6,2 L8,2 L8,8 L6,8 L4,8 Z M4,6 L6,6 L6,4 L4,4 L4,6 Z M14,18 L12,18 L12,12 L14,12 L16,12 L18,12 L18,18 L16,18 L14,18 Z M14,16 L16,16 L16,14 L14,14 L14,16 Z"/>
                            </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">更换模板</div>
                        </div>
                    </div>
                    <div class="img-tip-item tip-again-uploading">
                        <div class="img-tip-icon">
                             <svg width="20" height="20" fill="currentColor">
                                <path d="M10,19 C5.02943725,19 1,14.9705627 1,10 C1,5.02943725 5.02943725,1 10,1 C14.9705627,1 19,5.02943725 19,10 C19,14.9705627 14.9705627,19 10,19 Z M10,17 C13.8659932,17 17,13.8659932 17,10 C17,6.13400675 13.8659932,3 10,3 C6.13400675,3 3,6.13400675 3,10 C3,13.8659932 6.13400675,17 10,17 Z M11,10 L11,14 L9,14 L9,10 L6,10 L10,6 L14,10 L11,10 Z"/>
                             </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">重新上传</div>
                        </div>
                    </div>
                    <div class="img-tip-item tip-comment-inline">
                        <div class="img-tip-icon">
                            <svg width="20" height="20" fill="currentColor">
                                <path d="M4,4 L4,13 L6.625,13 L7.38539864,13 L10,15.3240901 L12.6146014,13 L16,13 L16,4 L4,4 Z M2,2 L18,2 L18,15 L13.375,15 L10,18 L6.625,15 L2,15 L2,2 Z M6,6 L14,6 L14,8 L6,8 L6,6 Z M6,9 L12,9 L12,11 L6,11 L6,9 Z"/>
                            </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">评论</div>
                        </div>
                    </div>
                </div>
                
                <div class="img-tip-type img-tip-type-mindmap">
                    <div class="img-tip-item tip-again-uploading">
                        <div class="img-tip-icon">
                            <svg width="20" height="20" fill="currentColor">
                                <path d="M10,19 C5.02943725,19 1,14.9705627 1,10 C1,5.02943725 5.02943725,1 10,1 C14.9705627,1 19,5.02943725 19,10 C19,14.9705627 14.9705627,19 10,19 Z M10,17 C13.8659932,17 17,13.8659932 17,10 C17,6.13400675 13.8659932,3 10,3 C6.13400675,3 3,6.13400675 3,10 C3,13.8659932 6.13400675,17 10,17 Z M11,10 L11,14 L9,14 L9,10 L6,10 L10,6 L14,10 L11,10 Z"/>
                            </svg>                       
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">重新上传</div>
                        </div>
                    </div>
                    <div class="img-tip-item tip-show-big">
                        <div class="img-tip-icon">
                            <svg width="20" height="20" fill="currentColor">
                                <path d="M5,13.5857864 L7.53553391,11.0502525 L8.94974747,12.4644661 L6.41421356,15 L9,15 L9,17 L3,17 L3,11 L5,11 L5,13.5857864 Z M15,6.41421356 L12.4644661,8.94974747 L11.0502525,7.53553391 L13.5857864,5 L11,5 L11,3 L17,3 L17,9 L15,9 L15,6.41421356 Z"/>
                            </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">展开</div>
                        </div>
                    </div>
                    <div class="img-tip-item tip-comment-inline">
                        <div class="img-tip-icon">
                            <svg width="20" height="20" fill="currentColor">
                                <path d="M4,4 L4,13 L6.625,13 L7.38539864,13 L10,15.3240901 L12.6146014,13 L16,13 L16,4 L4,4 Z M2,2 L18,2 L18,15 L13.375,15 L10,18 L6.625,15 L2,15 L2,2 Z M6,6 L14,6 L14,8 L6,8 L6,6 Z M6,9 L12,9 L12,11 L6,11 L6,9 Z"/>
                            </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">评论</div>
                        </div>
                    </div>
                    <div class="img-tip-item tip-file-down">
                        <div class="img-tip-icon">
                            <svg width="18px" height="18px" fill="currentColor">
                                <g fill-rule="evenodd" fill="none" transform="translate(1,0)">
                                    <polyline fill-rule="nonzero" stroke="currentColor" stroke-width="2" points="12.2619948 7.3144368 14 7.3144368 14 15.3144368 0 15.3144368 0 7.3144368 0 7.3144368 1.77091193 7.3144368"></polyline>
                                    <path d="M6.99565857,10.6130364 L10.1445539,7.35361958 L10.1172352,7.32515355 C10.1693058,7.17687276 10.1406853,7.00409923 10.0248466,6.88488139 C9.91030964,6.76571952 9.74307872,6.73527615 9.59920624,6.79021224 L9.57192417,6.76107467 L7.99464398,6.76107467 L7.99464398,-1.42108547e-14 L5.99464398,-1.42108547e-14 L5.99464398,6.76107467 L4.41935629,6.76107467 L4.39141418,6.79021224 C4.24754168,6.73529482 4.0809708,6.76573816 3.96582882,6.88488139 C3.85061348,7.00409923 3.82135127,7.17685411 3.87406357,7.32515355 L3.8460848,7.35361958 L6.99565857,10.6130364 Z" fill-rule="nonzero" fill="currentColor"></path>
                                    <rect fill="currentColor" y="0.989843365" width="2" height="7" x="5.99464398" id="矩形"></rect>
                                </g>
                            </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">下载</div>
                        </div>
                    </div>
                </div>
                
                <div class="img-tip-type img-tip-type-img">
                    <div class="img-tip-item tip-again-uploading">
                        <div class="img-tip-icon">
                            <svg width="20" height="20" fill="currentColor">
                                <path d="M10,19 C5.02943725,19 1,14.9705627 1,10 C1,5.02943725 5.02943725,1 10,1 C14.9705627,1 19,5.02943725 19,10 C19,14.9705627 14.9705627,19 10,19 Z M10,17 C13.8659932,17 17,13.8659932 17,10 C17,6.13400675 13.8659932,3 10,3 C6.13400675,3 3,6.13400675 3,10 C3,13.8659932 6.13400675,17 10,17 Z M11,10 L11,14 L9,14 L9,10 L6,10 L10,6 L14,10 L11,10 Z"/>
                            </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">重新上传</div>
                        </div>
                    </div>
                    <div class="img-tip-item tip-comment-inline">
                        <div class="img-tip-icon">
                            <svg width="20" height="20" fill="currentColor">
                                <path d="M4,4 L4,13 L6.625,13 L7.38539864,13 L10,15.3240901 L12.6146014,13 L16,13 L16,4 L4,4 Z M2,2 L18,2 L18,15 L13.375,15 L10,18 L6.625,15 L2,15 L2,2 Z M6,6 L14,6 L14,8 L6,8 L6,6 Z M6,9 L12,9 L12,11 L6,11 L6,9 Z"/>
                            </svg>
                        </div>
                        <div class="img-tip-text">
                            <div class="tip-box-triangle"></div>
                            <div class="img-tip-text-div">评论</div>
                        </div>
                    </div>
                </div>
                
                <div class="img-tip-item tip-del-inline">
                    <div class="img-tip-icon">
                        <svg width="20" height="20" fill="currentColor">
                            <path d="M14,6 L6,6 L6,16 L14,16 L14,6 Z M16,6 L16,16 L16,18 L4,18 L4,16 L4,6 L2,6 L2,4 L18,4 L18,6 L16,6 Z M8,8 L9,8 L9,14 L8,14 L8,8 Z M11,8 L12,8 L12,14 L11,14 L11,8 Z M7,1 L13,1 L13,3 L7,3 L7,1 Z"/>
                        </svg>
                    </div>
                    <div class="img-tip-text">
                        <div class="tip-box-triangle"></div>
                        <div class="img-tip-text-div">删除</div>
                    </div>
                </div>
            </div>
            `
            this.quill.addContainer($(tipDom)[0]);
        }

        //初始化输入@的快捷选择
        initShortcut() {
            let shortcutDom = `
            <div class="shortcut-div-modal">
                <div class="shortcut-div-list active" btn-class="ql-wireframe-image-btn">
                    <svg width="20" height="20" fill="currentColor">
                        <path d="M15,15 L15,9 L9,9 L9,15 L15,15 Z M17,15 L17,17 L3,17 L3,15 L3,5 L3,3 L17,3 L17,5 L17,15 Z M15,5 L5,5 L5,7 L15,7 L15,5 Z M7,15 L7,9 L5,9 L5,15 L7,15 Z"></path>
                    </svg>
                    <span class="shortcut-list-text">项目框架图</span>
                </div>
                <div class="shortcut-div-list" btn-class="ql-mindmap-image-btn">
                    <svg width="20" height="20" fill="currentColor">
                        <path d="M10,5 L10,4 L8,4 L8,5 L10,5 Z M12,4 L12,7 L10,7 L10,9 L8,9 L8,7 L6,7 L6,4 L6,2 L12,2 L12,4 Z M15,15 L13,15 L13,16 L15,16 L15,15 Z M15,13 L17,13 L17,16 L17,18 L11,18 L11,16 L11,13 L13,13 L13,11 L15,11 L15,13 Z M3,11 L3,9 L15,9 L15,11 L5,11 L5,13 L7,13 L7,16 L7,18 L1,18 L1,16 L1,13 L3,13 L3,11 Z M5,16 L5,15 L3,15 L3,16 L5,16 Z"></path>
                    </svg>
                    <span class="shortcut-list-text">思维导图</span>
                </div>
                <div class="shortcut-div-list" btn-class="ql-image">
                    <svg width="20" height="20" fill="currentColor">
                        <path d="M3,12.4852814 L7.36396103,8.12132034 L8.77817459,9.53553391 L10.8994949,11.6568542 L13.0208153,9.53553391 L13.7279221,10.2426407 L16,12.5147186 L16,4 L3,4 L3,12.4852814 Z M3.3137085,15 L15.6568542,15 L13.0208153,12.363961 L12.3137085,13.0710678 L10.8994949,14.4852814 L7.36396103,10.9497475 L3.3137085,15 Z M2,2 L17,2 C17.5522847,2 18,2.44771525 18,3 L18,16 C18,16.5522847 17.5522847,17 17,17 L2,17 C1.44771525,17 1,16.5522847 1,16 L1,3 C1,2.44771525 1.44771525,2 2,2 Z M13.5,8 C12.6715729,8 12,7.32842712 12,6.5 C12,5.67157288 12.6715729,5 13.5,5 C14.3284271,5 15,5.67157288 15,6.5 C15,7.32842712 14.3284271,8 13.5,8 Z"></path>
                    </svg>
                    <span class="shortcut-list-text">图片</span>
                </div>
            </div>
            `
            this.quill.addContainer($(shortcutDom)[0]);


        }

        //初始化方法绑定
        initHandle() {
            //quill的change事bl件
            var that = this;
            var onblurIndex = null;
            this.quill.on('selection-change', function (range, oldRange, source) {
                //离开焦点
                if (!range) {
                    $('#toolbar').addClass('disabled');

                    $('.shortcut-div-modal').removeClass('show-shortcut')
                } else {
                    onblurIndex = range.index;

                    //有焦点
                    $('#toolbar').removeClass('disabled');
                    //输入@时
                    if (that.quill.getText(range.index - 1, 1).trim() == '@') {
                        var boundInfo = that.quill.getBounds(range.index - 1);
                        $('.shortcut-div-modal').css({
                            top: boundInfo.top + boundInfo.height + 'px',
                            left: boundInfo.left + 'px',
                        })
                        $('.shortcut-div-modal').addClass('show-shortcut');
                        $('.shortcut-div-list').eq(0).addClass('active').siblings().removeClass('active');

                    } else {
                        $('.shortcut-div-modal').removeClass('show-shortcut');
                    }
                }
            });

            //输入@快捷键的事件
            $('#main-sections').keydown(function (event) {
                if (event.keyCode == 38 || event.keyCode == 40) {
                    if ($('.shortcut-div-modal').hasClass('show-shortcut')) {
                        let indexNum = $('.shortcut-div-list.active').index();

                        let indexActive = null;
                        if (event.keyCode == 38) {
                            if (indexNum == 0) {
                                indexActive = 2;
                            } else {
                                indexActive = indexNum - 1;
                            }
                        } else {
                            if (indexNum == 2) {
                                indexActive = 0;
                            } else {
                                indexActive = indexNum + 1;
                            }
                        }

                        $('.shortcut-div-list').eq(indexActive).addClass('active').siblings().removeClass('active');
                        return false;
                    } else {

                    }
                }
                if (event.keyCode == 13) {
                    if ($('.shortcut-div-modal').hasClass('show-shortcut')) {
                        let className = $('.shortcut-div-list.active').attr('btn-class');
                        let index = that.quill.getSelection().index - 2;
                        that.quill.deleteText(index, 2);
                        $('.' + className).click();

                        event.cancelBubble = true;
                        event.preventDefault();
                        event.stopPropagation();
                        return false;
                    }
                }
            });
            //输入@快捷键的点击事件
            $('#main-sections').on('click', '.shortcut-div-list', function () {
                let className = $(this).attr('btn-class');
                that.quill.deleteText(onblurIndex - 1, 1);
                that.quill.setSelection(onblurIndex - 1, 0);
                $('.' + className).click();
            })


            //关闭弹框
            $('.curent-modal-bg,.btn-off,.box-top-close').click(() => {
                if (
                    !$('.mind-map-modal').is(":hidden") &&
                    !$('.mind-map-modal .up-img-loading').is(":hidden")
                ) {
                    farmAlter('文件正在上传中，请稍后', 3000)

                } else {

                    $('.curent-modal').hide();
                    $('.mind-map-modal .box-bottom').hide();
                    $('body').removeClass('modal-open');

                    that.quill.focus();
                }


            })


            //点击确认
            $('.btn-comfim').click(() => {
                if (this.imgFlag == 'mindmap') {
                    if ($('.gear-all-image.active').length > 0) {
                        $('.gear-all-image.active').attr('src', $('.mind-map-modal .up-img-show img').attr('src'));

                        $('.gear-all-image.active').attr('json_url', $('.mind-map-modal .up-img-show img').attr('json_url'));
                        $('.gear-all-image.active').attr('file_url', $('.mind-map-modal .up-img-show img').attr('file_url'));
                        $('.gear-all-image.active').attr('filename', $('.mind-map-modal .up-img-show img').attr('filename'));


                    } else {
                        this.quill.insertEmbed(this.quillIndex.index, 'gear-image', {
                            src: $('.mind-map-modal .up-img-show img').attr('src'),
                            class: 'gear-all-image',
                            json_url: $('.mind-map-modal .up-img-show img').attr('json_url'),
                            file_url: $('.mind-map-modal .up-img-show img').attr('file_url'),
                            filename: $('.mind-map-modal .up-img-show img').attr('filename'),
                            flag: this.imgFlag,
                        });
                    }
                    $('.curent-modal').hide();
                    $('body').removeClass('modal-open');
                    $('.mind-map-modal .up-img-box').show().siblings().hide();

                    var top = $('.report-container').scrollTop();
                    var index = that.quillIndex.index + 2;
                    that.quill.setSelection(index);
                    that.quill.focus();
                    $('.report-container').scrollTop(top);
                }
                if (this.imgFlag == 'general') {
                }

            })

            //tab切换
            $('.frame-modal .box-top-tab').click((e) => {
                let index = $(e.target).index();
                $(e.target).addClass('active').siblings().removeClass('active');
                $('.frame-modal .tab-box').eq(index).show().siblings().hide()
            })

            //选择过滤
            $('.filter-list').on('click', '.filter-item', (e) => {

                let val = $(e.target).attr('flag');
                if (val == '不限') {
                    this.filter = [];
                } else {
                    if (this.filter.indexOf(val) >= 0) {
                        for (let i = 0; i < this.filter.length; i++) {
                            if (this.filter[i] == val || this.filter[i] == 1) {
                                this.filter.splice(i, 1);
                            }
                        }
                    } else {
                        this.filter.push(val);
                    }
                }

                if (this.filter.length <= 0) {
                    $('.filter-item').removeClass('active');
                    $('.filter-item').eq(0).addClass('active');
                } else {
                    $('.filter-item').map((index, item) => {
                        if (this.filter.indexOf($(item).attr('flag')) >= 0) {
                            $(item).addClass('active');
                        } else {
                            $(item).removeClass('active');
                        }
                    })
                }
                this.getImgData();

            })

            //选择框架图
            $('.center-div').on('click', '.center-div-item img', (e) => {
                if ($('.gear-all-image.active').length > 0) {
                    $('.gear-all-image.active').attr('src', $(e.target).attr('src'));
                } else {
                    this.quill.insertEmbed(this.quillIndex.index, 'gear-image', {
                        src: $(e.target).attr('src'),
                        class: 'gear-all-image',
                        flag: this.imgFlag,
                    });
                }
                $('.curent-modal').hide();
                $('body').removeClass('modal-open');

                var top = $('.report-container').scrollTop();
                var index = this.quillIndex.index + 2;
                this.quill.setSelection(index);
                this.quill.focus();
                $('.report-container').scrollTop(top);
            })

            // 自己上传框架图按钮
            // 上传思维导图
            // 普通上传
            // 三个重新上传按钮
            $('.btn-upimg-frame,.btn-upimg-mindmap,.btn-upimg-general,.btn-upimg-reset').click(() => {
                const input = document.createElement('input');
                input.setAttribute('type', 'file');

                if (this.imgFlag == 'mindmap') {
                    input.setAttribute('accept', ".opml");
                } else {
                    input.setAttribute('accept', "image/*");
                }


                input.click();
                input.onchange = () => {

                    const file = input.files[0];
                    let formData = new FormData();
                    formData.append('file', file);


                    if (this.imgFlag == 'wireframe') {
                        let url = "/api/reports/frame_diagrams/upload";
                        this.updateFrameImg(url, formData);
                    } else if (this.imgFlag == 'mindmap') {
                        let url = "/api/reports/mind_maps/upload";
                        this.updateMindmapImg(url, formData);
                    } else {
                        let url = "/api/reports/files/upload";
                        this.updateGeneralImg(url, formData);
                    }


                };
            })


            //插入后的图点击
            $('#main-sections').on('click', '.gear-all-image', (e) => {
                this.imgFlag = $(e.target).attr('flag');

                this.quill.blur();

                $('.img-tip').show();
                if ($(e.target).attr('flag') == 'wireframe') {
                    $('.img-tip-type.img-tip-type-frame').show().siblings('.img-tip-type').hide();
                } else if ($(e.target).attr('flag') == 'mindmap') {
                    $('.img-tip-type.img-tip-type-mindmap').show().siblings('.img-tip-type').hide();
                } else {
                    $('.img-tip-type.img-tip-type-img').show().siblings('.img-tip-type').hide();
                }

                $('.gear-all-image').removeClass('active')
                $(e.target).addClass('active')

                let topNum = $(e.target).offset().top - document.documentElement.scrollTop;
                let leftNum = $(e.target).offset().left + $(e.target).width() / 2;
                let parentTopNum = $(e.target).position().top;
                let parentLeftNum = $(e.target).position().left;

                //tip位置
                if (topNum <= (94)) {
                    $('.img-tip').css({
                        position: 'fixed',
                        top: '94px',
                        // left: (leftNum - $('.img-tip').width() / 2) + 'px',
                    })
                } else {
                    $('.img-tip').css({
                        position: 'absolute',
                        top: parentTopNum - (36 + 8) + 'px',
                        // left: (parentLeftNum + $(e.target).width() / 2 - $('.img-tip').width() / 2) + 'px',
                    })
                }
                var imageBlot = Quill.find(e.target)
                that.quillIndex = {
                    index: that.quill.getIndex(imageBlot) + 1,
                    length: 0
                }

                var top = $('.report-container').scrollTop();
                var imageBlot = Quill.find(e.target)
                var index = that.quill.getIndex(imageBlot) + 1;
                that.quill.setSelection(index);
                that.quill.focus();
                $('.report-container').scrollTop(top);
            })

            //更换模板 -- 框架图
            $('#main-sections').on('click', '.img-tip-type-frame .tip-change-tem', function (e) {
                var imageBlot = Quill.find($('.gear-all-image.active')[0])
                var index = that.quill.getIndex(imageBlot);
                that.quillIndex = {
                    index: index - 1 >= 0 ? index : 0,
                    length: 0
                }

                $('.frame-modal').show();
                $('body').addClass('modal-open');

                $('.frame-modal .up-img-box').show().siblings().hide();

                $('.frame-modal .box-top-tab').eq(0).addClass('active').siblings().removeClass('active');
                $('.frame-modal .tab-box').eq(0).show().siblings().hide();

                this.filter = [];
                $('.filter-item').removeClass('active');
                $('.filter-item').eq(0).addClass('active');

            })
            //重新上传 -- 框架图
            $('#main-sections').on('click', '.img-tip-type-frame .tip-again-uploading', function (e) {
                var imageBlot = Quill.find($('.gear-all-image.active')[0])
                var index = that.quill.getIndex(imageBlot);
                that.quillIndex = {
                    index: index - 1 >= 0 ? index : 0,
                    length: 0
                }

                $('.frame-modal').show();
                $('body').addClass('modal-open');

                $('.frame-modal .up-img-box').show().siblings().hide();

                $('.frame-modal .box-top-tab').eq(1).addClass('active').siblings().removeClass('active');
                $('.frame-modal .tab-box').eq(1).show().siblings().hide();

                this.filter = [];
                $('.filter-item').removeClass('active');
                $('.filter-item').eq(0).addClass('active');

            })

            //重新上传 -- 思维导图
            $('#main-sections').on('click', '.img-tip-type-mindmap .tip-again-uploading', function (e) {
                var imageBlot = Quill.find($('.gear-all-image.active')[0])
                var index = that.quill.getIndex(imageBlot);
                that.quillIndex = {
                    index: index - 1 >= 0 ? index : 0,
                    length: 0
                }

                $('.mind-map-modal').show();
                $('body').addClass('modal-open');

                $('.mind-map-modal .up-img-box').show().siblings().hide();
                $('.mind-map-modal .box-bottom').hide();

            })
            //大图查看 -- 思维导图
            $('#main-sections').on('click', '.img-tip-type-mindmap .tip-show-big', function (e) {

                $('#MindMapComment').show();
                $('body').addClass('modal-open');

                $('.mind-map-svg-center').empty();
                $('.mind-map-svg-center').html('<svg id="operation-mindmap" class="mindmap"></svg>');

                $('.svg-size-num').html('100%');

                var json_url = $('.gear-all-image.active').attr('json_url');
                d3.json(json_url, function (error, data) {
                    if (error) throw error;
                    activeSvgMap = markmap('svg#operation-mindmap', data, {
                        preset: 'colorful', // or default
                        linkShape: 'diagonal', // or bracket
                        onlyView: false,
                        showCircle: true,
                        zoomScale: [0.2, 5],
                        zoomFunction: zoomFunction, //放大缩小回调 zoomFunction(val)
                    });
                });

            })
            //文件下载 -- 思维导图
            $('#main-sections').on('click', '.img-tip-type-mindmap .tip-file-down', function (e) {
                var file_url = $('.gear-all-image.active').attr('file_url');
                if (!file_url) {
                    var json_url = $('.gear-all-image.active').attr('json_url');
                    if (json_url) {
                        file_url = json_url.replace('.json', '.opml')
                    }
                }
                if (file_url) {
                    var filename = $('.gear-all-image.active').attr('filename');
                    if (!filename | filename == 'undefined') {
                        filename = "脑图.opml"
                    }
                    const aTag = document.createElement('a');
                    aTag.setAttribute('href', file_url);
                    aTag.setAttribute('download', filename);
                    aTag.click();
                }
            })

            //重新上传 -- 普通图片
            $('#main-sections').on('click', '.img-tip-type-img .tip-again-uploading', function (e) {
                var imageBlot = Quill.find($('.gear-all-image.active')[0])
                var index = that.quill.getIndex(imageBlot);
                that.quillIndex = {
                    index: index - 1 >= 0 ? index : 0,
                    length: 0
                }

                $('.general-modal').show();
                $('body').addClass('modal-open');

                $('.general-modal .up-img-box').show().siblings().hide();

            })


            //删除
            $('#main-sections').on('click', '.tip-del-inline', (e) => {
                let line = Quill.find($('.gear-all-image.active')[0])
                let index = this.quill.getIndex(line);
                this.quill.deleteText(index, 1);
                let scrollTop = $('.report-container').scrollTop();
                this.quill.focus();
                this.quill.update();
                $('.report-container').scrollTop(scrollTop);

                //对应的图片评论
                $('#main-sections .gear-all-image').each(function () {
                    let className = 'img-' + $(this).attr('comment_uid');
                    $('.' + className).css({
                        top: $(this).position().top + 'px',
                    });
                });

                // $('.gear-all-image.active').remove();
                $('.img-tip').hide();
            })


            //滚动时
            $('.report-container').scroll(function () {
                if ($('.gear-all-image.active').length > 0) {
                    let topNum = $('.gear-all-image.active').offset().top - document.documentElement.scrollTop;
                    let leftNum = $('.gear-all-image.active').offset().left + $('.gear-all-image.active').width() / 2;

                    let parentTopNum = $('.gear-all-image.active').position().top;
                    let parentLeftNum = $('.gear-all-image.active').position().left;

                    if (topNum < (94)) {
                        $('.img-tip').css({
                            position: 'fixed',
                            top: '94px',
                            // left: (leftNum - $('.img-tip').width() / 2) + 'px',
                        })
                    } else {
                        $('.img-tip').css({
                            position: 'absolute',
                            top: parentTopNum - (36 + 8) + 'px',
                            // left: (parentLeftNum + $('.gear-all-image.active').width() / 2 - $('.img-tip').width() / 2) + 'px',
                        })
                    }
                }

            })
            //点击指定元素外
            $(document).bind('click', (e) => {
                var event = e || window.event; //浏览器兼容性
                var elem = event.target || event.srcElement;

                while (elem && elem !== '') { //循环判断至跟节点，防止点击的是div子元素
                    if (
                        (
                            elem.id &&
                            elem.id == 'GearCommentBox'
                        )
                        ||
                        (
                            elem.id &&
                            elem.id == 'MindMapComment'
                        )
                        ||
                        (
                            elem.className &&
                            typeof (elem.className) == 'string' &&
                            elem.className.indexOf('gear-all-image') >= 0 &&
                            elem.className.indexOf('active') >= 0
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
                            elem.className.indexOf('curent-modal') >= 0
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
                $('.img-tip').hide();
                $('.gear-all-image.active').removeClass('active')
            });

            // ESC按键
            $(document).keyup(function (e) {
                var key = e.which || e.keyCode;
                if (key == 27) {
                    if (!$('.frame-modal').is(":hidden") ||
                        !$('.mind-map-modal').is(":hidden") ||
                        !$('.general-modal').is(":hidden")
                    ) {
                        if (
                            !$('.mind-map-modal').is(":hidden") &&
                            !$('.mind-map-modal .up-img-loading').is(":hidden")
                        ) {
                            farmAlter('文件正在上传中，请稍后', 3000)

                        } else {

                            $('.curent-modal').hide();
                            $('.mind-map-modal .box-bottom').hide();
                            $('body').removeClass('modal-open');

                            that.quill.focus();
                        }
                    } else if (
                        $('.gear-all-image.active').length > 0 ||
                        $('.estimate-box.checked').length > 0 ||
                        $('.annotation.active').length > 0
                    ) {
                        $('body').click();
                    }


                }
            });

        }


        //获取tab列表
        getTabData() {

            let url = '/api/reports/frame_diagrams/filter_data';
            commonRequest('get', url, '', (res) => {
                let data = [
                    {
                        id: '',
                        name: '不限'
                    },
                    ...res.data.tags
                ];

                let tabDom = data.map((item, index) => {
                    return (
                        `
                        <div flag="${item.name}" class="filter-item">${item.name}</div>
                        `
                    )
                })
                $('.filter-list').html(tabDom);
                $('.filter-item').eq(0).addClass('active');
                this.filter = [];
            })

        }

        //获取框架图列表
        getImgData() {
            let tgas = '&tags=' + this.filter.join();
            let url = '/api/reports/frame_diagrams?is_standard=true' + tgas;

            commonRequest('get', url, '', (res) => {
                let data = res.data;
                let tabDom = data.map((item, index) => {
                    return (
                        `
                        <div class="center-div-item">
                            <img src="${item.file_url}" alt="">
                        </div>
                        `
                    )
                })
                $('.frame-modal .center-div').html(tabDom)

            })

        }

        //框架图上传
        updateFrameImg(url, formData) {
            let that = this;

            $('.frame-modal .up-img-loading').show().siblings().hide();
            commonUploadFile(url, formData, (res) => {
                if (res.result) {

                    if ($('.gear-all-image.active').length > 0) {
                        $('.gear-all-image.active').attr('src', res.data.file_url);
                    } else {
                        this.quill.insertEmbed(this.quillIndex.index, 'gear-image', {
                            src: res.data.file_url,
                            class: 'gear-all-image',
                            flag: this.imgFlag,
                        });
                    }
                    $('.curent-modal').hide();
                    $('body').removeClass('modal-open');
                    $('.frame-modal .up-img-box').show().siblings().hide();

                    var top = $('.report-container').scrollTop();
                    var index = that.quillIndex.index + 2;
                    that.quill.setSelection(index);
                    that.quill.focus();
                    $('.report-container').scrollTop(top);
                } else {
                    $('.frame-modal .up-img-err').show().siblings().hide();
                    $('.frame-modal .err-text').html(res);

                    that.quill.focus();
                }
            })
        }

        //思维导图上传
        updateMindmapImg(url, formData) {
            let that = this;
            $('.mind-map-modal .up-img-loading').show().siblings().hide();
            commonUploadFile(url, formData, (res) => {
                if (res.result) {

                    let imgDom = "<img json_url='" + res.data.json_url + "' filename='" + res.data.filename + "' file_url='" + res.data.file_url + "' src='" + res.data.image_url + "' alt=''>";
                    $('.mind-map-modal .up-img-show').html(imgDom);
                    $('.mind-map-modal .up-img-show').show().siblings().hide();
                    $('.mind-map-modal .box-bottom').show();
                } else {
                    $('.mind-map-modal .up-img-err').show().siblings().hide();
                    $('.mind-map-modal .err-text').html(res);
                    $('.mind-map-modal .box-bottom').hide();
                }
            })
        }

        //普通图上传
        updateGeneralImg(url, formData) {
            let that = this;
            $('.general-modal .up-img-loading').show().siblings().hide();
            commonUploadFile(url, formData, (res) => {
                if (res.result) {

                    if ($('.gear-all-image.active').length > 0) {
                        $('.gear-all-image.active').attr('src', res.data.file_url);
                    } else {
                        this.quill.insertEmbed(this.quillIndex.index, 'gear-image', {
                            src: res.data.file_url,
                            class: 'gear-all-image',
                            flag: this.imgFlag,
                        });
                    }
                    $('.curent-modal').hide();
                    $('body').removeClass('modal-open');
                    $('.general-modal .up-img-box').show().siblings().hide();

                    var top = $('.report-container').scrollTop();
                    var index = that.quillIndex.index + 2;
                    that.quill.setSelection(index);
                    that.quill.focus();
                    $('.report-container').scrollTop(top);
                } else {
                    $('.general-modal .up-img-err').show().siblings().hide();
                    $('.general-modal .err-text').html(res);
                    that.quill.focus();
                }
            })
        }

        //点击插入框架图的处理函数
        frameImageHanlder() {
            this.imgFlag = 'wireframe';
            this.quillIndex = this.quill.getSelection();
            $('.frame-modal').show();
            $('body').addClass('modal-open');

            $('.frame-modal .up-img-box').show().siblings().hide();

            $('.frame-modal .box-top-tab').eq(0).addClass('active').siblings().removeClass('active');
            $('.frame-modal .tab-box').eq(0).show().siblings().hide();

            this.filter = [];
            $('.filter-item').removeClass('active');
            $('.filter-item').eq(0).addClass('active');
        }

        //点击插入思维导图的处理函数
        mindMapImageHanlder() {
            this.imgFlag = 'mindmap';
            this.quillIndex = this.quill.getSelection();
            $('.mind-map-modal').show();
            $('body').addClass('modal-open');

            $('.mind-map-modal .up-img-box').show().siblings().hide();

        }

        //普通上传图片
        generalImageHanlder() {
            this.imgFlag = 'general';
            this.quillIndex = this.quill.getSelection();
            $('.general-modal').show();
            $('body').addClass('modal-open');

            $('.general-modal .up-img-box').show().siblings().hide();

        }


    }

    Quill.register('modules/gear_images', SelectWireframeImage);


    // 思维导图弹框中按钮
    $('#NewReports').on('click', '.svg-close', function () {
        $('#MindMapComment').hide();
        $('body').removeClass('modal-open')
    })

    $('#NewReports').on('click', '.fold-btn', function () {
        $('.mind-map-preview-comment').toggleClass('is-fold');
    })

    $('#NewReports').on('click', '.modal-svg-subtract', function () {
        calculate(1)
    })
    $('#NewReports').on('click', '.modal-svg-add', function () {
        calculate(2)
    })

    function zoomFunction(val) {
        $('.svg-size-num').html(Math.round(val * 100) + '%')
    }

    function calculate(flag) {
        var nums = Number($('.svg-size-num').html().replace('%', ''));
        var minNum = 20;
        var maxNum = 500;
        var changeNum = 20;

        var activeNum = 20;
        //1减 2加
        if (flag == 1) {
            while (activeNum < nums - changeNum) {
                activeNum += changeNum;
            }
        } else {
            while (activeNum <= nums && activeNum < maxNum) {
                activeNum += changeNum;
            }
        }
        $('.svg-size-num').html(activeNum + '%')


        var svgDom = $('#operation-mindmap').children('g');
        var svgDomW = document.getElementById("operation-mindmap").firstChild.getBBox().width;
        var svgDomH = document.getElementById("operation-mindmap").firstChild.getBBox().height;

        var realNum = activeNum / 100;
        var realW = svgDomW * realNum;
        var realH = svgDomH * realNum;

        var x = (Number($('.mind-map-svg-center').width()) - realW) / 2;
        var y = Number($('.mind-map-svg-center').height()) / 2;

        // console.log(x,y)
        activeSvgMap.updateZoom([x, y], realNum);
    }

})();



