
/****
 * 多图插入
 *
 *
 this.quill.insertEmbed(this.quillIndex.index, 'GearMultipleImage', {
    data: [
        {
            src: this.siginImage.file_url,
            id: this.siginImage.id,
            uid: this.siginImage.uid,
        },
        {
            src: this.siginImage.file_url,
            id: this.siginImage.id,
            uid: this.siginImage.uid,
        },
        {
            src: this.siginImage.file_url,
            id: this.siginImage.id,
            uid: this.siginImage.uid,
        },
    ],
    id: this.siginImage.id,
    uid: this.siginImage.uid,
    describe: $('.images-modal .sigle-image-des').val()
});

*/
// data-tag-flag='gear-custom-module'
(function () {
    const COMMENT_ATTRIBUTES = [
        'comment_uid',
        'nums',
    ];

    // 引入源码中的BlockEmbed
    const BlockEmbed = Quill.import('blots/block/embed');
    // 定义新的blot类型
    class GearMultipleImage extends BlockEmbed {
        static create(options) {
            const node = super.create(options);
            node.setAttribute('class', 'gear-all-image gear-multiple-image');
            node.setAttribute('contenteditable', 'false');
            node.setAttribute('id', options.id);
            node.setAttribute('uid', options.uid);
            node.setAttribute('data-tag-flag', 'gear-custom-module');

            COMMENT_ATTRIBUTES.forEach(function (attribute) {
                if (options[attribute]) {
                    node.setAttribute(attribute, options[attribute]);
                }
            });

            let data = options.data;

            let desDom = document.createElement("div");
            desDom.innerText = options.describe
            desDom.setAttribute('class', 'img-describe');
            desDom.setAttribute('data-tag-flag', 'gear-custom-module');

            let swiperSlide = '';
            let swiperPagination = ''
            data.forEach((obj,index)=>{
                swiperSlide += `
                    <div class="swiper-slide item-box" data-tag-flag='gear-custom-module'>
                        <div class="swiper-slide-div" data-tag-flag='gear-custom-module'>
                            <div class="more-pic-box" data-tag-flag='gear-custom-module'>
                                <img class="item-img" src="${obj.src}" data-tag-flag='gear-custom-module' id="${obj.id}" src="${obj.uid}"/>
                            </div>
                        </div>
                    </div>
                `
                swiperPagination += `
                    <span data-tag-flag='gear-custom-module' class="swiper-pagination-bullet ${index==0?'active':''}"></span>
                `
            })

            let swiperDom = `
            <div class="swiper-container" data-tag-flag='gear-custom-module'>
                <div class="swiper-wrapper multiple-image-box" data-tag-flag='gear-custom-module'>
                    ${swiperSlide}
                </div>
                
                <div class="swiper-pagination" data-tag-flag='gear-custom-module'>
                    ${swiperPagination}
                </div>
                
                <div class="swiper-button-prev-g" data-tag-flag='gear-custom-module'></div>
                <div class="swiper-button-next-g" data-tag-flag='gear-custom-module'></div>
            </div>
            `
            node.appendChild($(swiperDom)[0])
            node.appendChild(desDom)
            return node;
        }
        // 返回节点自身的value值 用于撤销操作 与insertEmbed传递的参数一致
        static value(node) {
            let Dom = node
            let itemImg = node.querySelectorAll('.item-img')
            let desDom = node.querySelector('.img-describe')
            let data = [];
            itemImg.forEach(function(item){
                data.push({
                    src: $(item).attr('src'),
                    id: $(item).attr('id'),
                    uid: $(item).attr('uid'),
                })
            })
            var values = {
                data: data,
                id: Dom && Dom.getAttribute('id') || '',
                uid: Dom && Dom.getAttribute('uid') || '',
                describe: desDom && desDom.innerHTML || '',
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
    GearMultipleImage.blotName = 'GearMultipleImage';
    // class名将用于匹配blot名称
    // GearMultipleImage.className = 'gear-multiple-image';
    // 标签类型自定义
    GearMultipleImage.tagName = 'divImage';
    Quill.register(GearMultipleImage, true);

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


