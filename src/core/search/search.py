# -*- coding: utf-8 -*-
import requests
from core.data.train import Train
from core import logger, common


class TicketPricing:
    NORMAL = "ADULT"
    STUDENT = "0X00"


class TicketDirection:
    ONE_WAY = "dc"
    ROUND_TRIP = "fc"


class TrainQuery:
    def __init__(self, station_list):
        # Station list, required for train initialization
        self.station_list = station_list
        # The type of ticket pricing -- normal ("adult") or student
        self.pricing = TicketPricing.NORMAL
        # The trip type -- one-direction or round-trip
        self.direction = TicketDirection.ONE_WAY
        # The departure date -- datetime.date (or a str in the format YYYY-mm-dd)
        self.date = None
        # The departure station -- data.Station (or use the station ID)
        self.departure_station = None
        # The destination station -- data.Station (or use the station ID)
        self.destination_station = None
        # Optionally disable the "fuzzy station search" feature
        self.exact_departure_station = False
        self.exact_destination_station = False

    def __ensure_param_types(self):
        if isinstance(self.date, str):
            self.date = common.str_to_date(self.date)
            logger.warning("Using date string instead of object")
        if isinstance(self.departure_station, str):
            self.departure_station = self.station_list.get_by_id(self.departure_station)
            logger.warning("Using departure station ID instead of object")
        if isinstance(self.destination_station, str):
            self.destination_station = self.station_list.get_by_id(self.destination_station)
            logger.warning("Using destination station ID instead of object")

    def __get_query_string(self):
        return common.get_ordered_query_params(
            "leftTicketDTO.train_date", common.date_to_str(self.date),
            "leftTicketDTO.from_station", self.departure_station.id,
            "leftTicketDTO.to_station", self.destination_station.id,
            "purpose_codes", self.pricing)

    def execute(self):
        self.__ensure_param_types()
        url = "https://kyfw.12306.cn/otn/leftTicket/query?" + self.__get_query_string()
        response = requests.get(url, verify=False)
        response.raise_for_status()
        json_data = common.read_json_data(response)
        logger.debug("Got ticket list from {0} to {1} on {2}".format(
            self.departure_station.name,
            self.destination_station.name,
            common.date_to_str(self.date)
        ), response)
        train_list = []
        for train_data in json_data:
            combined_data = common.flatten_dict(train_data)
            departure_station = self.station_list.get_by_id(combined_data["from_station_telecode"])
            destination_station = self.station_list.get_by_id(combined_data["to_station_telecode"])
            if self.exact_departure_station and departure_station != self.departure_station:
                continue
            if self.exact_destination_station and destination_station != self.destination_station:
                continue
            train_list.append(Train(combined_data, departure_station, destination_station))
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