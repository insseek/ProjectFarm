//表格中的数据
var tableData = [
    {
        versions: '',
        date: '',
        name: '',
    }
];
//监听表格的输入框
$('.history-table-tbody').on('input', '.table-input', function (e) {
    tableData[$(this).parents('.edit-table-tr').index()][$(this).attr('keyName')] = $(e.target).val();
})

//右键菜单
var trDom = `
        <tr class="edit-table-tr">
            <td>
                <input keyName="versions" class="table-input table-input-versions" type="text" value="" placeholder="请输入版本">
            </td>
            <td>
                <input keyName="date" class="table-input table-input-date" type="text" value="" placeholder="请输入日期">
            </td>
            <td>
                <input keyName="name" class="table-input table-input-name" type="text" value="" placeholder="请输入姓名">
            </td>
        </tr>
    `;
$('.history-table').contextMenu({
    selector: '.edit-table-tr',
    items: {
        upInset: {
            name: "上方插入一行",
            callback: function (itemKey, opt, e) {
                $(opt.$trigger).before(trDom);
                tableData.splice($(opt.$trigger).index() - 1, 0, {
                    versions: '',
                    date: '',
                    name: '',
                });
            }
        },
        downInset: {
            name: "下方插入一行",
            callback: function (itemKey, opt, e) {
                $(opt.$trigger).after(trDom);
                tableData.splice($(opt.$trigger).index() + 1, 0, {
                    versions: '',
                    date: '',
                    name: '',
                });
            }
        },
        del: {
            name: "删除所在行",
            callback: function (itemKey, opt, e) {
                tableData.splice($(opt.$trigger).index(), 1);
                $(opt.$trigger).remove();
            },
            disabled: function (key, opt) {
                return $('.edit-table-tr').length <= 1 ? true : false;
            }
        },
    }
});


// 开关点击
$('.edit-report-container').on('click','.switch-bg',function(e){
    $(this).siblings('.switch-input')[0].checked = !$(this).siblings('.switch-input')[0].checked;

    if ($(this).siblings('.switch-input').is(':checked')) {
        $(this).parents('.center-list-box').find('.masking-bg').hide();
        $(this).siblings('.switch-tip').children('.switch-tip-text').html('在报告中隐藏报价');
    } else {
        $(this).parents('.center-list-box').find('.masking-bg').show();
        $(this).siblings('.switch-tip').children('.switch-tip-text').html('在报告中显示报价');
    }
})
// 开关鼠标悬浮时的tip
$('.edit-report-container').on('mouseover','.switch-bg',function(e){
    if ($(this).siblings('.switch-input').is(':checked')) {
        $(this).siblings('.switch-tip').children('.switch-tip-text').html('在报告中隐藏报价');
    } else {
        $(this).siblings('.switch-tip').children('.switch-tip-text').html('在报告中显示报价');
    }
})
$('.edit-report-container').on('mouseout','.switch-bg',function(e){
})

//顶部阴影
$(window).scroll(function () {
    if($(document).scrollTop()>50){
        $('.toolbar-fixed').addClass('scroll-top')
    }else{
        $('.toolbar-fixed').removeClass('scroll-top')
    }
})