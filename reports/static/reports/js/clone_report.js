$(function(){
    $('#cloneReportBtn').click(function () {
            if ($('#cloneReportModal').hasClass('in')) {
                $('#cloneReportModal').modal('hide');
            } else {
                renderSuggest.init();
                $('#cloneReportModal').modal('show');
            }
        }
    );
    $('#cloneReportModal').on('hidden.bs.modal', function (e) {
        $('#refProjectAndPropsal > li:not(.suggest-title)').remove();
        $('#referenceProject').val('').attr('data-id', '').removeAttr('disabled', 'false');
    });
    $('#cloneReportModal').on('shown.bs.modal', function (e) {
        window.setTimeout(function () {
            $('#referenceProject').focus();
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
                    $('#refProjectAndPropsal').children().remove();
                    suggestTitle.myOngoingProposals = '<li id="myOngoingProposals" class="suggest-title">我的进行中的需求</li>';
                    suggestTitle.otherOngoingProposals = '<li id="othetOngoingProposals" class="suggest-title">其他进行中的需求</li>';
                    // 渲染我的需求
                    if (suggestData.my_ongoing_proposals.length > 0) {
                        that.renderSuggestItem('#refProjectAndPropsal', suggestData.my_ongoing_proposals, suggestTitle.myOngoingProposals);
                    }
                    // 渲染其他需求
                    if (suggestData.other_ongoing_proposals.length > 0) {
                        that.renderSuggestItem('#refProjectAndPropsal', suggestData.other_ongoing_proposals, suggestTitle.otherOngoingProposals);
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
            this.getSuggestLIst('/api/tasks/sources/');
        }
    };

// 搜索项目
    $('#referenceProject').bind('input propertychange', function () {
        $('#refProjectAndPropsal > li:not(.suggest-title)').remove();
        var searchKeyWords = $(this).val();
        var searchUrl = '/api/tasks/sources';
        if (searchKeyWords.trim() != '') {
            searchUrl += '?search_value=' + searchKeyWords;
        }
        renderSuggest.getSuggestLIst(searchUrl);
    });

    $('#referenceProject').on('keyup', function (e) {
        var suggestEle = $(this).next('.suggest-container')
        selectSuggest(e, suggestEle, this);
    });

    $('.quick-add-task-close').click(function () {
        $('#cloneReportModal').modal('hide');
    });
// 选择需求
    $('#referenceProject').on('focus', function () {
        $(this).next('.suggest-container').removeClass('hidden');
    });

    $('.reference-project').on('click', 'li:not(.suggest-title)', function (e) {
        var objectId = $(this).attr('data-id');
        $('#referenceProject').attr('data-id', objectId)
        $('#referenceProject').val($(this).text())
        $('#refProjectAndPropsal').addClass('hidden');
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
        ;
        if (e.keyCode === 13) {
            $(element).addClass('hidden');
        }
    }
// 检查form
    var checkAddNewTaskForm = function () {
        var dataId = $('#referenceProject').attr('data-id')
        if (dataId == undefined || dataId.trim() == '') {
            $('#referenceProject').css('border', '1px solid #FF0F1D');
            return false;
        }
        return true
    };
// 提交任务
    $('#addTaskButton').click(function () {
        var subTaskData = {}
        // subTaskData.name = $('#referenceProject').val();
        subTaskData.source_report = PageData.reportData.id;
        if ($('#referenceProject').attr('data-id')) {
            subTaskData.proposal = $('#referenceProject').attr('data-id');
        }
        if (checkAddNewTaskForm()) {
            $.ajax({
                type: 'POST',
                url: '/api/reports/create/proposal_report/farm',
                contentType: 'application/json',
                data: JSON.stringify(subTaskData),
                success: function (data) {
                    if (data.result) {
                        $('#cloneReportModal').modal('hide');
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