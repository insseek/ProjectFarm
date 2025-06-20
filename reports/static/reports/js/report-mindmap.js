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

$('.content-image-container .content-image-click').on('click', function (index, element) {
    var that = $(this);
    that.parent().find('img')[0].click()
});

// $('.content-image-click').hide();
//判断是否是手机端
if (!(/Android|webOS|iPhone|iPod|BlackBerry|IEMobile/i.test(navigator.userAgent))) {
    // $('.content-image-click').hide();

    /*$('.content-image-container, .mindmap-box').mouseenter(function () {
        var that = $(this);
        that.find('.content-image-click').show()
    });

    $('.content-image-container, .mindmap-box').mouseleave(function () {
        var that = $(this);
        that.find('.content-image-click').hide()
    });*/
} else {

    /*$('.content-image-container, .mindmap-box').on('touchstart', function () {
        var that = $(this);
        that.find('.content-image-click').show()
    });

    $('.content-image-container, .mindmap-box').on('touchend', function () {
        var that = $(this);
        setTimeout(function () {
            that.find('.content-image-click').hide()
        }, 8000)
    });*/
}


var activeSvgMap = '';

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