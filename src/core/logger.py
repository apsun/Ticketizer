# -*- coding: utf-8 -*-
import datetime
import requests


class LogType:
    ERROR = "E"
    WARNING = "W"
    DEBUG = "D"


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
        curr_time = datetime.datetime.now().strftime("%H:%M:%S")
    else:
        curr_time = None
    print(fmt_str.format(log_type, curr_time, msg))


def log_convert_response(log_type, msg, response):
    # Automatically appends the status code of an HTTP request to the log, if applicable.
    if response is None:
        log(log_type, msg)
    elif isinstance(response, requests.Response):
        log(log_type, "{0} (status code: {1})".format(msg, response.status_code))
    else:
        assert False
    

def error(msg, response=None):
    log_convert_response(LogType.ERROR, msg, response)

    
def warning(msg, response=None):
    log_convert_response(LogType.WARNING, msg, response)

    
def debug(msg, response=None):
    log_convert_response(LogType.DEBUG, msg, response)