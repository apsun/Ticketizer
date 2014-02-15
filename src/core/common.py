# -*- coding: utf-8 -*-
import datetime
import urllib.parse
import itertools
from core.errors import InvalidRequestError


def read_json_data(response):
    json = read_json(response)
    json_data = json.get("data")
    if json_data is None:
        raise InvalidRequestError(json.get("messages"))
    return json_data


def islice(iterable, start=None, end=None, step=None):
    # For some reason PyCharm thinks islice's constructor
    # has the signature __init__(iterable, end). This avoids
    # a warning every time you use itertools.islice.
    # noinspection PyArgumentList
    return itertools.islice(iterable, start, end, step)


def get_ordered_query_params(*args):
    # This function only exists because 12306 is retarded.
    keys = islice(args, start=0, step=2)
    values = islice(args, start=1, step=2)
    # urlencode properly handles special characters, even
    # through there probably won't be any...
    return urllib.parse.urlencode(list(zip(keys, values)))
    # return "&".join("%s=%s" % pair for pair in zip(keys, values))


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
        raise InvalidRequestError("Invalid query, check your parameters")
    return response.json()


def datetime_to_str(datetime_obj, fmt="%Y-%m-%d %H:%M"):
    return datetime_obj.strftime(fmt)


def str_to_datetime(date, time, date_fmt="%Y-%m-%d", time_fmt="%H:%M"):
    # Allows date and time parameters to be date and time objects respectively,
    # meaning you can use this method to "concatenate" date and time objects.
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, date_fmt).date()
    if isinstance(time, str):
        time = datetime.datetime.strptime(time, time_fmt).time()
    return datetime.datetime.combine(date, time)


def date_to_str(date_obj, fmt="%Y-%m-%d"):
    return date_obj.strftime(fmt)


def str_to_date(date_str, fmt="%Y-%m-%d"):
    return datetime.datetime.strptime(date_str, fmt).date()


def time_to_str(time_obj, fmt="%H:%M"):
    return time_obj.strftime(fmt)


def str_to_time(time_str, fmt="%H:%M"):
    return datetime.datetime.strptime(time_str, fmt).time()


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
    if value is True:
        return True
    if value == "Y":
        return True
    return False