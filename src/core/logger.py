# -*- coding: utf-8 -*-
from datetime import datetime


class LogType:
    DEBUG = 1
    NETWORK = 2
    WARNING = 4
    ERROR = 8

    NAME_LOOKUP = {
        DEBUG: "D",
        NETWORK: "N",
        WARNING: "W",
        ERROR: "E"
    }


def log(log_type, msg):
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