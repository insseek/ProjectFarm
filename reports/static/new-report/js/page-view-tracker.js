/*Copyright (c) 2017 Jason Zissman
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

(function () {
    (function (root, factory) {
        if (typeof module !== 'undefined' && module.exports) {
            // CommonJS
            return module.exports = factory();
        } else if (typeof define === 'function' && define.amd) {
            // AMD
            define([], function () {
                return (root.PageViewTracker = factory());
            });
        } else {
            // Global Variables
            return root.PageViewTracker = factory();
        }
    })(this, function () {
        var PageViewTracker = {

            startStopTimes: {},
            idleTimeoutMs: 30 * 1000,
            currentIdleTimeMs: 0,
            checkStateRateMs: 250,
            active: false,
            idle: false,
            currentPageName: "default-page-name",
            timeElapsedCallbacks: [],
            userLeftCallbacks: [],
            userReturnCallbacks: [],

            pageData: {},
            setVisitTimeout: null,
            visitIsTimeout: false,
            serverDomain: '',
            pageViewStartUrl: '/api/reports/pageview/return',
            pageViewEndUrl: '/api/reports/pageview/leave',

            getFullPath: function (path) {
                return PageViewTracker.serverDomain + path
            },
            commonRequest: function (type, url, subData, func) {
                url = PageViewTracker.getFullPath(url);
                $.ajax({
                    type: type,
                    url: url,
                    contentType: 'application/json',
                    headers: {
                    },
                    data: JSON.stringify(subData),
                    success: function (data) {
                        func(data);
                    },
                    error: function (err) {
                        func(err);
                    }
                });
            },
            commonSyncRequest: function (type, url, subData, func) {
                url = PageViewTracker.getFullPath(url);
                $.ajax({
                    type: type,
                    url: url,
                    async: false,
                    timeout: 3000,
                    contentType: 'application/json',
                    data: JSON.stringify(subData),
                    success: function (data) {
                        func(data);
                    },
                    error: function (err) {
                        err.resultCode = "500";
                        func(err);
                    }
                });
            },
            startPageView: function (createNewView = false) {
                var subData = PageViewTracker.pageData;
                var url = PageViewTracker.pageViewStartUrl;
                PageViewTracker.commonRequest('POST', url, subData, function (data) {
                    if (!data.result) {
                    }
                })
            },
            endPageView: function () {
                var result = false;
                var subData = PageViewTracker.pageData;
                var url = PageViewTracker.pageViewEndUrl;
                PageViewTracker.commonRequest('POST', url, subData, function (data) {
                    if (data.result == true) {
                        result = true;
                    } else {
                        console.info(data)
                    }
                });
                return result
            },
            startPageViewTracker: function () {
                // PageViewTracker.startPageView();
                $(window).on('beforeunload', function () {
                    PageViewTracker.endPageView();
                    // return false
                });
                PageViewTracker.callWhenUserLeaves(function () {
                    PageViewTracker.setVisitTimeout && window.clearTimeout(PageViewTracker.setVisitTimeout);
                    PageViewTracker.setVisitTimeout = setTimeout(function () {
                        PageViewTracker.endPageView();
                        PageViewTracker.visitIsTimeout = true
                    }, 180000);
                });
                PageViewTracker.callWhenUserReturns(function () {
                    if (PageViewTracker.visitIsTimeout) {
                        PageViewTracker.startPageView(true);
                        PageViewTracker.visitIsTimeout = false;
                    }
                    PageViewTracker.setVisitTimeout && window.clearTimeout(PageViewTracker.setVisitTimeout);
                    PageViewTracker.setVisitTimeout = null;
                });
            }
            ,
            trackTimeOnElement: function (elementId) {
                var element = document.getElementById(elementId);
                if (element) {
                    element.addEventListener("mouseover", function () {
                        PageViewTracker.startTimer(elementId);
                    });
                    element.addEventListener("mousemove", function () {
                        PageViewTracker.startTimer(elementId);
                    });
                    element.addEventListener("mouseleave", function () {
                        PageViewTracker.stopTimer(elementId);
                    });
                    element.addEventListener("keypress", function () {
                        PageViewTracker.startTimer(elementId);
                    });
                    element.addEventListener("focus", function () {
                        PageViewTracker.startTimer(elementId);
                    });
                }
            },

            startTimer: function (pageName) {
                if (!pageName) {
                    pageName = PageViewTracker.currentPageName;
                }
                PageViewTracker.startStopTimes[pageName] = {uid: pageName, active: true};
                PageViewTracker.active = true;
            },

            stopAllTimers: function () {
                var pageNames = Object.keys(PageViewTracker.startStopTimes);
                for (var i = 0; i < pageNames.length; i++) {
                    PageViewTracker.stopTimer(pageNames[i]);
                }
            },

            stopTimer: function (pageName) {
                if (!pageName) {
                    pageName = PageViewTracker.currentPageName;
                }
                PageViewTracker.startStopTimes[pageName] = {uid: pageName, active: false};
                PageViewTracker.active = false;
            },

            setIdleDurationInSeconds: function (duration) {
                var durationFloat = parseFloat(duration);
                if (isNaN(durationFloat) === false) {
                    PageViewTracker.idleTimeoutMs = duration * 1000;
                } else {
                    throw {
                        name: "InvalidDurationException",
                        message: "An invalid duration time (" + duration + ") was provided."
                    };
                }
                return this;
            },

            setCurrentPageName: function (pageName) {
                PageViewTracker.currentPageName = pageName;
                return this;
            },
            setPageData: function (pageData) {
                PageViewTracker.pageData = pageData;
                return this;
            },

            resetRecordedPageTime: function (pageName) {
                delete PageViewTracker.startStopTimes[pageName];
            },

            resetAllRecordedPageTimes: function () {
                var pageNames = Object.keys(PageViewTracker.startStopTimes);
                for (var i = 0; i < pageNames.length; i++) {
                    PageViewTracker.resetRecordedPageTime(pageNames[i]);
                }
            },

            resetIdleCountdown: function () {
                if (PageViewTracker.idle) {
                    PageViewTracker.triggerUserHasReturned();
                }
                PageViewTracker.idle = false;
                PageViewTracker.currentIdleTimeMs = 0;
            },

            callWhenUserLeaves: function (callback, numberOfTimesToInvoke) {
                this.userLeftCallbacks.push({
                    callback: callback,
                    numberOfTimesToInvoke: numberOfTimesToInvoke
                })
            },

            callWhenUserReturns: function (callback, numberOfTimesToInvoke) {
                this.userReturnCallbacks.push({
                    callback: callback,
                    numberOfTimesToInvoke: numberOfTimesToInvoke
                })
            },

            triggerUserHasReturned: function () {
                if (!PageViewTracker.active) {
                    for (var i = 0; i < this.userReturnCallbacks.length; i++) {
                        var userReturnedCallback = this.userReturnCallbacks[i];
                        var numberTimes = userReturnedCallback.numberOfTimesToInvoke;
                        if (isNaN(numberTimes) || (numberTimes === undefined) || numberTimes > 0) {
                            userReturnedCallback.numberOfTimesToInvoke -= 1;
                            userReturnedCallback.callback();
                        }
                    }
                }
                PageViewTracker.startTimer();
            },

            triggerUserHasLeftPage: function () {
                if (PageViewTracker.active) {
                    for (var i = 0; i < this.userLeftCallbacks.length; i++) {
                        var userHasLeftCallback = this.userLeftCallbacks[i];
                        var numberTimes = userHasLeftCallback.numberOfTimesToInvoke;
                        if (isNaN(numberTimes) || (numberTimes === undefined) || numberTimes > 0) {
                            userHasLeftCallback.numberOfTimesToInvoke -= 1;
                            userHasLeftCallback.callback();
                        }
                    }
                }
                PageViewTracker.stopAllTimers();
            },

            callAfterTimeElapsedInSeconds: function (timeInSeconds, callback) {
                PageViewTracker.timeElapsedCallbacks.push({
                    timeInSeconds: timeInSeconds,
                    callback: callback,
                    pending: true
                });
            },

            checkState: function () {
                for (var i = 0; i < PageViewTracker.timeElapsedCallbacks.length; i++) {
                    if (PageViewTracker.timeElapsedCallbacks[i].pending) {
                        PageViewTracker.timeElapsedCallbacks[i].callback();
                        PageViewTracker.timeElapsedCallbacks[i].pending = false;
                    }
                }
                if (PageViewTracker.idle === false && PageViewTracker.currentIdleTimeMs > PageViewTracker.idleTimeoutMs) {
                    PageViewTracker.idle = true;
                    PageViewTracker.triggerUserHasLeftPage();
                } else {
                    PageViewTracker.currentIdleTimeMs += PageViewTracker.checkStateRateMs;
                }
            },

            visibilityChangeEventName: undefined,
            hiddenPropName: undefined,

            listenForVisibilityEvents: function () {

                if (typeof document.hidden !== "undefined") {
                    PageViewTracker.hiddenPropName = "hidden";
                    PageViewTracker.visibilityChangeEventName = "visibilitychange";
                } else if (typeof document.mozHidden !== "undefined") {
                    PageViewTracker.hiddenPropName = "mozHidden";
                    PageViewTracker.visibilityChangeEventName = "mozvisibilitychange";
                } else if (typeof document.msHidden !== "undefined") {
                    PageViewTracker.hiddenPropName = "msHidden";
                    PageViewTracker.visibilityChangeEventName = "msvisibilitychange";
                } else if (typeof document.webkitHidden !== "undefined") {
                    PageViewTracker.hiddenPropName = "webkitHidden";
                    PageViewTracker.visibilityChangeEventName = "webkitvisibilitychange";
                }

                document.addEventListener(PageViewTracker.visibilityChangeEventName, function () {
                    if (document[PageViewTracker.hiddenPropName]) {
                        PageViewTracker.triggerUserHasLeftPage();
                    } else {
                        PageViewTracker.triggerUserHasReturned();
                    }
                }, false);

                window.addEventListener('blur', function () {
                    PageViewTracker.triggerUserHasLeftPage();
                });

                window.addEventListener('focus', function () {
                    PageViewTracker.triggerUserHasReturned();
                });

                document.addEventListener("mousemove", function () {
                    PageViewTracker.resetIdleCountdown();
                });
                document.addEventListener("keyup", function () {
                    PageViewTracker.resetIdleCountdown();
                });
                document.addEventListener("touchstart", function () {
                    PageViewTracker.resetIdleCountdown();
                });
                window.addEventListener("scroll", function () {
                    PageViewTracker.resetIdleCountdown();
                });

                setInterval(function () {
                    PageViewTracker.checkState();
                }, PageViewTracker.checkStateRateMs);
            },

            websocket: undefined,

            websocketHost: undefined,

            setUpWebsocket: function (websocketOptions) {
                if (window.WebSocket && websocketOptions) {
                    var websocketHost = websocketOptions.websocketHost; // "ws://hostname:port"
                    try {
                        PageViewTracker.websocket = new WebSocket(websocketHost);
                        window.onbeforeunload = function (event) {
                            PageViewTracker.sendCurrentTime(websocketOptions.appId);
                        };
                        PageViewTracker.websocket.onopen = function () {
                            PageViewTracker.sendInitWsRequest(websocketOptions.appId);
                        };
                        PageViewTracker.websocket.onerror = function (error) {
                            if (console) {
                                console.log("Error occurred in websocket connection: " + error);
                            }
                        };
                        PageViewTracker.websocket.onmessage = function (event) {
                            if (console) {
                                console.log(event.data);
                            }
                        }
                    } catch (error) {
                        if (console) {
                            console.error("Failed to connect to websocket host.  Error:" + error);
                        }
                    }
                }
                return this;
            },

            websocketSend: function (data) {
                PageViewTracker.websocket.send(JSON.stringify(data));
            },

            sendCurrentTime: function (appId) {
                var timeSpentOnPage = PageViewTracker.getTimeOnCurrentPageInMilliseconds();
                var data = {
                    type: "INSERT_TIME",
                    appId: appId,
                    timeOnPageMs: timeSpentOnPage,
                    pageName: PageViewTracker.currentPageName
                };
                PageViewTracker.websocketSend(data);
            },
            sendInitWsRequest: function (appId) {
                var data = {
                    type: "INIT",
                    appId: appId
                };
                PageViewTracker.websocketSend(data);
            },

            initialize: function (options) {

                var idleTimeoutInSeconds = PageViewTracker.idleTimeoutMs || 30;
                var currentPageName = PageViewTracker.currentPageName || "default-page-name";
                var pageData = PageViewTracker.pageData || {};
                var websocketOptions = undefined;

                if (options) {
                    idleTimeoutInSeconds = options.idleTimeoutInSeconds || idleTimeoutInSeconds;
                    currentPageName = options.currentPageName || currentPageName;
                    websocketOptions = options.websocketOptions;
                    pageData = options.pageData || pageData;
                }

                PageViewTracker.setIdleDurationInSeconds(idleTimeoutInSeconds)
                    .setCurrentPageName(currentPageName)
                    .setPageData(pageData)
                    .setUpWebsocket(websocketOptions)
                    .listenForVisibilityEvents();

                // TODO - only do this if page currently visible.

                PageViewTracker.startTimer(undefined);
                PageViewTracker.startPageViewTracker();
            }
        };
        return PageViewTracker;
    });
}).call(this);
