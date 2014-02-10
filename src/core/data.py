# -*- coding: utf-8 -*-
import numbers
import requests
import datetime
from . import logger
from . import common
from . import enums


class Train:

    def __init__(self, data_dict, origin_station, destination_station):
        # The user-friendly name of the train (e.g. T546)
        self.name = data_dict["station_train_code"]
        # The unique internal identifier of the train (e.g. 5l000D220200)
        self.id = data_dict["train_no"]
        # The type of the train (from TrainType enum)
        self.type = enums.TrainType.REVERSE_ABBREVIATION_LOOKUP.get(self.name[0], enums.TrainType.OTHER)
        # A station object that represents the departure (from) station
        self.origin_station = origin_station
        # A station object that represents the arrival (to) station
        self.destination_station = destination_station
        # The departure time of the train (datetime.datetime)
        self.departure_time = common.str_to_datetime(data_dict["start_train_date"], data_dict["start_time"], "%Y%m%d")
        # The length of the trip (datetime.timedelta)
        self.duration = datetime.timedelta(minutes=int(data_dict["lishiValue"]))
        # The arrival time of the train (datetime.datetime)
        self.arrival_time = self.departure_time + self.duration
        # The 1-based index of the departure station in the train's overall station list
        self.origin_index = data_dict["from_station_no"]
        # The 1-based index of the arrival station in the train's overall station list
        self.destination_index = data_dict["to_station_no"]
        # Whether it has passed the selling time for this train.
        # TODO: This is false when no tickets are left. What do?
        self.has_begun_selling = common.is_true(data_dict["canWebBuy"])
        # If self.has_begun_selling is false, holds the time (datetime.time)
        # at which tickets for this train will begin selling.
        self.begin_selling_time = common.str_to_time(data_dict["sale_time"], "%H%M")
        # Some stupid string that shows the type of seats this train has.
        # Used for querying ticket prices.
        self.seat_types = data_dict["seat_types"]
        # A string that is used when purchasing the ticket
        self.secret_key = data_dict["secretStr"]
        # A dictionary mapping each ticket type to a Ticket object.
        # Even if the train does not have that ticket type,
        # an object should still be created for it.
        self.tickets = {}
        for key, value in enums.TicketType.REVERSE_ABBREVIATION_LOOKUP.items():
            ticket_count = TicketCount(data_dict[key + "_num"])
            ticket_type = value
            self.tickets[value] = Ticket(self, ticket_type, ticket_count)
        # A flag to see whether we have already fetched ticket prices.
        self.ticket_prices_fetched = False

    def __get_price_query_params(self):
        # Once again, we have a case where the order of params matters.
        # I hate you so much I want to rearrange these params up your rectum.
        return "train_no=%s&" \
               "from_station_no=%s&" \
               "to_station_no=%s&" \
               "seat_types=%s&" \
               "train_date=%s" % (self.id,
                                  self.origin_index,
                                  self.destination_index,
                                  self.seat_types,
                                  common.date_to_str(self.departure_time))

    def refresh_ticket_prices(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?" + self.__get_price_query_params()
        response = requests.get(url, verify=False)
        response.raise_for_status()
        json_data = common.read_json_data(response)
        for key, value in json_data.items():
            if not isinstance(value, str):
                continue
            ticket_type = enums.TicketType.REVERSE_ID2_LOOKUP.get(key)
            if ticket_type is None:
                continue
            if self.tickets[ticket_type].count.status == enums.TicketStatus.NotApplicable:
                continue
            # Ensure that price is in the format ¥XXX.X
            assert value[0] == "¥"
            assert value[-2] == "."
            self.tickets[ticket_type].price = float(value[1:])
        self.ticket_prices_fetched = True
        logger.debug("Fetched ticket prices for train " + self.name, response)


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

    @staticmethod
    def get_all_stations():
        url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
        response = requests.get(url, verify=False)
        response.raise_for_status()
        logger.debug("Fetched station list (status code: " + str(response.status_code) + ")")
        split = response.text.split("'")
        assert len(split) == 3
        data_list = split[1].split("@")[1:]
        return [Station(item.split("|")) for item in data_list]


class Ticket:

    def __init__(self, train, ticket_type, count):
        # The train this object corresponds to
        self.train = train
        # The seat type (from TicketType enum)
        self.type = ticket_type
        # The number of tickets remaining as a TicketCount class
        self.count = count
        # The price of the ticket, as a double (e.g 546.23)
        # Note that this is None until explicitly refreshed, because
        # each train needs to query for its ticket prices individually,
        # which is insanely slow (network requests, yo).
        # The value can also be None if the ticket type does not exist.
        self.__price = None

    @property
    def price(self):
        if not self.train.ticket_prices_fetched:
            self.train.refresh_ticket_prices()
        return self.__price

    @price.setter
    def price(self, value):
        self.__price = value


class TicketCount:

    def __init__(self, count_string):
        # Since all the workers at 12306 have a combined IQ of "banana",
        # I have to wrap their stupidity with this class (which is just as stupid).
        # It just provides easier comparisons against cases such as "有" or "无".
        # (Who the heck thought that was a good idea? Why not just give a number?)

        if count_string == "--":  # Train doesn't have this type of ticket
            self.status = enums.TicketStatus.NotApplicable
            self.value = 0
        elif count_string == "*":  # Tickets are not being sold yet (or none remaining, occasionally)
            self.status = enums.TicketStatus.NotYetSold
            self.value = 0
        elif count_string == "有":  # More than 20 tickets remaining
            self.status = enums.TicketStatus.LargeCount
            self.value = float("inf")
        elif count_string == "无":  # No tickets remaining
            self.status = enums.TicketStatus.SoldOut
            self.value = 0
        else:
            self.status = enums.TicketStatus.Normal
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
        status = enums.TicketStatus
        return {
            status.NotApplicable: "--",
            status.NotYetSold: "*",
            status.LargeCount: "有",
            status.SoldOut: "无"
        }.get(self.status, str(self.value))