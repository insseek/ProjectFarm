$(function(){


    $('.mindmap-box').each(function (index, element) {
        var image_url = $(this).attr('data-image-url');
        var json_url = $(this).attr('data-file-url');
        var that = $(this);
        var img = $('<img alt="" class="mindmap-view mindmap-view-image print-image"  src="' + image_url + '">');
        img.attr("data-index", index);
        var contentImageClick = $('<span class="content-image-click"></span>');
        var contentImageLogo = '<span class="content-image-logo-text">此图由齿轮易创提供</span>';
        contentImageClick.attr("data-file-url", json_url);
        that.append(img);
        that.append(contentImageClick);
        that.append(contentImageLogo);
    });
    $('.mindmap-box').each(function (index, element) {
        var image_url = $(this).attr('data-image-url');
        var json_url = $(this).attr('data-file-url');
        var that = $(this);
        d3.json(json_url, function (error, data) {
            if (error) throw error;
            var svg = $("<svg class='mindmap-view print-hidden-image'></svg>");
            svg.attr("data-file-url", json_url);
            svg.attr("id", 'mindmap' + index);
            that.append(svg);
            markmap('svg#mindmap' + index, data, {
                preset: 'colorful', // or default
                linkShape: 'diagonal', // or bracket
                onlyView: true,
                showCircle: false
            });
        });
    });

    $('.content-image-container').each(function (index, element) {
        var that = $(this);
        var contentImageClick = $('<span class="content-image-click"></span>');
        var contentImageLogo = $('<span class="content-image-logo-text">此图由齿轮易创提供</span>');
        that.append(contentImageLogo);
        that.append(contentImageClick);
    });

    //设置图片宽高
    $('.content-image').each(function (index, element) {
        setImgWidth(element)
    });
    $('.gear-multiple-image .item-img').each(function (index, element) {
        setImgWidth(element)
    });
    $('.gear-single-image .img-pic').each(function (index, element) {
        setImgWidth(element)
    });

    var activeSvgMap = '';

    //脑图预览
    $('.mindmap-box').on('click', function () {
        var json_url = $(this).attr('data-file-url');
        $('#operationMindmap').empty();
        $('.modal-svg-div').show();
        $('body').addClass('modal-open');
        $('#modalSvgCenter').empty();
        $('#modalSvgCenter').append('<svg id="operation-mindmap" class="mindmap"></svg>')
        $('.modal-svg-num').find('span').html(100);
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
    });
    $('.modal-svg-close').click(function () {
        $('.modal-svg-div').hide();
        $('body').removeClass('modal-open');
    })
    $('.modal-svg-subtract').click(function () {
        calculate(1)
    })
    $('.modal-svg-add').click(function () {
        calculate(2)
    })

    function zoomFunction(val) {
        $('.modal-svg-num').find('span').html(Math.round(val * 100))
    }

    function calculate(flag) {
        var nums = Number($('.modal-svg-num').find('span').html());
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
        $('.modal-svg-num').find('span').html(activeNum)


        var svgDom = $('#operation-mindmap').children('g');
        var svgDomW = document.getElementById("operation-mindmap").firstChild.getBBox().width;
        var svgDomH = document.getElementById("operation-mindmap").firstChild.getBBox().height;

        var realNum = activeNum / 100;
        var realW = svgDomW * realNum;
        var realH = svgDomH * realNum;

        var x = (Number($('.modal-svg-center').width()) - realW) / 2;
        var y = Number($('.modal-svg-center').height()) / 2;
        activeSvgMap.updateZoom([x, y], realNum);
    }


    //图片预览
    /*$('.content-image-container').click(function(){
        let link = $(this).find('.content-image').attr('src');
        var pswpElement = document.querySelectorAll('.pswp')[0];

        getImageWidth(link,function(obj){
            var items = [
                {
                    src: link,
                    // title: '直接在这里我们计算图片的宽高即可直接在这里我们计算图片的宽高即可直接在这里我们计算图片的宽高即可直接在这里我们计算图片的宽高即可',
                    w: obj.width,
                    h: obj.height,
                },
            ];
            var options = {
                index: 0 // start at first slide
            };
            var gallery = new PhotoSwipe( pswpElement, PhotoSwipeUI_Default, items, options);
            gallery.init();
        })
    })*/

    var viewerOptions = {
        title: false, navbar: false, fullscreen: false, minZoomRatio: 0.2, maxZoomRatio: 10, scalable: false, toolbar: {
            zoomIn: 4,
            zoomOut: 4,
            oneToOne: 4,
            reset: 4,
            prev: 0,
            play: 0,
            next: 0,
            rotateLeft: 4,
            rotateRight: 4,
            flipHorizontal: 4,
            flipVertical: 4,
        }
    };


    $('.content-image').each(function (index, element) {
        var viewer = new Viewer(element, viewerOptions);
    });
    $('.content-image-container .content-image-click').on('click', function (index, element) {
        var that = $(this);
        that.parent().find('img')[0].click()
    });



    $('.gear-single-image .img-pic').each(function (index, element) {
        var viewer = new Viewer(element, viewerOptions);
    });
    $('.gear-single-image .img-box').on('click', function (index, element) {
        var that = $(this);
        that.parent().find('img')[0].click()
    });

    /*$('.gear-multiple-image .item-img').each(function (index, element) {
        var viewer = new Viewer(element, viewerOptions);
    });*/
    $('.gear-multiple-image').each(function (index, element) {
        var viewer = new Viewer(element, {
            url: 'src',
            title: false, navbar: false, fullscreen: false, minZoomRatio: 0.2, maxZoomRatio: 10, scalable: false, toolbar: {
                zoomIn: 4,
                zoomOut: 4,
                oneToOne: 4,
                reset: 4,
                prev: 1,
                play: 0,
                next: 1,
                rotateLeft: 4,
                rotateRight: 4,
                flipHorizontal: 4,
                flipVertical: 4,
            }
        });
    });
    $('.gear-multiple-image .more-pic-box').on('click', function (index, element) {
        var that = $(this);
        that.parent().find('img')[0].click()
    });



    function getImageWidth(url,callBack) {
        var img = new Image();
        img.src = url;
        let obj = {}
        // 如果图片被缓存，则直接返回缓存数据
        if (img.complete) {
            console.log(123);
            obj.width = img.width;
            obj.height = img.height;
            callBack(obj)
        } else {
            img.onload = function () {
                console.log(456);
                obj.width = img.width;
                obj.height = img.height;
                callBack(obj)
            }
        }
    }



})


//根据图片宽高设置样式
function setImgWidth(el){
    var img = new Image();
    img.src = $(el).attr('src');
    let obj = {}
    // 如果图片被缓存，则直接返回缓存数据
    if (img.complete) {
        let width = img.width;
        let height = img.height;
        if($(document).width() >= 900){
            if(width/height>1.78){
                $(el).css('width','100%')
            }else{
                $(el).css('height','386px')
            }
        }else{
            if(width/height>1){
                $(el).css('width','100%')
            }else{
                $(el).css('height','calc( 100vw - 40px - 40px)')
            }
        }

    } else {
        img.onload = function () {
            let width = img.width;
            let height = img.height;
            if($(document).width() >= 900){
                if(width/height>1.78){
                    $(el).css('width','100%')
                }else{
                    $(el).css('height','386px')
                }
            }else{
                if(width/height>1){
                    $(el).css('width','100%')
                }else{
                    $(el).css('height','calc( 100vw - 40px - 40px)')
                }
            }
        }
    }
}
