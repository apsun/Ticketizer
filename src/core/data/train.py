# -*- coding: utf-8 -*-
import datetime
import requests
from core.data.ticket import Ticket, TicketCount, TicketList
from core.enums import TrainType, TicketType, TicketStatus
from core import logger, common


class Train:
    def __init__(self, data_dict, departure_station, destination_station):
        # The user-friendly name of the train (e.g. T546)
        self.name = data_dict["station_train_code"]
        # The unique internal identifier of the train (e.g. 5l000D220200)
        self.id = data_dict["train_no"]
        # The type of the train (from TrainType enum)
        self.type = TrainType.REVERSE_ABBREVIATION_LOOKUP.get(self.name[0], TrainType.OTHER)
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
        self.tickets = TicketList(self.__get_ticket_dict(data_dict))
        # A flag to see whether we have already fetched ticket prices.
        self.ticket_prices_fetched = False
        # Set the ticket selling time
        self.begin_selling_time = self.__get_begin_selling_time(data_dict)

    def __get_ticket_dict(self, data_dict):
        tickets = {}
        for key, value in TicketType.REVERSE_ABBREVIATION_LOOKUP.items():
            ticket_count = TicketCount(data_dict[key + "_num"])
            tickets[value] = Ticket(self, value, ticket_count)
        return tickets

    def __get_begin_selling_time(self, data_dict):
        if self.can_buy:
            return None
        not_yet_sold = False
        for ticket in self.tickets:
            if ticket.count.status == TicketStatus.NotYetSold:
                not_yet_sold = True
                break
        if not not_yet_sold:
            return None
        # TODO: Is this even correct?
        begin_date = data_dict["control_train_day"]
        # I sure hope this website doesn't last until 2030-03-03...
        if begin_date == "20300303":
            begin_date = datetime.datetime.now().date()
        return common.str_to_datetime(begin_date, data_dict["sale_time"], "%Y%m%d", "%H%M")

    def __get_price_query_params(self):
        # Once again, we have a case where the order of params matters.
        return common.get_ordered_query_params(
            "train_no", self.id,
            "from_station_no", self.departure_index,
            "to_station_no", self.destination_index,
            "seat_types", self.seat_types,
            "train_date", common.date_to_str(self.departure_time))

    def refresh_ticket_prices(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice?" + self.__get_price_query_params()
        response = requests.get(url, verify=False)
        response.raise_for_status()
        json_data = common.read_json_data(response)
        for key, value in json_data.items():
            if not isinstance(value, str):
                continue
            ticket_type = TicketType.REVERSE_ID2_LOOKUP.get(key)
            if ticket_type is None:
                continue
            if self.tickets[ticket_type].count.status == TicketStatus.NotApplicable:
                continue
            # Ensure that price is in the format ¥XXX.X
            assert value[0] == "¥"
            assert value[-2] == "."
            self.tickets[ticket_type].price = float(value[1:])
        self.ticket_prices_fetched = True
        logger.debug("Fetched ticket prices for train " + self.name, response)

    def __str__(self):
        return "{0} (ID: {1}) from {2} to {3}".format(
            self.name,
            self.id,
            self.departure_station.name,
            self.destination_station.name
        )