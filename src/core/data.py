# -*- coding: utf-8 -*-
import requests
import logger


class TrainType:
    G = 1       # 高铁
    D = 2       # 动车
    Z = 4       # 直达
    T = 8       # 特快
    K = 16      # 快速
    OTHER = 32  # 其他
    ALL = 63


class TicketType:
    OTHER = 1              # 其他
    NO_SEAT = 2            # 无座
    HARD_SEAT = 4          # 硬座
    SOFT_SEAT = 8          # 软座
    HARD_SLEEPER = 16      # 硬卧
    SOFT_SLEEPER = 32      # 软卧
    SOFT_SLEEPER_PRO = 64  # 高级软卧
    SECOND_CLASS = 128     # 二等座
    FIRST_CLASS = 256      # 一等座
    SPECIAL = 512          # 特等座
    BUSINESS = 1024        # 商务座
    ALL = 2047


class TicketId:
    OTHER = ""              # 其他
    NO_SEAT = "W"            # 无座
    HARD_SEAT = "1"          # 硬座
    SOFT_SEAT = "2"          # 软座
    HARD_SLEEPER = "3"      # 硬卧
    SOFT_SLEEPER = "4"      # 软卧
    SOFT_SLEEPER_PRO = "6"  # 高级软卧
    SECOND_CLASS = "O"     # 二等座
    FIRST_CLASS = "M"      # 一等座
    SPECIAL = "P"          # 特等座
    BUSINESS = "9"        # 商务座


class Train:

    def __init__(self):
        # The unique identifier of the train (e.g. T546)
        self.name = None
        # The type of the train (from TrainType enum)
        self.type = None
        # A list of ticket information. There should
        # be at maximum one item per ticket type.
        self.tickets = []
        # The departure time of the train (datetime.datetime)
        self.departure_time = None
        # The arrival time of the train (datetime.datetime)
        self.arrival_time = None
        # The length of the trip (datetime.timedelta)
        self.duration = None
        # A station object that represents the departure (from) station
        self.departure_station = None
        # A station object that represents the arrival (to) station
        self.arrival_station = None
        # Whether it has passed the selling time for this train.
        # If sold out, this value should still be true.
        self.has_begun_selling = False
        # If self.has_begun_selling is false, holds the time
        # at which tickets for this train will begin selling.
        self.begin_selling_time = None


class Station:

    def __init__(self, station_id, station_name, station_pinyin, station_pinyin_abbreviated):
        self.id = station_id
        self.name = station_name
        self.pinyin = station_pinyin
        self.pinyin_abbreviated = station_pinyin_abbreviated

    @staticmethod
    def _fetch_station_list():
        # Ugh, why don't they just store the station list as a text file or something?
        # Why did they have to make it a JavaScript file, of all things?!
        url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
        response = requests.get(url, verify=False)
        response.raise_for_status()
        logger.debug("Fetched station list (status code: " + str(response.status_code) + ")")
        split = response.text.split("'")
        assert len(split) == 3
        return split[1].split("@")

    @staticmethod
    def get_all_stations():
        # Format of each entry is as follows:
        # bjb|北京北|VAP|beijingbei|bjb|0
        # 0. defines alphabetical order
        # 1. user-friendly name
        # 2. station ID
        # 3. name in pinyin
        # 4. name in pinyin (abbreviated to first characters)
        # 5. station number (0-indexed)

        data_list = Station._fetch_station_list()
        station_list = []

        # The first entry is blank, since it starts with an "@"
        for i in range(1, len(data_list)):
            data_split = data_list[i].split("|")
            station_list.append(Station(data_split[2], data_split[1], data_split[3], data_split[4]))
        return station_list


class Ticket:

    def __init__(self):
        # The seat type (from TicketType enum)
        self.type = None
        # The price of the ticket, as a double (e.g 546.23)
        self.price = None
        # The number of tickets remaining.
        # -1 if count is unknown (unlimited if selling, or not yet selling)
        self.count = 0