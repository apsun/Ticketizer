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
import urllib.parse as urllib
from core import logger, jsonwrapper
from core.auth.cookies import SessionCookies


def request(method, url, **kwargs):
    log_network(method, url, **kwargs)
    params = kwargs.get("params")
    if isinstance(params, list):
        url += "?" + urllib.urlencode(params)
        kwargs["params"] = None
    response = requests.request(method, url, verify=False, **kwargs)
    response.raise_for_status()
    cookies = kwargs.get("cookies")
    if isinstance(cookies, SessionCookies):
        cookies.update_cookies(response)
    return response


def log_network(method, url, **kwargs):
    log_values = ["[{0}] {1}".format(method.upper(), url)]
    for arg, value in kwargs.items():
        if value is None:
            continue
        try:
            if len(value) == 0:
                continue
            if isinstance(value, dict):
                value = value.items()
            value = "".join(map(lambda x: "\n   -> {0}: {1}".format(*x), value))
        except TypeError:
            pass
        log_values.append(" -> {0}: {1}".format(arg, value))
    logger.network("\n".join(log_values))


def get(url, **kwargs):
    return request("get", url, **kwargs)


def post(url, **kwargs):
    return request("post", url, **kwargs)


def get_json(url, **kwargs):
    return jsonwrapper.read(get(url, **kwargs))


def post_json(url, **kwargs):
    return jsonwrapper.read(post(url, **kwargs))