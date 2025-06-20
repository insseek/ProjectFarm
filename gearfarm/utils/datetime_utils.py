from datetime import timedelta
from dateutil import rrule
from copy import deepcopy

def get_current_day_prev_week_workday_end(current_day):
    prev_week_workday_end = current_day - timedelta(days=current_day.weekday() + 3)
    return prev_week_workday_end


def get_current_day_next_week_start(current_day):
    next_week_start = (current_day + timedelta(days=7 - current_day.weekday()))
    return next_week_start


def get_current_day_current_week_end(current_day):
    current_week_end = (current_day + timedelta(days=6 - current_day.weekday()))
    return current_week_end


# 下一个工作日
def next_workday(start_date, include_start_date=False):
    if include_start_date and is_workday(start_date):
        return start_date
    return get_date_by_timedelta_days(start_date, 1, only_workday=True)


# 获取一个日期 延期后的日期
def get_date_by_timedelta_days(start_date, days_count, only_workday=False):
    if only_workday:
        business_days_to_add = days_count
        current_date = start_date
        while business_days_to_add > 0:
            current_date += timedelta(days=1)
            weekday = current_date.weekday()
            if weekday >= 5:  # sunday = 6
                continue
            business_days_to_add -= 1
        return current_date
    else:
        result_date = start_date + timedelta(days=days_count)
    return result_date


# 获取两个日期之前的天数   包含起始结束日期
def get_days_count_between_date(start_date, end_date, only_workday=False):
    if only_workday:
        days_count = workdays(start_date, end_date)
    else:
        days_count = (end_date - start_date).days + 1
    return days_count


def is_workday(date):
    if date.weekday() in [5, 6]:
        return False
    return True


def workdays(start, end, holidays=0, days_off=None):
    if days_off is None:
        days_off = 5, 6
    workday_list = [x for x in range(7) if x not in days_off]
    days = rrule.rrule(rrule.DAILY, dtstart=start, until=end, byweekday=workday_list)
    return days.count() - holidays


def get_date_list(start_date, end_date):
    """
    获取开始结束日期列表
    :param start_date: 开始日期
    :param end_date: 结束日期
    :return:
    """
    data = []
    current_date = start_date
    while current_date <= end_date:
        data.append(deepcopy(current_date))
        current_date = current_date + timedelta(days=1)
    return data
