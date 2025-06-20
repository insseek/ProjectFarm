# -*- coding:utf-8 -*-
import re
import datetime


def change_huawei_fee_info_case_and_set_time_filed(data: dict):
    new_data = {}
    for key in data.keys():
        new_key = lower_camel_case_to_under_score_case(key)
        value = data[key]
        if new_key.endswith('time') and data[key]:
            time_str = data[key]
            value = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=8)
        new_data[new_key] = value
    return new_data


def change_camel_case_data_to_under_score_case_data(data: dict):
    new_data = {}
    for key in data.keys():
        new_key = lower_camel_case_to_under_score_case(key)
        new_data[new_key] = data[key]
    return new_data


def lower_camel_case_to_under_score_case(original_string):
    pattern = "[A-Z]"
    new_string = re.sub(pattern, lambda x: "_" + x.group(0), original_string).lower()
    return new_string


def get_valid_china_phone_number(number):
    if isinstance(number, str):
        number = '+86' + number if not number.startswith('+86') else number
    return number
