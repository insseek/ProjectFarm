function commonRequest(type, url, params, func) {
    params = params ? params : {};
    if (type.toUpperCase() != 'GET') {
        params = JSON.stringify(params)
    }
    let request = $.ajax({
        type: type,
        url: url,
        contentType: 'application/json',
        data: params,
        success: function (data, status, xhr) {
            let pagination_properties = xhr.getResponseHeader('X-Pagination');
            if (pagination_properties && !data.pagination_properties) {
                data.pagination_properties = JSON.parse(pagination_properties);
            }
            func(data);
        },
        error: function (err) {
            if (err.responseJSON) {
                func(err.responseJSON);
            } else if (err.status == 0 && err.statusText == 'abort') {
            } else {
                func({result: false, message: '服务器错误 请联系管理员'});
            }
        }
    });
    return request
}

function commonRequestDown(type, url, params, func) {
    params = params ? params : {};
    if (type.toUpperCase() != 'GET') {
        params = JSON.stringify(params)
    }
    let request = $.ajax({
        type: type,
        url: url,
        contentType: 'application/json',
        xhrFields: { responseType: "blob" },
        data: params,
        success: function (data, status, xhr) {
            var str = xhr.getResponseHeader("Content-Disposition");
            var fileName = str.split("filename*=utf-8''")[1];
            func({
                data:data,
                fileName:fileName
            });
        },
        error: function (err) {
            if (err.responseJSON) {
                func(err.responseJSON);
            } else if (err.status == 0 && err.statusText == 'abort') {
            } else {
                func({result: false, message: '服务器错误 请联系管理员'});
            }
        }
    });
    return request
}




function commonSyncRequest(type, url, params, func) {
    params = params ? params : {};
    if (type.toUpperCase() != 'GET') {
        params = JSON.stringify(params)
    }
    let request = $.ajax({
        type: type,
        url: url,
        async: false,
        contentType: 'application/json',
        data: params,
        success: function (data, status, xhr) {
            let pagination_properties = xhr.getResponseHeader('X-Pagination');
            if (pagination_properties && !data.pagination_properties) {
                data.pagination_properties = JSON.parse(pagination_properties);
            }
            func(data);
        },
        error: function (err) {
            if (err.responseJSON) {
                func(err.responseJSON);
            } else if (err.status == 0 && err.statusText == 'abort') {

            } else {
                farmAlter ? farmAlter("服务器错误 请联系管理员") : alert("服务器错误 请联系管理员")
            }
        }
    });
    return request
}


function copyJsonObj(obj) {
    return JSON.parse(JSON.stringify(obj))
}

function deepCopyJson(obj) {
    return JSON.parse(JSON.stringify(obj))
}

// 字符串、数组基本方法
// 字符串的常用方法
// indexOf()
// includes()
// startsWith()
// endsWith()
// 字符串中是否匹配指定字符
function matchingStr(str, avtiveStr) {
    let arrs = str.split(' ');
    for (let i = 0; i < arrs.length; i++) {
        if (arrs[i] == avtiveStr) {
            return true;
        }
    }
    return false;
}

// 判断是否为空  0 false '' undefined [], null都无效
function isValidValue(value) {
    if (typeof (value) == "undefined" || value == undefined || value == null || value == false || value == '') {
        return false
    }
    if (isNaN(value) && value == 0) {
        return false
    }
    if ((value instanceof Array) && value.length == 0) {
        return false
    }
    if ((typeof value) == 'string' && value.trim() == '') {
        return false
    }
    let result = value ? true : false
    return result
}

/**
 * 验证数据 是数字：返回true；不是数字：返回false
 **/

function isRealNumber(val) {
    if (parseFloat(val).toString() == "NaN") {
        return false;
    } else {
        return true;
    }
}

