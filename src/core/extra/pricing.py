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
from core import timeconverter, webrequest
from core.auth.authable import Authable


class PriceQuery(Authable):
    def __init__(self, cookies):
        super(PriceQuery, self).__init__(cookies, "login")
        self.departure_station = None
        self.destination_station = None
        self.date = None

    def __get_query_params(self):
        return [
            ("leftTicketDTO.train_date", timeconverter.date_to_str(self.date)),
            ("leftTicketDTO.from_station", self.departure_station.id),
            ("leftTicketDTO.to_station", self.destination_station.id),
            ("purpose_codes", "ADULT"),
            ("randCode", self.captcha.answer)
        ]

    @Authable.consumes_captcha()
    def execute(self):
        url = "https://kyfw.12306.cn/otn/leftTicketPrice/query"
        params = self.__get_query_params()
        json = webrequest.get_json(url, params=params, cookies=self.cookies)
        # TODO: Complete