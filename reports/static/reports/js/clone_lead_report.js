$(function(){
    $('#cloneLeadReportBtn').click(function () {
            if ($('#cloneLeadReportModal').hasClass('in')) {
                $('#cloneLeadReportModal').modal('hide');
            } else {
                renderSuggest.init();
                $('#cloneLeadReportModal').modal('show');
            }
        }
    )

    $('#cloneLeadReportModalClose').click(function () {
        $('#cloneLeadReportModal').modal('hide');
    });



    $('#cloneLeadReportModal').on('hidden.bs.modal', function (e) {
        $('#refLead > li:not(.suggest-title)').remove();
        $('#referenceLead').val('').attr('data-id', '').removeAttr('disabled', 'false');
    });
    $('#cloneLeadReportModal').on('shown.bs.modal', function (e) {
        window.setTimeout(function () {
            $('#referenceLead').focus();
        }, 400);
    });

    var renderSuggest = {
        // 获取项目需求列表
        getSuggestLIst: function (url) {
            var that = this;
            $.ajax({
                url: url,
                success: function (data) {
                    var suggestData = data.data;
                    var suggestTitle = {};
                    $('#refLead').children().remove();
                    suggestTitle.myOngoingProposals = '<li id="myOngoingProposals" class="suggest-title">我的进行中的线索</li>';
                    // 渲染我的需求
                    if (suggestData.length > 0) {
                        that.renderSuggestItem('#refLead', suggestData, suggestTitle.myOngoingProposals);
                    }
                }
            });
        },
        getSuggestItem: function (suggestItem) {
            var taskSuggestName = (suggestItem.name && suggestItem.name != ' ') ? suggestItem.name : suggestItem.description;
            var taskSuggestId = suggestItem.id;
            return ('<li data-id=' + taskSuggestId + '>' + taskSuggestName + '</li>');
        },
        renderSuggestItem: function (target, listData, suggestTitle) {
            $(target).show();
            var renderList = [];
            for (var i in listData) {
                renderList.push(this.getSuggestItem(listData[i]))
            }
            $(target).append(suggestTitle).append(renderList.join(''));
        },
        init: function () {
            this.getSuggestLIst('/api/clients/leads/mine?status=contact');
        }
    };


    $('#referenceLead').on('keyup', function (e) {
        var suggestEle = $(this).next('.suggest-container')
        selectSuggest(e, suggestEle, this);
    });

    $('#cancelCloneLeadReportButton').click(function () {
        $('#cloneLeadReportModal').modal('hide');
    });
    // 选择需求
    $('#referenceLead').on('focus', function () {
        $(this).next('.suggest-container').removeClass('hidden');
    });

    $('.reference-project').on('click', 'li:not(.suggest-title)', function (e) {
        var objectId = $(this).attr('data-id');
        $('#referenceLead').attr('data-id', objectId)
        $('#referenceLead').val($(this).text())
        $('#refLead').addClass('hidden');
    });


    function selectSuggest(e, element, target) {
        var suggestFirst = $(element).children('li').first();
        var suggestLast = $(element).children('li').last();
        var activeEle = $(element).children('li.active');
        var refName = null;
        if (e.keyCode === 40) {
            e.preventDefault();
            if (suggestLast[0] !== activeEle[0]) {
                if (activeEle.next('li').hasClass('suggest-title')) {
                    activeEle.removeClass('active').next('li').next('li').addClass('active');
                } else {
                    activeEle.removeClass('active').next('li').addClass('active');
                }
            }
            refName = $(element).children('li.active').text();
            $(target).val(refName);
            $(element).scrollTop(activeEle.index() * 40);
        }
        ;
        if (e.keyCode === 38) {
            e.preventDefault();
            if (activeEle[0] !== suggestFirst[0]) {
                if (activeEle.prev('li').hasClass('suggest-title')) {
                    activeEle.removeClass('active').prev('li').prev('li').addClass('active');
                } else {
                    activeEle.removeClass('active').prev('li').addClass('active');
                }
            }
            ;
            refName = $(element).children('li.active').text();
            $(target).val(refName);
            $(element).scrollTop(activeEle.index() * 40 - 100);
        }
        if (e.keyCode === 13) {
            $(element).addClass('hidden');
        }
    }

    // 检查form
    var checkAddNewTaskForm = function () {
        var dataId = $('#referenceLead').attr('data-id')
        if (dataId == undefined || dataId.trim() == '') {
            $('#referenceLead').css('border', '1px solid #FF0F1D');
            return false;
        }
        return true
    };
    // 提交任务
    $('#cloneLeadReportButton').click(function () {
        var subTaskData = {}
        // subTaskData.name = $('#referenceLead').val();
        subTaskData.source_report = PageData.reportData.id;
        if ($('#referenceLead').attr('data-id')) {
            subTaskData.lead = $('#referenceLead').attr('data-id');
        }
        if (checkAddNewTaskForm()) {
            $.ajax({
                type: 'POST',
                url: '/api/reports/create/lead_report/farm',
                contentType: 'application/json',
                data: JSON.stringify(subTaskData),
                success: function (data) {
                    if (data.result) {
                        $('#cloneLeadReportModal').modal('hide');
                        var openUrl = '/reports/' + data.data.uid + '/edit/';
                        window.open(openUrl);
                    } else {
                        farmAlter(data.message, 3000);
                    }

                },
                error: function () {
                    farmAlter('网络异常')
                }
            });
        }
    });

})
