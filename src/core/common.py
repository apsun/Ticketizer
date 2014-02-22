# -*- coding: utf-8 -*-
#
# This file is part of Ticketizer.
# Copyright (c) 2014 Andrew Sun <youlosethegame@live.com>
#
# Ticketizer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ticketizer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ticketizer.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from itertools import islice


def between(string, start, end):
    begin = string.index(start) + len(start)
    end = string.index(end)
    return string[begin:end]


def slice_list(iterable, start=None, end=None, step=None):
    # If you REALLY like your negative end indices,
    # you can have them (only if you can natively call
    # len() on the iterable)
    if end is not None and end < 0:
        end %= len(iterable)
    # For some reason PyCharm thinks islice's constructor
    # has the signature __init__(iterable, end). This avoids
    # a warning every time you use itertools.islice.
    # noinspection PyArgumentList
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
        if value == "Y" or value == "true":
            return True
        if value == "N" or value == "false":
            return False
    return False
    # raise ValueError("Unknown boolean value: " + str(value))


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