//深度比较两个js对象
function deepCompare(x, y) {
    var i, l, leftChain, rightChain;

    function compare2Objects(x, y) {
        var p;

        // remember that NaN === NaN returns false
        // and isNaN(undefined) returns true
        if (isNaN(x) && isNaN(y) && typeof x === 'number' && typeof y === 'number') {
            return true;
        }

        // Compare primitives and functions.
        // Check if both arguments link to the same object.
        // Especially useful on the step where we compare prototypes
        if (x === y) {
            return true;
        }

        // Works in case when functions are created in constructor.
        // Comparing dates is a common scenario. Another built-ins?
        // We can even handle functions passed across iframes
        if ((typeof x === 'function' && typeof y === 'function') ||
            (x instanceof Date && y instanceof Date) ||
            (x instanceof RegExp && y instanceof RegExp) ||
            (x instanceof String && y instanceof String) ||
            (x instanceof Number && y instanceof Number)) {
            return x.toString() === y.toString();
        }

        // At last checking prototypes as good as we can
        if (!(x instanceof Object && y instanceof Object)) {
            return false;
        }

        if (x.isPrototypeOf(y) || y.isPrototypeOf(x)) {
            return false;
        }

        if (x.constructor !== y.constructor) {
            return false;
        }

        if (x.prototype !== y.prototype) {
            return false;
        }

        // Check for infinitive linking loops
        if (leftChain.indexOf(x) > -1 || rightChain.indexOf(y) > -1) {
            return false;
        }

        // Quick checking of one object being a subset of another.
        // todo: cache the structure of arguments[0] for performance
        for (p in y) {
            if (y.hasOwnProperty(p) !== x.hasOwnProperty(p)) {
                return false;
            } else if (typeof y[p] !== typeof x[p]) {
                return false;
            }
        }

        for (p in x) {
            if (y.hasOwnProperty(p) !== x.hasOwnProperty(p)) {
                return false;
            } else if (typeof y[p] !== typeof x[p]) {
                return false;
            }

            switch (typeof (x[p])) {
                case 'object':
                case 'function':

                    leftChain.push(x);
                    rightChain.push(y);

                    if (!compare2Objects(x[p], y[p])) {
                        return false;
                    }

                    leftChain.pop();
                    rightChain.pop();
                    break;

                default:
                    if (x[p] !== y[p]) {
                        return false;
                    }
                    break;
            }
        }

        return true;
    }

    if (arguments.length < 1) {
        return true; //Die silently? Don't know how to handle such case, please help...
        // throw "Need two or more arguments to compare";
    }

    for (i = 1, l = arguments.length; i < l; i++) {

        leftChain = []; //Todo: this can be cached
        rightChain = [];

        if (!compare2Objects(arguments[0], arguments[i])) {
            return false;
        }
    }

    return true;
}

//isNaN(val)不能判断空串或一个空格
//如果是一个空串、空格或null，而isNaN是做为数字0进行处理的，而parseInt与parseFloat是返回一个错误消息，这个isNaN检查不严密而导致的。

//数组属性、Array 对象的方法
// constructor	返回创建数组对象的原型函数。
// length	设置或返回数组元素的个数。
// prototype	允许你向数组对象添加属性或方法
//一个元素是否在数组中
// concat()	连接两个或更多的数组，并返回结果。
// copyWithin()	从数组的指定位置拷贝元素到数组的另一个指定位置中。
// entries()	返回数组的可迭代对象。
// every()	检测数值元素的每个元素是否都符合条件。
// fill()	使用一个固定值来填充数组。
// filter()	检测数值元素，并返回符合条件所有元素的数组。
// find()	返回符合传入测试（函数）条件的数组元素。
// findIndex()	返回符合传入测试（函数）条件的数组元素索引。
// forEach()	数组每个元素都执行一次回调函数。
// from()	通过给定的对象中创建一个数组。
// includes()	判断一个数组是否包含一个指定的值。
// indexOf()	搜索数组中的元素，并返回它所在的位置。
// isArray()	判断对象是否为数组。
// join()	把数组的所有元素放入一个字符串。
// keys()	返回数组的可迭代对象，包含原始数组的键(key)。
// lastIndexOf()	搜索数组中的元素，并返回它最后出现的位置。
// map()	通过指定函数处理数组的每个元素，并返回处理后的数组。
// pop()	删除数组的最后一个元素并返回删除的元素。
// push()	向数组的末尾添加一个或更多元素，并返回新的长度。
// reduce()	将数组元素计算为一个值（从左到右）。
// reduceRight()	将数组元素计算为一个值（从右到左）。
// reverse()	反转数组的元素顺序。
// shift()	删除并返回数组的第一个元素。
// slice()	选取数组的的一部分，并返回一个新数组。
// some()	检测数组元素中是否有元素符合指定条件。
// sort()	对数组的元素进行排序。
// splice()	从数组中添加或删除元素。
// toString()	把数组转换为字符串，并返回结果。
// unshift()	向数组的开头添加一个或更多元素，并返回新的长度。
// valueOf()	返回数组对象的原始值。

