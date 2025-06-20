// 配置数据示例
// var wxShareData = {
//         title: "",
//         desc:'',
//         imgUrl:'',
//         appId: '',
//         timestamp: '',
//         nonceStr: '',
//         signature: '',
//     };
$(document).on('ready', function () {
    wx.config({
        debug: false,
        appId: wxShareData.appId,
        timestamp: wxShareData.timestamp,
        nonceStr: wxShareData.nonceStr,
        signature: wxShareData.signature,
        jsApiList: ['onMenuShareTimeline', 'onMenuShareAppMessage', 'hideMenuItems', 'hideOptionMenu']
    });
});
wx.ready(function () {
    wx.hideMenuItems({menuList: ['menuItem:share:qq', 'menuItem:share:weiboApp', 'menuItem:favorite', 'menuItem:share:facebook', 'menuItem:share:QZone', 'menuItem:editTag', 'menuItem:delete', 'menuItem:copyUrl', 'menuItem:originPage', 'menuItem:readMode', 'menuItem:openWithQQBrowser', 'menuItem:openWithSafari', 'menuItem:share:email']});
    wx.onMenuShareAppMessage({
        title: wxShareData.title,
        desc: wxShareData.desc,
        link: location.href,
        imgUrl: wxShareData.imgUrl,
        type: '',
        dataUrl: '',
        success: function () {
        },
        cancel: function () {
        },
    });
    wx.onMenuShareTimeline({
        title: wxShareData.title,
        desc: wxShareData.desc,
        link: location.href,
        imgUrl: wxShareData.imgUrl,
        type: '',
        dataUrl: '',
        success: function () {
        },
        cancel: function () {
        },
    });
});