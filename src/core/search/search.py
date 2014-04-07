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

from core import logger, timeconverter, webrequest
from core.enums import TicketPricing, TicketDirection
from core.jsonwrapper import RequestError
from core.data.train import Train


class SearchFailedError(Exception):
    pass


class DateOutOfRangeError(SearchFailedError):
    pass


class TrainQuery:
    def __init__(self, station_list):
        # Station list, required for train initialization
        self.__station_list = station_list
        # The type of ticket pricing -- normal ("adult") or student
        self.pricing = TicketPricing.NORMAL
        # The trip type -- one-direction or round-trip
        self.direction = TicketDirection.ONE_WAY
        # The departure date -- datetime.date
        self.date = None
        # The departure station -- data.Station
        self.departure_station = None
        # The destination station -- data.Station
        self.destination_station = None
        # Optionally disable the "fuzzy station search" feature
        self.exact_departure_station = False
        self.exact_destination_station = False

    def __get_query_params(self):
        return [
            ("leftTicketDTO.train_date", timeconverter.date_to_str(self.date)),
            ("leftTicketDTO.from_station", self.departure_station.id),
            ("leftTicketDTO.to_station", self.destination_station.id),
            ("purpose_codes", TicketPricing.SEARCH_LOOKUP[self.pricing])
        ]

    def execute(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/query"
        params = self.__get_query_params()
        json = webrequest.get_json(url, params=params)
        try:
            json_data = json["data"]
        except RequestError as ex:
            if ex.args[0] == "选择的查询日期不在预售日期范围内":
                raise DateOutOfRangeError() from ex
            raise
        logger.debug("Got train list from {0} to {1} on {2}".format(
            self.departure_station.name,
            self.destination_station.name,
            timeconverter.date_to_str(self.date)))
        train_list = []
        for train_data in json_data:
            query_data = train_data["queryLeftNewDTO"]
            departure_station = self.__station_list.get_by_id(query_data["from_station_telecode"])
            destination_station = self.__station_list.get_by_id(query_data["to_station_telecode"])
            if self.exact_departure_station and departure_station != self.departure_station:
                continue
            if self.exact_destination_station and destination_station != self.destination_station:
                continue
            train = Train(train_data, departure_station, destination_station,
                          self.pricing, self.direction, self.date)
            train_list.append(train)
        return train_list