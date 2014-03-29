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
import os
import sys


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

    REVERSE_NAME_LOOKUP = {
        "D": DEBUG,
        "N": NETWORK,
        "W": WARNING,
        "E": ERROR
    }

# Setup color and stuff
enabled_log_types = LogType.ALL

__colors = {
    LogType.NONE: lambda s: None,
    LogType.DEBUG: lambda s: None,
    LogType.NETWORK: lambda s: None,
    LogType.WARNING: lambda s: None,
    LogType.ERROR: lambda s: None
}

__streams = {
    LogType.DEBUG: sys.stdout,
    LogType.NETWORK: sys.stdout,
    LogType.WARNING: sys.stdout,
    LogType.ERROR: sys.stderr
}


if hasattr(sys.stderr, "isatty") and sys.stdout.isatty():
    if os.name == "nt":
        import ctypes
        SetConsoleTextAttribute = ctypes.windll.kernel32.SetConsoleTextAttribute
        GetStdHandle = ctypes.windll.kernel32.GetStdHandle
        color = lambda s: SetConsoleTextAttribute(GetStdHandle(-11), s)
        __colors[LogType.DEBUG] = lambda s: color(0x02)
        __colors[LogType.NETWORK] = lambda s: color(0x05)
        __colors[LogType.WARNING] = lambda s: color(0x06)
        __colors[LogType.ERROR] = lambda s: color(0x04)
        __colors[LogType.NONE] = lambda s: color(0x07)
    elif os.name == "posix":
        __colors[LogType.DEBUG] = lambda s: s.write("\033[32m")
        __colors[LogType.NETWORK] = lambda s: s.write("\033[35m")
        __colors[LogType.WARNING] = lambda s: s.write("\033[33m")
        __colors[LogType.ERROR] = lambda s: s.write("\033[31m")
        __colors[LogType.NONE] = lambda s: s.write("\033[0m")


def set_color(log_type):
    __colors[log_type](__streams[log_type])


def reset_color(log_type):
    __colors[LogType.NONE](__streams[log_type])


def write(log_type, msg):
    __streams[log_type].write(msg + os.linesep)


def log(log_type, msg):
    if (enabled_log_types & log_type) != log_type:
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

    set_color(log_type)
    write(log_type, fmt_str.format(LogType.NAME_LOOKUP[log_type], curr_time, msg))
    reset_color(log_type)


def error(msg):
    log(LogType.ERROR, msg)

    
def warning(msg):
    log(LogType.WARNING, msg)


def network(msg):
    log(LogType.NETWORK, msg)


def debug(msg):
    log(LogType.DEBUG, msg)