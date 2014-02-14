# -*- coding: utf-8 -*-
import requests
from core import logger, common


class Station:
    def __init__(self, data_list):
        # Format of each entry is as follows:
        # bjb|北京北|VAP|beijingbei|bjb|0
        # 0 -> defines alphabetical order, pretty useless
        # 1 -> user-friendly name
        # 2 -> station ID
        # 3 -> name in pinyin
        # 4 -> name in pinyin (abbreviated to first characters)
        # 5 -> station number (0-indexed)
        assert len(data_list) == 6
        self.name = data_list[1]
        self.id = data_list[2]
        self.pinyin = data_list[3]
        self.pinyin_abbreviated = data_list[4]

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return self.name + " (ID: " + self.id + ")"


class StationList:
    def __init__(self, use_dict=True):
        self.stations = self.__get_all_stations()
        # We can get better lookup performance at the
        # cost of higher memory usage. Choose wisely.
        if use_dict:
            self.name_lookup = self.__generate_name_dict(self.stations)
            self.id_lookup = self.__generate_id_dict(self.stations)
        else:
            self.name_lookup = None
            self.id_lookup = None

    @staticmethod
    def __get_all_stations():
        url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
        response = requests.get(url, verify=False)
        response.raise_for_status()
        js_split = response.text.split("'")
        assert len(js_split) == 3
        station_split = js_split[1].split("@")
        station_data_list = common.islice(station_split, start=1)
        logger.debug("Fetched station list (" + str(len(station_split)-1) + " stations)", response)
        return [Station(item.split("|")) for item in station_data_list]

    @staticmethod
    def __generate_name_dict(station_list):
        return {station_list[i].name: i for i in range(len(station_list))}

    @staticmethod
    def __generate_id_dict(station_list):
        return {station_list[i].id: i for i in range(len(station_list))}

    def get_by_name(self, station_name):
        if self.name_lookup is None:
            for station in self.stations:
                if station.name == station_name:
                    return station
            raise KeyError()
        else:
            return self.stations[self.name_lookup[station_name]]

    def get_by_id(self, station_id):
        if self.id_lookup is None:
            for station in self.stations:
                if station.id == station_id:
                    return station
            raise KeyError()
        else:
            return self.stations[self.id_lookup[station_id]]

    def __iter__(self):
        for station in self.stations:
            yield station

    def __len__(self):
        return len(self.stations)