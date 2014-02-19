# -*- coding: utf-8 -*-
import requests
import urllib.parse
from core.auth.cookies import SessionCookies
from core.errors import InvalidRequestError
from core import common, logger


def request(method, url, params=None, data=None, cookies=None):
    def log_request():
        def dict_to_str(obj):
            if isinstance(obj, dict):
                iterable = obj.items()
            else:
                iterable = obj
            return "".join(map(lambda x: "\n   -> {0}: {1}".format(*x), iterable))
        log_values = ["[{0}] {1}".format(method.upper(), url)]
        # noinspection PyTypeChecker
        if params is not None and len(params) > 0:
            log_values.append(" -> Params:" + dict_to_str(params))
        if data is not None and len(data) > 0:
            log_values.append(" -> Data:" + dict_to_str(data))
        if cookies is not None and len(cookies) > 0:
            log_values.append(" -> Cookies:" + dict_to_str(cookies))
        logger.network("\n".join(log_values))

    log_request()
    if isinstance(params, list):
        url += "?" + urllib.parse.urlencode(params)
        params = None
    response = requests.request(method, url, params=params, cookies=cookies, data=data, verify=False)
    response.raise_for_status()
    if isinstance(cookies, SessionCookies):
        cookies.update_cookies(response)
    return response


def get(url, params=None, data=None, cookies=None):
    return request("get", url, params=params, data=data, cookies=cookies)


def post(url, params=None, data=None, cookies=None):
    return request("post", url, params=params, data=data, cookies=cookies)


def get_json(url, params=None, data=None, cookies=None):
    return read_json(get(url, params=params, data=data, cookies=cookies))


def post_json(url, params=None, data=None, cookies=None):
    return read_json(post(url, params=params, data=data, cookies=cookies))


def read_json(response):
    if response.text == "-1":  # For 12306, "-1" means invalid query
        raise InvalidRequestError("Invalid query parameters, has the 12306 API changed?")
    json = response.json()
    if json.get("status") is not True:
        raise InvalidRequestError(common.join_list(json.get("messages")))
    return json


def check_json_flag(json, *path, custom_bool=True, exception=None):
    value = common.get_dict_value_coalesce(json, *path)
    if custom_bool:
        status = common.is_true(value)
    else:
        status = value is True
    if not status:
        if exception is None:
            exception = InvalidRequestError
        raise exception(common.join_list(json.get("messages")))
    return json