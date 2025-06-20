    // 通过消息实时推送实现协作编辑
    // 自己的鼠标
    const cursorsModule = quill.getModule('multi_cursors');
    var cursorsDict = {};
    const COLOR = [
        '#FE802F', '#33C4E7', '#9FD218',
        '#19C582', '#EAE718', '#008DEC',
        '#8465FA', '#D047FF', '#FF239C'
    ];
    const myCursorId = getUUID(2, 62);
    const myCursorName = '李韩非' + getUUID(2, 62);
    const myCursorColor = COLOR[Math.floor(Math.random() * 9 + 1) - 1];
    const myCursorData = {"id": myCursorId, "name": myCursorName, "color": myCursorColor}
    createNewCursor(myCursorData);

    function createNewCursor(cursorData) {
        let newCursor = cursorsModule.createCursor(cursorData.id, cursorData.name, cursorData.color)
        cursorsDict[cursorData.id] = newCursor
    }
    var client = emitter.connect({
        "host": "api.emitter.io",
        "port": 8080
    });
    var emitterKey = "2aWuhH71Kdnh7L60b_ypW9V_rQ6Ylv6y";
    var channelName = 'report/uuid/edit';
    // use require('emitter-io').connect() on NodeJS
    // once we're connected, subscribe to the 'chat' channel
    client.subscribe({
        key: emitterKey,
        channel: channelName
    });
    client.publish({
        key: emitterKey,
        channel: channelName,
        message: JSON.stringify({"user": myCursorData, "event": "create-cursor"})
    });
    // on every message, print it out
    client.on('message', function (msg) {
        var msg = msg.asObject();

        if (msg.user.id != myCursorId) {
            if (msg.event == "text-change") {
                quill.updateContents(msg.delta);
            }
            if (msg.event == "create-cursor" || cursorsDict[msg.user.id] == undefined) {
                createNewCursor(msg.user)
            }
            if (msg.event == "selection-change" ) {
                cursorsModule.moveCursor(msg.user.id, msg.range);
            }
        }
    });
    quill.on('text-change', function (delta, oldContents, source) {
        if (source === 'user') {
            client.publish({
                key: emitterKey,
                channel: channelName,
                message: JSON.stringify({delta: delta, user: myCursorData, event: "text-change", source: source})
            });
        }
    });

    quill.on('selection-change', function (range) {
        client.publish({
            key: emitterKey,
            channel: channelName,
            message: JSON.stringify({"range": range, "user": myCursorData, "event": "selection-change"})
        });
    });
