
/****
 * 单图插入
 *
 *
quill.insertEmbed(
  0,
  'GearSingleImage',
  {
      src:'/static/new-report/img/report-time-icon@2x.png',
      id: '',
      uid: '',
      describe:'describe'
  }
);
*/

// data-tag-flag=gear-custom-module

(function () {
    const COMMENT_ATTRIBUTES = [
        'comment_uid',
        'nums',
    ];

    // 引入源码中的BlockEmbed
    const BlockEmbed = Quill.import('blots/block/embed');
    // 定义新的blot类型
    class GearSingleImage extends BlockEmbed {
        static create(options) {
            console.log(options);
            const node = super.create(options);
            node.setAttribute('class', 'gear-all-image gear-single-image');
            node.setAttribute('contenteditable', 'false');
            node.setAttribute('id', options.id);
            node.setAttribute('uid', options.uid);

            node.setAttribute('data-tag-flag', 'gear-custom-module');

            COMMENT_ATTRIBUTES.forEach(function (attribute) {
                if (options[attribute]) {
                    node.setAttribute(attribute, options[attribute]);
                }
            });

            let imgDom  =`
            <div class="img-box" data-tag-flag='gear-custom-module'>
                <img class="img-pic" data-tag-flag='gear-custom-module' src="${options.src}" alt="">
            </div>
            `;
            let desDom  =`
            <div class="img-describe" data-tag-flag='gear-custom-module'>${options.describe}</div>
            `;


            node.appendChild($(imgDom)[0])
            node.appendChild($(desDom)[0])
            return node;
        }


        // 返回节点自身的value值 用于撤销操作 与insertEmbed传递的参数一致
        static value(node) {
            let Dom = node
            let imgDom = node.querySelector('.img-pic')
            let desDom = node.querySelector('.img-describe')

            var values = {
                src: imgDom.getAttribute('src'),
                id: Dom.getAttribute('id'),
                uid: Dom.getAttribute('uid'),
                describe: desDom.innerHTML,
            };

            COMMENT_ATTRIBUTES.forEach(function (attribute) {
                if (Dom.hasAttribute(attribute)) {
                    values[attribute] = Dom.getAttribute(attribute)
                }
            });

            return values
        }
    }
    // blotName
    GearSingleImage.blotName = 'GearSingleImage';
    // class名将用于匹配blot名称
    // GearSingleImage.className = 'gear-single-image';
    // 标签类型自定义
    GearSingleImage.tagName = 'divImage';
    Quill.register(GearSingleImage, true);

})();


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



