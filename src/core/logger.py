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


class LogType:
    NONE = 0
    DEBUG = 1
    NETWORK = 2
    WARNING = 4
    ERROR = 8
    ALL = 15

    NAME_LOOKUP = {
        DEBUG: "D",
        NETWORK: "N",
        WARNING: "W",
        ERROR: "E"
    }

# Optionally switch off some log types for
# reduced log output verbosity
__enabled_log_types = LogType.ALL


def get_type_enabled(log_type):
    return (__enabled_log_types & log_type) == log_type


def set_type_enabled(log_type, enabled):
    global __enabled_log_types
    if enabled:
        __enabled_log_types |= log_type
    else:
        __enabled_log_types &= ~log_type


def log(log_type, msg):
    if not get_type_enabled(log_type):
        return

    # Whether to print the log verbosity
    enable_type = True
    # Whether to print the current time
    enable_time = True
    
    if enable_type and enable_time:
        fmt_str = "[{0}][{1}] {2}"
    elif enable_type:
        fmt_str = "[{0}] {2}"
    elif enable_time:
        fmt_str = "[{1}] {2}"
    else:
        fmt_str = "{2}"
    
    if enable_time:
        curr_time = datetime.now().strftime("%H:%M:%S")
    else:
        curr_time = None
    print(fmt_str.format(LogType.NAME_LOOKUP[log_type], curr_time, msg))


def error(msg):
    log(LogType.ERROR, msg)

    
def warning(msg):
    log(LogType.WARNING, msg)


def network(msg):
    log(LogType.NETWORK, msg)


def debug(msg):
    log(LogType.DEBUG, msg)