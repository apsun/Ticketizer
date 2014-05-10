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

enabled_log_types = LogType.ALL
print_log_type = True
print_log_time = False

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


def log(log_type, msg, *args, **kwargs):
    if (enabled_log_types & log_type) != log_type:
        return

    # Generate log header
    header = ""
    if print_log_type:
        header += "[" + LogType.NAME_LOOKUP[log_type] + "]"
    if print_log_time:
        header += "[" + datetime.now().strftime("%H:%M:%S") + "]"

    # Lazy evaluate log message for performance reasons
    if callable(msg):
        msg = msg()

    set_color(log_type)
    write(log_type, header + " " + msg.format(*args, **kwargs))
    reset_color(log_type)


def error(msg, *args, **kwargs):
    log(LogType.ERROR, msg, *args, **kwargs)

    
def warning(msg, *args, **kwargs):
    log(LogType.WARNING, msg, *args, **kwargs)


def network(msg, *args, **kwargs):
    log(LogType.NETWORK, msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    log(LogType.DEBUG, msg, *args, **kwargs)