//元素从数组中移除
function removeFromArray(array, value) {
    let newArray = [];
    for (let i = 0; i < array.length; i++) {
        if (value !== array[i]) {
            newArray.push(array[i])
        }
    }
    return newArray;
}

//一个对象是否在数组中，key是判断的标准
function objIsInArray(obj, array, key) {
    let isHave = false;
    for (let i = 0; i < array.length; i++) {
        if (array[i][key] == obj[key]) {
            isHave = true;
        }
    }
    return isHave
}

function isUserInList(user, userList) {
    return objIsInArray(user, userList, 'id')
}

//两个数组是否有交集
function haveIntersection(arrayOne, arrayTwo) {
    //item:当前元素的值；index:当前元素的索引；array:当前元素的数组对象；
    return arrayOne.some(function (item, index, array) {
        return arrayTwo.includes(item)
    });
}

function isSubset(subset, superset) {
    return subset.every(function (item, index, array) {
        return superset.includes(item)
    });
}

//百分比和小数转化
function numberToPercentage(num, fractionDigits = 2) {
    let percent = Number(num * 100).toFixed(fractionDigits) + "%";


    return percent;
}

function percentageToNumber(percent) {
    let num = percent.replace("%", "") / 100;
    return num;
}

//获取url参数
function getQueryString(name) {
    let reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)", "i");
    let r = window.location.search.substr(1).match(reg);
    if (r != null) return unescape(r[2]);
    return null;
}

//修改或添加url参数
function changeUrl(key, val) {
    let url = window.location.href;
    let pars = '';
    if (url.indexOf('?' >= 0)) {
        pars = url.split('?')[1]
    }
    let strs = [];
    if (pars && pars != '' && pars.indexOf('&') >= 0) {
        strs = pars.split('&')
    }
    if (pars && pars != '' && pars.indexOf('&') < 0) {
        strs = [pars]
    }
    let isExists = false;
    for (var i = 0; i < strs.length; i++) {
        if (strs[i].indexOf('=') >= 0 && strs[i].indexOf(key) >= 0 && strs[i].split('=')[0] == key) {
            var dqArr = strs[i].split('=');
            dqArr[1] = val;
            var dqStr = dqArr.join('=');
            strs[i] = dqStr;
            isExists = true
            break;
        }
    }
    let params = '';
    if (isExists) {

        params = strs.join('&');
    } else {
        if (pars && pars != '') {

            params = strs.join('&') + '&' + key + '=' + val;
        } else {

            params = key + '=' + val;
        }
    }
    return url.split('?')[0] + '?' + params
}

function getUUID(len, radix) {
    let chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'.split('');
    let uuid = [], i;
    radix = radix || chars.length;

    if (len) {
        for (i = 0; i < len; i++) uuid[i] = chars[0 | Math.random() * radix];
    } else {
        let r;
        uuid[8] = uuid[13] = uuid[18] = uuid[23] = '-';
        uuid[14] = '4';
        for (i = 0; i < 36; i++) {
            if (!uuid[i]) {
                r = 0 | Math.random() * 16;
                uuid[i] = chars[(i == 19) ? (r & 0x3) | 0x8 : r];
            }
        }
    }
    return uuid.join('');
}


