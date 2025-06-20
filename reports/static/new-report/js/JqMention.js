;(function ($) {

    var CreateTextArea = function(ele,opt){
        this.$elemnt = ele;
        this.defaults = {
            placeholder: '请输入'
        };
        this.options = $.extend({}, this.defaults, opt);
    }
    CreateTextArea.prototype = {
        initDom :function(){
            let dom = `
                <div class="gear-at-div">
                    <div class="gear-at-textarea" contenteditable="true" data-beforeContent="${this.options.placeholder}"></div>
                </div>
                `;
            return this.$elemnt.html($(dom)[0]);
        },
        setAtwho: function(){
            var opt = this.options;
            this.$elemnt.find('.gear-at-textarea').atwho({
                at: "@",
                data: opt.userList,
                displayTpl: "<li><img color='${avatar_color}' name='${username}' widthSize='24' fontSize='12' src='${avatar_url}' onerror='userAvatarImgError(this)'/>${username}</li>",
                insertTpl: "<div id='${id}' userName='${username}' avatarUrl='${avatar_url}' color='${avatar_color}' name='${username}' email='${email}' class='gear-user-box' href='javascript:;'>${username}</div>",
                limit: 40,
                searchKey: "username",
                sendFun: function(val){
                    opt.enterCallbick(val)
                }
            });
        },
        initFunction: function(){
            var elem = this.$elemnt;
            let that = this;
            elem.on('input','.gear-at-textarea',function(){
                if(elem.find('.gear-at-textarea').text() == '' && elem.find('.gear-at-textarea').html() == ''){
                    elem.find('.gear-at-textarea').attr('data-beforeContent', that.options.placeholder);
                }else{
                    elem.find('.gear-at-textarea').attr('data-beforeContent', '');
                }
            })
            elem.on('change','.gear-at-textarea',function(){
                var userNameDom = elem.find('.atwho-inserted');
                var userNameData = [];
                if(userNameDom.length>0){
                    userNameDom.each(function() {
                        userNameData.push($(this).text())
                    })
                }
                elem.attr('userNameData',userNameData)
            })

            if(that.options.defValue == ''){
                elem.find('.gear-at-textarea').html('');
                elem.find('.gear-at-textarea').attr('data-beforeContent', that.options.placeholder);
            }else{
                elem.find('.gear-at-textarea').focus().html(that.options.defValue);
                elem.find('.gear-at-textarea').attr('data-beforeContent', '');
                var range = window.getSelection();//创建range
                range.selectAllChildren(elem.find('.gear-at-textarea')[0]);//range 选择obj下所有子内容
                range.collapseToEnd();//光标移至最后
            }

        }

    }

    $.fn.JqMention = function(options) {
        return this.each(function() {
            var createTextArea = new CreateTextArea($(this), options);
            createTextArea.initDom();
            createTextArea.setAtwho();
            createTextArea.initFunction();
        })
    }
})(jQuery);
