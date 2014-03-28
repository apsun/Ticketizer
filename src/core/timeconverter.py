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