function getDateArray(date_string) {
    let new_string = date_string.replace(/[^0-9:]/g, ' ').trim();
    let date_array = new_string.split(/\s+/g);
    let newArray = [parseInt(date_array[0]), parseInt(date_array[1]), parseInt(date_array[2])]
    if (date_array.length > 3) {
        newArray.push(date_array[3])
    }
    return newArray
}


function simpleDateStr(date_string, need_time = true) {
    if (isValidValue(date_string)) {
        let date_array = getDateArray(date_string);
        let result_str = [date_array[0], date_array[1], date_array[2]].join('.');
        if (need_time && date_array.length > 3) {
            result_str = result_str + ' ' + date_array[3]
        }
        return result_str
    } else {
        return ''
    }
}

function monthDayStr(date_string) {
    let date_array = getDateArray(date_string);
    let result_str = [date_array[1], date_array[2]].join('.');
    return result_str
}

function commonDateStr(date_string) {
    let date_array = getDateArray(date_string);
    let result_str = [date_array[0], date_array[1], date_array[2]].join('/');
    if (date_array.length > 3) {
        result_str = result_str + ' ' + date_array[3]
    }
    return result_str
}


function gearDate(date_string) {
    let newString = commonDateStr(date_string);
    return new Date(newString)
}

//根据日期（开始日期与结束日期）获取其中多有的年月（2018-04～2019-12）；
function getMounthSection(start, end) {
    let startMonth = moment(start).format('YYYY-MM');
    let endMonth = moment(end).format('YYYY-MM');

    let DateArr = [];
    if (moment(endMonth).diff(moment(startMonth), 'months') >= 0) {
        let lengths = moment(endMonth).diff(moment(startMonth), 'months');
        for (let i = 0; i < lengths + 1; i++) {
            let obj = getMonthCenter(moment(startMonth).add(i, 'months').format('YYYY-MM'));
            obj.yearMonth = moment(startMonth).add(i, 'months').format('YYYY-MM');
            let days = [];
            for (let j = 1; j <= obj.daysLength; j++) {
                days.push(j);
            }
            obj.days = days;
            DateArr.push(obj)
        }
    }
    return DateArr;
}

//根据年月返回该月的年与月与天数 getMonthCenter('2019-02');
function getMonthCenter(val) {
    let daysLength = moment(val).daysInMonth();
    let year = moment(val).get('year');
    let month = moment(val).get('month') + 1;
    if (month < 10) {
        month = '0' + month
    }
    return {
        year: year,
        month: month,
        daysLength: daysLength,
    };
}


// getWaitDuration('2019-10-11 13:11', '2019-10-11 14:59')
function getWaitDuration(start, end, dayNum = 1, zeroStr = "1分钟") {
    if (start && end && start != end) {
        let startTime = moment(start);
        let endTime = moment(end);
        if (startTime.isSame(end)) {
            return zeroStr
        }
        let waitTime = moment.duration(endTime - startTime, 'ms');
        let years = waitTime.get('years');
        let months = waitTime.get('months');
        let days = waitTime.get('days');
        let hours = waitTime.get('hours');
        let minutes = waitTime.get('minutes');


        let yearStr = years ? years + '年' : '';
        let monthsStr = months ? months + '个月' : '';
        let resultStr = yearStr + monthsStr;
        let daysStr = '';
        let hoursStr = '';
        let minutesStr = minutes != 0 ? minutes + '分钟' : '';

        if (days >= dayNum) {
            daysStr = days + '天';
            if (hours != 0) {
                hoursStr = hours + '小时';
            }
            minutesStr = '';
        } else {
            hoursStr = days * 24 + hours == 0 ? '' : days * 24 + hours + '小时';
        }
        if (!resultStr && !days && !hours && !minutes) {
            return zeroStr
        } else {
            yearStr || monthsStr ? hoursStr = minutesStr = '' : null;
            return resultStr = resultStr + daysStr + hoursStr + minutesStr
        }
        return resultStr
    }
    return zeroStr
}