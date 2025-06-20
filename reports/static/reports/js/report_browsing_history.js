const objBrowsingLogSettings = {
    contentTypeData: {
        app_label: 'reports',
        model: 'report',
        object_id: reportData.id,
    },
    visitorName: (typeof loggedUser !== "undefined" && loggedUser) ? loggedUser.username + loggedUser.id : ''
};
$(function () {
        var contentTypeData = objBrowsingLogSettings.contentTypeData;
        var visitorName = objBrowsingLogSettings.visitorName;
        // 每间隔半小时内同一个用户 只统计一次浏览记录，时长为阅读累积时长
        // 当前用户+同一个报告uid 作为key
        var currentViewCacheKey = contentTypeData.app_label + contentTypeData.model + contentTypeData.object_id + visitorName;
        var currentViewId = null;
        var setVisitTimeout = null;
        var isVisitTimeout = false;
        TimeMe.initialize({
            currentPageName: window.location.href,
            idleTimeoutInSeconds: 120 // seconds
        });
        TimeMe.callWhenUserLeaves(function () {
            setVisitTimeout && window.clearTimeout(setVisitTimeout);
            setVisitTimeout = setTimeout(function () {
                if (currentViewId) {
                    finishCurrentBrowsing();
                }
                isVisitTimeout = true
            }, 1800000);
        });
        TimeMe.callWhenUserReturns(function () {
            if (isVisitTimeout) {
                isVisitTimeout = false;
                finishCurrentBrowsing();
                createNewView();
            } else {
                if (setVisitTimeout != null) {
                    window.clearTimeout(setVisitTimeout);
                    setVisitTimeout = null;
                }
            }
        });
        window.onload = function () {
            setCurrentViewId();
            sendViewSeconds();
        };
        window.onunload = function (e) {
            if (currentViewId != null) {
                finishCurrentBrowsing();
            }
        };

        // 重写localStorage get
        function getStorageExpire(key, remove = true) {
            const val = localStorage.getItem(key);
            if (val != null) {
                this.storageInfo = JSON.parse(val);
                const timeSpan = Date.now() - this.storageInfo.time;

                if (timeSpan > this.storageInfo.expire) {
                    if (remove) {
                        localStorage.removeItem(key);
                    }
                    return null;
                }
                return this.storageInfo.value;
            }
            return null;
        }

        //重写localStorage set
        function setStorageExpire(key, value, expire) {
            const obj = {
                value: value,
                time: Date.now(),
                expire: 1000 * 60 * expire  // 单位是分钟
            };
            localStorage.setItem(key, JSON.stringify(obj));
        }

        sendViewSeconds = function () {
            setInterval(function () {
                if (currentViewId != null) {
                    finishCurrentBrowsing();
                }
            }, 20000);
        };

        function setCurrentViewId() {
            var currentView = getStorageExpire(currentViewCacheKey);
            if (currentView) {
                currentViewId = currentView.browsing_history_id;
            } else {
                createNewView()
            }
        }

        function createNewView() {
            if (!contentTypeData.object_id) {
                return
            }
            var subData = contentTypeData;
            commonRequest('POST', '/api/logs/browsing_histories', subData, function (data) {
                localStorage.removeItem(currentViewCacheKey);
                currentViewId = data.data.id;
                TimeMe.resetAllRecordedPageTimes();
            })
        }

        function finishCurrentBrowsing() {
            if (!currentViewId || currentViewId == 'null') {
                return
            }
            var subData = {};
            var timeInSeconds = TimeMe.getTimeOnCurrentPageInSeconds() ? TimeMe.getTimeOnCurrentPageInSeconds() : 0;
            subData.browsing_history_id = currentViewId;
            subData.browsing_seconds = timeInSeconds;
            var currentView = getStorageExpire(currentViewCacheKey);
            if (currentView) {
                subData.browsing_seconds = parseInt(currentView.browsing_seconds + subData.browsing_seconds)
            }
            setStorageExpire(currentViewCacheKey, JSON.parse(JSON.stringify(subData)), 30);
            TimeMe.resetAllRecordedPageTimes();
            if (!currentViewId) {
                return
            }
            var url = '/api/logs/browsing_histories/' + currentViewId + '/done';
            commonSyncRequest('POST', url, subData, function () {
            })
        }
    }
);