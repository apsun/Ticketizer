# -*- coding: utf-8 -*-
import numbers
import requests
from . import logger
from . import common


class Train:

    def __init__(self):
        # The user-friendly name of the train (e.g. T546)
        self.name = None
        # The unique internal identifier of the train (e.g. 5l000D220200)
        self.id = None
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
        # The 1-based index of the departure station in the train's overall station list
        self.departure_index = None
        # The 1-based index of the arrival station in the train's overall station list
        self.arrival_index = None
        # Whether it has passed the selling time for this train.
        # If sold out, this value should still be true.
        self.has_begun_selling = False
        # If self.has_begun_selling is false, holds the time
        # at which tickets for this train will begin selling.
        self.begin_selling_time = None
        # Some stupid string that shows the type of seats this train has.
        # Used for querying ticket prices.
        self.seat_types = None

    def _get_price_query_params(self):
        # Once again, we have a case where the order of params matters.
        # I hate you, 12306.

        return "train_no=%s&" \
               "from_station_no=%s&" \
               "to_station_no=%s&" \
               "seat_types=%s&" \
               "train_date=%s" % (self.id,
                                  self.departure_index,
                                  self.arrival_index,
                                  self.seat_types,
                                  common.date_to_str(self.departure_time))

    def refresh_ticket_prices(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?" + self._get_price_query_params()
        response = requests.get(url, verify=False)
        response.raise_for_status()
        json_data = common.read_json_data(response)
        # TODO: FINISH
        pass


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
            split = data_list[i].split("|")
            station_list.append(Station(split[2], split[1], split[3], split[4]))
        return station_list


class Ticket:

    def __init__(self):
        # The seat type (from TicketType enum)
        self.type = None
        # The price of the ticket, as a double (e.g 546.23)
        self.price = None
        # The number of tickets remaining as a TicketCount class
        self.count = None


class TicketCount:

    NotApplicable = 0  # --  -> int(0)
    NotYetSold = 1     # *   -> int(0)
    LargeCount = 2     # 有  -> float("inf")
    SoldOut = 3        # 无  -> int(0)
    Normal = 4         # int -> int

    def __init__(self, count_string):
        # Since all the workers at 12306 have a combined IQ of "banana",
        # I have to wrap their stupidity with this class (which is just as stupid).
        # It just provides easier comparisons against cases such as "有" or "无".
        # (Who the heck thought that was a good idea? Why not just give a number?)

        if count_string == "--":  # Train doesn't have this type of ticket
            self.status = self.NotApplicable
            self.value = 0
        elif count_string == "*":  # Tickets are not being sold yet (or none remaining, occasionally)
            self.status = self.NotYetSold
            self.value = 0
        elif count_string == "有":  # Large amount of tickets remaining, count unknown
            self.status = self.LargeCount
            self.value = float("inf")
        elif count_string == "无":  # No tickets remaining
            self.status = self.SoldOut
            self.value = 0
        else:
            self.status = self.Normal
            self.value = int(count_string)

    def __lt__(self, other):
        if isinstance(other, numbers.Number):
            return self.value < other
        if isinstance(other, TicketCount):
            return self.value < other.value
        raise TypeError()

    def __le__(self, other):
        if isinstance(other, numbers.Number):
            return self.value <= other
        if isinstance(other, TicketCount):
            return self.value <= other.value
        raise TypeError()

    def __gt__(self, other):
        return not (self <= other)

    def __ge__(self, other):
        return not (self < other)

    def __eq__(self, other):
        if isinstance(other, numbers.Number):
            return self.value == other
        if isinstance(other, TicketCount):
            return self.value == other.value
        raise TypeError()

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        # Oh god here we go again...
        return {
            self.NotApplicable: "--",
            self.NotYetSold: "*",
            self.LargeCount: "有",
            self.SoldOut: "无"
        }.get(self.status, str(self.value))