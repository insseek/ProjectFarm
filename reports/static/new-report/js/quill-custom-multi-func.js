let Clipboard = Quill.import('modules/clipboard');
let Delta = Quill.import('delta');

class MyClipboard extends Clipboard {
    onPaste(e) {
        var reportContainerScrollTop = $('.report-container').scrollTop();
        if (e.defaultPrevented || !this.quill.isEnabled()) return;
        let range = this.quill.getSelection();
        let delta = new Delta().retain(range.index);
        let scrollTop = this.quill.scrollingContainer.scrollTop;
        this.container.focus();
        this.quill.selection.update(Quill.sources.SILENT);
        setTimeout(() => {
            $('.report-container').scrollTop(reportContainerScrollTop);
            delta = delta.concat(this.convert()).delete(range.length);
            this.quill.updateContents(delta, Quill.sources.USER);
            // range.length contributes to delta.length()
            this.quill.setSelection(delta.length() - range.length, Quill.sources.SILENT);
            this.quill.scrollingContainer.scrollTop = scrollTop;
            this.quill.focus();
            $('.report-container').scrollTop(reportContainerScrollTop);
        }, 1);
    }

}

Quill.register('modules/clipboard', MyClipboard);

