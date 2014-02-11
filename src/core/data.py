# -*- coding: utf-8 -*-
import numbers
import requests
import datetime
from . import logger
from . import common
from . import enums


class Train:

    def __init__(self, data_dict, departure_station, destination_station):
        # The user-friendly name of the train (e.g. T546)
        self.name = data_dict["station_train_code"]
        # The unique internal identifier of the train (e.g. 5l000D220200)
        self.id = data_dict["train_no"]
        # The type of the train (from TrainType enum)
        self.type = enums.TrainType.REVERSE_ABBREVIATION_LOOKUP.get(self.name[0], enums.TrainType.OTHER)
        # A station object that represents the departure (from) station
        self.departure_station = departure_station
        # A station object that represents the arrival (to) station
        self.destination_station = destination_station
        # The departure time of the train (datetime.datetime)
        self.departure_time = common.str_to_datetime(data_dict["start_train_date"], data_dict["start_time"], "%Y%m%d")
        # The length of the trip (datetime.timedelta)
        self.duration = datetime.timedelta(minutes=int(data_dict["lishiValue"]))
        # The arrival time of the train (datetime.datetime)
        self.arrival_time = self.departure_time + self.duration
        # The 1-based index of the departure station in the train's overall station list
        self.departure_index = data_dict["from_station_no"]
        # The 1-based index of the arrival station in the train's overall station list
        self.destination_index = data_dict["to_station_no"]
        # Whether we can buy any tickets for this train
        self.can_buy = common.is_true(data_dict["canWebBuy"])
        # Used for querying ticket prices.
        self.seat_types = data_dict["seat_types"]
        # Used for purchasing tickets.
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
        # Set the ticket selling time
        if not self.can_buy:
            not_yet_sold = False
            for ticket in self.tickets.values():
                if ticket.count.status == enums.TicketStatus.NotYetSold:
                    not_yet_sold = True
                    break
            if not_yet_sold:
                # TODO: Is this even correct?
                begin_date = data_dict["control_train_day"]
                # I sure hope this website doesn't last until 2030-03-03...
                if begin_date == "20300303":
                    begin_date = datetime.datetime.now().date()
                self.begin_selling_time = common.str_to_datetime(begin_date, data_dict["sale_time"], "%Y%m%d", "%H%M")

    def __get_price_query_params(self):
        # Once again, we have a case where the order of params matters.
        return "train_no=%s&" \
               "from_station_no=%s&" \
               "to_station_no=%s&" \
               "seat_types=%s&" \
               "train_date=%s" % (self.id,
                                  self.departure_index,
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
        split = response.text.split("'")
        assert len(split) == 3
        logger.debug("Fetched station list (status code: " + str(response.status_code) + ")")
        return [Station(item.split("|")) for item in split[1].split("@")[1:]]


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
        status = enums.TicketStatus
        self.status = status.REVERSE_TEXT_LOOKUP.get(count_string, status.Normal)
        if self.status == status.LargeCount:
            self.value = float("inf")
        elif self.status == status.Normal:
            self.value = int(count_string)
        else:
            self.value = 0

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
        return enums.TicketStatus.TEXT_LOOKUP.get(self.status, str(self.value))