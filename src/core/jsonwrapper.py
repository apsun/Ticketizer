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


class RequestError(Exception):
    def __init__(self, msg, json, response):
        super(RequestError, self).__init__(msg, json, response)


class JsonList(list):
    def __init__(self, json_list, parent):
        super(JsonList, self).__init__()
        self.parent = parent
        for item in json_list:
            if isinstance(item, dict):
                self.append(JsonDict(item, self))
            elif isinstance(item, list):
                self.append(JsonList(item, self))
            else:
                self.append(item)


class JsonDict(dict):
    def __init__(self, json_dict, parent):
        super(JsonDict, self).__init__()
        self.parent = parent
        for k, v in json_dict.items():
            if isinstance(v, dict):
                self[k] = JsonDict(v, self)
            elif isinstance(v, list):
                self[k] = JsonList(v, self)
            else:
                self[k] = v

    def __getitem__(self, item):
        value = self.get(item)
        if value is None:
            self.raise_error()
        return value

    def raise_error(self):
        base = self
        while base.parent is not None:
            base = base.parent
        assert isinstance(base, (RootJsonList, RootJsonDict))
        messages = base.get("messages")
        if messages is None or len(messages) == 0:
            raise RequestError("Unknown error occured", base, base.response)
        elif len(messages) == 1:
            raise RequestError(messages[0], base, base.response)
        else:
            raise RequestError(messages, base, base.response)

    def get_bool(self, item):
        value = self[item]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value == "Y" or value == "true":
                return True
            if value == "N" or value == "false":
                return False
        return False

    def assert_true(self, item):
        if not self.get_bool(item):
            self.raise_error()


class RootJsonList(JsonList):
    def __init__(self, json_list, response):
        super(RootJsonList, self).__init__(json_list, None)
        self.response = response


class RootJsonDict(JsonDict):
    def __init__(self, json_dict, response, check_status=True):
        super(RootJsonDict, self).__init__(json_dict, None)
        self.response = response
        if check_status and not self.get("status"):
            self.raise_error()


def read(response, check_status=True):
    if response.text == "-1":
        raise RequestError("Invalid request parameters, did the 12306 API change?", None, response)
    json = response.json()
    if isinstance(json, dict):
        return RootJsonDict(json, response, check_status)
    if isinstance(json, list):
        return RootJsonList(json, response)