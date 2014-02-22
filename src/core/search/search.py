# -*- coding: utf-8 -*-
from core import logger, common, webrequest
from core.enums import TicketPricing, TicketDirection
from core.data.train import Train


class TrainQuery:
    def __init__(self, station_list):
        # Station list, required for train initialization
        self.__station_list = station_list
        # The type of ticket pricing -- normal ("adult") or student
        self.pricing = TicketPricing.NORMAL
        # The trip type -- one-direction or round-trip
        self.direction = TicketDirection.ONE_WAY
        # The departure date -- datetime.date (or a str in the format YYYY-mm-dd)
        self.date = None
        # The departure station -- data.Station (or use the station ID/name/pinyin)
        self.departure_station = None
        # The destination station -- data.Station (or use the station ID/name/pinyin)
        self.destination_station = None
        # Optionally disable the "fuzzy station search" feature
        self.exact_departure_station = False
        self.exact_destination_station = False

    def __get_query_string(self):
        return [
            ("leftTicketDTO.train_date", common.date_to_str(self.date)),
            ("leftTicketDTO.from_station", self.departure_station.id),
            ("leftTicketDTO.to_station", self.destination_station.id),
            ("purpose_codes", TicketPricing.SEARCH_LOOKUP[self.pricing])
        ]

    def execute(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/query"
        params = self.__get_query_string()
        json_data = webrequest.get_json(url, params=params)["data"]
        logger.debug("Got ticket list from {0} to {1} on {2}".format(
            self.departure_station.name,
            self.destination_station.name,
            common.date_to_str(self.date)))
        train_list = []
        for train_data in json_data:
            raw_data = common.flatten_dict(train_data)
            departure_station = self.__station_list.get_by_id(raw_data["from_station_telecode"])
            destination_station = self.__station_list.get_by_id(raw_data["to_station_telecode"])
            if self.exact_departure_station and departure_station != self.departure_station:
                continue
            if self.exact_destination_station and destination_station != self.destination_station:
                continue
            train = Train(raw_data, departure_station, destination_station,
                          self.pricing, self.direction, self.date)
            train_list.append(train)
        return train_list


class TicketSearcher:
    def __init__(self):
        self.query = None
        self.filter = None
        self.sorter = None

    def filter_by_train(self, train_list):
        if self.filter is not None:
            return self.filter.filter(train_list)
        else:
            return train_list

    def sort_trains(self, train_list):
        if self.sorter is not None:
            self.sorter.sort(train_list)

    def get_train_list(self):
        train_list = self.query.execute()
        train_list = self.filter_by_train(train_list)
        self.sort_trains(train_list)
        return train_list