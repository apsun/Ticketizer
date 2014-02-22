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

import requests
import urllib.parse
from core import common, logger
from core.auth.cookies import SessionCookies
from core.errors import InvalidRequestError


def request(method, url, **kwargs):
    def log_request():
        def dict_to_str(obj):
            if isinstance(obj, dict):
                iterable = obj.items()
            else:
                iterable = obj
            return "".join(map(lambda x: "\n   -> {0}: {1}".format(*x), iterable))

        log_values = ["[{0}] {1}".format(method.upper(), url)]
        for arg, value in kwargs.items():
            if value is None:
                continue
            try:
                if len(value) == 0:
                    continue
                value = dict_to_str(value)
            except TypeError:
                pass
            log_values.append(" -> {0}: {1}".format(arg, value))
        logger.network("\n".join(log_values))

    log_request()
    params = kwargs.get("params")
    if isinstance(params, list):
        url += "?" + urllib.parse.urlencode(params)
        kwargs["params"] = None
    response = requests.request(method, url, verify=False, **kwargs)
    response.raise_for_status()
    cookies = kwargs.get("cookies")
    if isinstance(cookies, SessionCookies):
        cookies.update_cookies(response)
    return response


def get(url, **kwargs):
    return request("get", url, **kwargs)


def post(url, **kwargs):
    return request("post", url, **kwargs)


def get_json(url, **kwargs):
    return read_json(get(url, **kwargs))


def post_json(url, **kwargs):
    return read_json(post(url, **kwargs))


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