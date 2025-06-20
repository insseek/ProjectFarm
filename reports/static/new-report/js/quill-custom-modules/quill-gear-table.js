(function () {
    class quillGearBetterTable extends quillBetterTable {
        constructor(quill,option) {
            super(quill,option);

            this.quill = quill;
            this.toolbar = quill.getModule('toolbar');

            this.init();

            if (typeof this.toolbar != 'undefined') {
                this.toolbar.addHandler('insert-table-btn', this.insertTableHanlder.bind(this));
            }

        }

        //初始化
        init() {

        }
        insertTableHanlder(){
            let tableModule = quill.getModule('better-table')
            tableModule.insertTable(3, 3)
        }

    }

    Quill.register('modules/better-table', quillGearBetterTable);

})();



