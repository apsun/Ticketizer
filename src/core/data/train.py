# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from core import logger, common, webrequest
from core.enums import TrainType, TicketType, TicketStatus
from core.data.ticket import Ticket, TicketCount, TicketList


class Train:
    def __init__(self, raw_data, departure_station, destination_station, pricing, direction):
        # The user-friendly name of the train (e.g. T546)
        self.name = raw_data["station_train_code"]
        # The unique internal identifier of the train (e.g. 5l000D220200)
        self.id = raw_data["train_no"]
        # The type of the train (from TrainType enum)
        self.type = TrainType.REVERSE_ABBREVIATION_LOOKUP.get(self.name[0], TrainType.OTHER)
        # A station object that represents the departure (from) station
        self.departure_station = departure_station
        # A station object that represents the arrival (to) station
        self.destination_station = destination_station
        # The ticket pricing (normal/student) used when searching for this train
        self.pricing = pricing
        # The train direction (one-way/round-trip) used when searching for this train
        self.direction = direction
        # The departure time of the train (datetime.datetime)
        self.departure_time = common.str_to_datetime(raw_data["start_train_date"], raw_data["start_time"], "%Y%m%d")
        # The length of the trip (datetime.timedelta)
        self.duration = timedelta(minutes=int(raw_data["lishiValue"]))
        # The arrival time of the train (datetime.datetime)
        self.arrival_time = self.departure_time + self.duration
        # The 1-based index of the departure station in the train's overall station list
        self.departure_index = raw_data["from_station_no"]
        # The 1-based index of the arrival station in the train's overall station list
        self.destination_index = raw_data["to_station_no"]
        # Whether we can buy any tickets for this train
        self.can_buy = common.is_true(raw_data["canWebBuy"])
        # Data that we don't use, but is still required for
        # purchasing tickets.
        self.data = {
            # Used for buying tickets.
            "ticket_count": raw_data["yp_info"],
            # Used for querying ticket prices.
            "seat_types": raw_data["seat_types"],
            # Used for purchasing tickets. Note that this value
            # expires 5 minutes after creation, so the client must
            # re-query the train information after creating this object
            # if they want to purchase any tickets.
            "secret_key": raw_data["secretStr"]
        }
        # A dictionary mapping each ticket type to a Ticket object.
        # Even if the train does not have that ticket type,
        # an object should still be created for it.
        self.tickets = TicketList(self.__get_ticket_dict(self, raw_data, self.__parse_ticket_count(raw_data["yp_info"])))
        # Set the ticket selling time
        self.begin_selling_time = self.__get_begin_selling_time(self.tickets, raw_data)
        # A flag to see whether we have already fetched ticket prices.
        self.__ticket_prices_fetched = False

    @staticmethod
    def __parse_ticket_count(ticket_count_str):
        # WTF, 12306! Ever heard of CSV? Arrays? ANYTHING but this?!
        # Each entry is 10 characters long (or at least, it better be...)
        assert len(ticket_count_str) % 10 == 0
        ticket_counts = [ticket_count_str[i:i+10] for i in range(0, len(ticket_count_str), 10)]
        counts = {}
        for ticket_count in ticket_counts:
            # Last 4 digits represent ticket count
            count_int = int(ticket_count[6:])
            if count_int >= 3000:
                # If the ticket count >= 3000, the count
                # refers to the 无座 ticket type
                type_value = TicketType.NO_SEAT
                count_int -= 3000
            else:
                # Find type based on first character
                type_value = TicketType.REVERSE_ID_LOOKUP[ticket_count[0]]
            counts[type_value] = count_int
        return counts

    @staticmethod
    def __get_ticket_dict(train, data_dict, count_dict):
        tickets = {}
        for key, value in TicketType.REVERSE_ABBREVIATION_LOOKUP.items():
            # ticket_count = TicketCount(data_dict[key + "_num"])
            ticket_count = TicketCount(str(count_dict.get(value, 0)))
            tickets[value] = Ticket(train, value, ticket_count)
        return tickets

    @staticmethod
    def __get_begin_selling_time(tickets, data_dict):
        # For some reason, different ticket categories can
        # begin selling at different times. Thus, even if we
        # can buy some tickets, some might still be unavailable.
        # This "transition" usually lasts around 5 minutes.
        # if self.can_buy:
        #     return None

        # Either the tickets are all sold out or some are
        # not yet sold. Make sure this is the latter case.
        not_yet_sold = False
        for ticket in tickets:
            if ticket.count.status == TicketStatus.NOT_YET_SOLD:
                not_yet_sold = True
                break
        if not not_yet_sold:
            return None

        begin_date = data_dict["control_train_day"]
        # I sure hope this website doesn't last until 2030-03-03...
        if begin_date == "20300303":
            begin_date = datetime.now().date()
        return common.str_to_datetime(begin_date, data_dict["sale_time"], "%Y%m%d", "%H%M")

    def __get_price_query_params(self):
        return [
            ("train_no", self.id),
            ("from_station_no", self.departure_index),
            ("to_station_no", self.destination_index),
            ("seat_types", self.data["seat_types"]),
            ("train_date", common.date_to_str(self.departure_time))
        ]

    def refresh_ticket_prices(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"
        params = self.__get_price_query_params()
        json = webrequest.get_json(url, params=params)
        for key, value in json["data"].items():
            if not isinstance(value, str):
                continue
            ticket_type = TicketType.REVERSE_ID2_LOOKUP.get(key)
            if ticket_type is None:
                continue
            if self.tickets[ticket_type].count.status == TicketStatus.NOT_APPLICABLE:
                continue
            # Ensure that price is in the format ¥XXX.X
            assert value[0] == "¥"
            assert value[-2] == "."
            self.tickets[ticket_type].price = float(value[1:])
        self.__ticket_prices_fetched = True
        logger.debug("Fetched ticket prices for train " + self.name)

    def __str__(self):
        return "{0} (ID: {1}) from {2} to {3}".format(
            self.name,
            self.id,
            self.departure_station.name,
            self.destination_station.name
        )