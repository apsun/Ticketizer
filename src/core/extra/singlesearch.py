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
import re
from core import webrequest, timeconverter
from core.auth.authable import Authable


class SingleTrainQuery(Authable):
    __data__ = None

    def __init__(self, cookies):
        super(SingleTrainQuery, self).__init__(cookies, "login")
        self.date = None
        self.train_name = None

    @classmethod
    def load_list(cls, local_path=None):
        if local_path is None:
            url = "https://kyfw.12306.cn/otn/resources/js/query/train_list.js"
            response = webrequest.get(url)
            text = response.text
        else:
            with open(local_path, "rt", encoding="utf-8") as f:
                text = f.read()

        # Remove var keyword
        assert text.startswith("var ")
        text = text[4:]

        # Execute the JS as Python code
        variables = {}
        exec(text, variables)

        # Load the train data
        date_map = {}
        for train_date_str, type_map in variables["train_list"].items():
            train_date = timeconverter.str_to_date(train_date_str)
            train_map = {}
            for train_type, train_list in type_map.items():
                for train_obj in train_list:
                    train_id = train_obj["train_no"]
                    train_name = train_obj["station_train_code"]
                    train_name = re.match("(.+)\(.*-.*\)", train_name).group(1)
                    train_map[train_name] = train_id
            date_map[train_date] = train_map

        cls.__data__ = date_map

    def __get_query_params(self):
        return [
            ("leftTicketDTO.train_no", self.__data__[self.date][self.train_name]),
            ("leftTicketDTO.train_date", timeconverter.date_to_str(self.date)),
            ("rand_code", self.captcha.answer)
        ]

    @Authable.consumes_captcha()
    def execute(self):
        if self.__data__ is None:
            self.load_list()
        url = "https://kyfw.12306.cn/otn/queryTrainInfo/query"
        params = self.__get_query_params()
        json = webrequest.get_json(url, params=params, cookies=self.cookies)
        # TODO: Complete
