(function () {
    const ATTRIBUTES = [
        'alt',
        'height',
        'width',
        'src',
        'flag',
        'class',
        'id',
        'json_url',
        'file_url',
        'filename',
        'comment_uid',
        'nums'
    ];
    const Block = Quill.import("blots/block");
    const Image = Quill.import("formats/image");


    class GearImageBox extends Block {
        static create(options) {
            let node = super.create(options);
            // node.setAttribute('class', 'image-container');
            let image = document.createElement("img");
            // image.setAttribute('data-tag-flag', 'gear-custom-module');

            ATTRIBUTES.forEach(function (attribute) {
                if (options[attribute]) {
                    image.setAttribute(attribute, options[attribute]);
                }
            });
            if (!image.hasAttribute('class')) {
                image.setAttribute('class', 'gear-all-image');
            }
            if (!image.hasAttribute('flag')) {
                image.setAttribute('flag', 'general');
            }
            for (let key in options) {
                if (key == 'class') {
                    options[key] = options[key] + ' normal-image'
                }
                image.setAttribute(key, options[key]);
            }
            node.appendChild(image);

            return node;
        }

        static value(node) {
            let image = node.querySelector('img')
            var values = {};
            ATTRIBUTES.forEach(function (attribute) {
                if (image.hasAttribute(attribute)) {
                    values[attribute] = image.getAttribute(attribute)
                }
            });
            return values
        }
    }

    //定义图片插入时外层加一个p标签 blotName为gear-image
    GearImageBox.blotName = 'gear-image';
    GearImageBox.tagName = 'p';
    Quill.register(GearImageBox, true);

    //overwrite formats/image 覆盖原有的
    class GearImage extends Image {
        static create(options) {
            let node = super.create(options.src);
            ATTRIBUTES.forEach(function (attribute) {
                if (options[attribute]) {
                    node.setAttribute(attribute, options[attribute]);
                }
            });
            if (!node.hasAttribute('class')) {
                node.setAttribute('class', 'gear-all-image');
            }
            if (!node.hasAttribute('flag')) {
                node.setAttribute('flag', 'general');
            }

            return node;
        }

        static value(node) {
            var values = {};
            ATTRIBUTES.forEach(function (attribute) {
                if (node.hasAttribute(attribute)) {
                    values[attribute] = node.getAttribute(attribute)
                }
            });
            return values
        }
    }

    GearImage.blotName = 'image';
    GearImage.tagName = 'IMG';


    Quill.register(GearImage, true);

})();



