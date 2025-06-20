export function initQuillKeyboard(quill){

    quill.keyboard.addBinding({
        key: '1',
        shortKey: true,
        shiftKey: true,
    }, function (range, context) {
        $('.ql-main').click();

    });
    quill.keyboard.addBinding({
        key: '2',
        shiftKey: true,
        shortKey: true,
    }, function (range, context) {
        $('.ql-title').click();
    });
    quill.keyboard.addBinding({
        key: '3',
        shiftKey: true,
        shortKey: true,
    }, function (range, context) {
        $('.ql-title-small').click();
    });
    quill.keyboard.addBinding({
        key: '7',
        shiftKey: true,
        shortKey: true,
    }, function (range, context) {
        $('.ql-bullet').click();
    });
    quill.keyboard.addBinding({
        key: 'L',
        shiftKey: true,
        shortKey: true,
    }, function (range, context) {
        $('.ql-ordered').click();
    });
}

