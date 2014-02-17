# -*- coding: utf-8 -*-
from datetime import datetime
from itertools import islice
from core.errors import InvalidRequestError


def read_json_data(response):
    json = read_json(response)
    json_data = json.get("data")
    if json_data is None:
        raise InvalidRequestError(join_list(json.get("messages")))
    return json_data


def between(string, start, end):
    begin = string.index(start) + len(start)
    end = string.index(end)
    return string[begin:end]


def slice_list(iterable, start=None, end=None, step=None):
    # If you REALLY like your negative end indices,
    # you can have them (only if you can natively call
    # len() on the iterable)
    if end is not None and end < 0:
        try:
            end %= len(iterable)
        except TypeError:
            pass
    # For some reason PyCharm thinks islice's constructor
    # has the signature __init__(iterable, end). This avoids
    # a warning every time you use itertools.islice.
    return islice(iterable, start, end, step)


def get_dict_value_coalesce(value, *keys):
    # If the dictionary is None, coalesce the result to None
    if value is None:
        return None
    # If there are no more keys to check, return the current result
    if len(keys) == 0:
        return value
    # Pop first key from the list, using that as the next dictionary key
    key, *keys = keys
    return get_dict_value_coalesce(value.get(key), *keys)


def flatten_dict(value):
    combined = {}
    for k, v in value.items():
        if isinstance(v, dict):
            combined.update(flatten_dict(v))
        else:
            combined[k] = v
    return combined


def read_json(response):
    if response.text == "-1":  # For 12306, "-1" means invalid query
        raise InvalidRequestError("Invalid query parameters, has the 12306 API changed?")
    json = response.json()
    if json.get("status") is not True:
        raise InvalidRequestError(join_list(json.get("messages")))
    return json


def datetime_to_str(datetime_obj, fmt="%Y-%m-%d %H:%M"):
    return datetime_obj.strftime(fmt)


def str_to_datetime(date_value, time_value, date_fmt="%Y-%m-%d", time_fmt="%H:%M"):
    # Allows date and time parameters to be date and time objects respectively,
    # meaning you can use this method to "concatenate" date and time objects.
    if isinstance(date_value, str):
        date_value = datetime.strptime(date_value, date_fmt).date()
    if isinstance(time_value, str):
        time_value = datetime.strptime(time_value, time_fmt).time()
    return datetime.combine(date_value, time_value)


def date_to_str(date_obj, fmt="%Y-%m-%d"):
    return date_obj.strftime(fmt)


def str_to_date(date_str, fmt="%Y-%m-%d"):
    return datetime.strptime(date_str, fmt).date()


def time_to_str(time_obj, fmt="%H:%M"):
    return time_obj.strftime(fmt)


def str_to_time(time_str, fmt="%H:%M"):
    return datetime.strptime(time_str, fmt).time()


def timedelta_to_str(timedelta_obj, force_seconds=False):
    minutes, seconds = divmod(timedelta_obj.total_seconds(), 60)
    hours, minutes = divmod(minutes, 60)
    hours = int(hours)
    minutes = int(minutes)
    seconds = int(seconds)
    fmt = "{0:02d}:{1:02d}"
    if force_seconds or seconds != 0:
        fmt += "{2:02d}"
    return fmt.format(hours, minutes, seconds)


def is_true(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value == "Y":
            return True
        if value == "N":
            return False
    raise ValueError("Unknown boolean string format")


def join_list(value, separator="; "):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        if len(value) == 0:
            return None
        return separator.join(value)
    raise ValueError("Argument is not a list or string")