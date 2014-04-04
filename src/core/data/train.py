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

from datetime import datetime, timedelta
from core import logger, timeconverter, webrequest
from core.enums import TrainType, TicketType, TicketStatus
from core.data.ticket import Ticket, TicketList


class Train:
    def __init__(self, train_data, departure_station, destination_station, pricing, direction, date):
        query_data = train_data["queryLeftNewDTO"]
        # The user-friendly name of the train (e.g. T546)
        self.name = query_data["station_train_code"]
        # The unique internal identifier of the train (e.g. 5l000D220200)
        self.id = query_data["train_no"]
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
        # The date must be passed in from the query because 12306
        # has a bug where the incorrect date is returned in the data.
        self.departure_time = timeconverter.str_to_datetime(date, query_data["start_time"])
        # The length of the trip (datetime.timedelta)
        self.duration = timedelta(minutes=int(query_data["lishiValue"]))
        # The arrival time of the train (datetime.datetime)
        self.arrival_time = self.departure_time + self.duration
        # The 1-based index of the departure station in the train's overall station list
        self.departure_index = query_data["from_station_no"]
        # The 1-based index of the arrival station in the train's overall station list
        self.destination_index = query_data["to_station_no"]
        # Whether we can buy any tickets for this train
        self.can_buy = query_data.get_bool("canWebBuy")
        # Data that we don't use, but is still required for purchasing tickets.
        self.data = {
            # Required for getting train path.
            # Can be, but IS NOT ALWAYS, the same
            # as the queried train date.
            "alt_date": query_data["start_train_date"],
            # Used for buying tickets.
            "location_code": query_data["location_code"],
            # Used for buying tickets (also holds ticket count data).
            "ticket_count": query_data["yp_info"],
            # Used for querying ticket prices.
            "seat_types": query_data["seat_types"],
            # Used for purchasing tickets. Note that this value
            # expires 5 minutes after creation, so the client must
            # re-query the train information after creating this object
            # if they want to purchase any tickets.
            "secret_key": train_data["secretStr"]
        }
        # A dictionary mapping each ticket type to a Ticket object.
        # Even if the train does not have that ticket type,
        # an object should still be created for it.
        self.tickets = TicketList(self.__get_ticket_dict(query_data))
        # Set the ticket selling time
        self.begin_selling_time = self.__get_begin_selling_time(self.tickets, query_data)
        # A flag to see whether we have already fetched ticket prices.
        self.ticket_prices_fetched = False

    @staticmethod
    def __parse_ticket_count(query_data):
        # WTF, 12306! Ever heard of CSV? Arrays? ANYTHING but this?!
        ticket_count_str = query_data["yp_info"]
        # Each entry is 10 characters long (or at least, it better be...)
        assert len(ticket_count_str) % 10 == 0
        ticket_counts = [ticket_count_str[i:i+10] for i in range(0, len(ticket_count_str), 10)]
        counts = {}
        for ticket_count in ticket_counts:
            # Last 4 digits represent ticket count
            count_int = int(ticket_count[6:])
            if count_int >= 3000:
                # If the ticket count >= 3000, the count
                # refers to the no-seat ticket type
                type_value = TicketType.NO_SEAT
                count_int -= 3000
            else:
                # Find type based on first character
                type_value = TicketType.REVERSE_ID_LOOKUP[ticket_count[0]]
            counts[type_value] = count_int
        return counts

    def __get_ticket_dict(self, query_data):
        count_data = self.__parse_ticket_count(query_data)
        tickets = {}
        for key, value in TicketType.REVERSE_ABBREVIATION_LOOKUP.items():
            ticket_count_text = query_data[key + "_num"]
            ticket_count_num = count_data.get(value, 0)
            tickets[value] = Ticket(self, value, ticket_count_text, ticket_count_num)
        return tickets

    @staticmethod
    def __get_begin_selling_time(tickets, query_data):
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
            if ticket.status == TicketStatus.NOT_YET_SOLD:
                not_yet_sold = True
                break
        if not not_yet_sold:
            return None

        begin_date = query_data["control_train_day"]
        # I sure hope this website doesn't last until 2030-03-03...
        if begin_date == "20300303":
            begin_date = datetime.now().date()
        return timeconverter.str_to_datetime(begin_date, query_data["sale_time"], "%Y%m%d", "%H%M")

    def __get_price_query_params(self):
        return [
            ("train_no", self.id),
            ("from_station_no", self.departure_index),
            ("to_station_no", self.destination_index),
            ("seat_types", self.data["seat_types"]),
            ("train_date", timeconverter.date_to_str(self.departure_time))
        ]

    def refresh_ticket_prices(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/queryTicketPrice"
        params = self.__get_price_query_params()
        json = webrequest.get_json(url, params=params)
        for key, value in json["data"].items():
            if not isinstance(value, str):
                continue
            if value[0] == "¥" and value[-2] == ".":
                num_value = float(value[1:])
                lookup = TicketType.REVERSE_ID2_LOOKUP
            else:
                try:
                    num_value = int(value)/10.0
                    lookup = TicketType.REVERSE_ID_LOOKUP
                except ValueError:
                    continue
            ticket_type = lookup.get(key)
            if ticket_type is None:
                continue
            if self.tickets[ticket_type].status == TicketStatus.NOT_APPLICABLE:
                continue
            self.tickets[ticket_type].price = num_value
        self.ticket_prices_fetched = True
        logger.debug("Fetched ticket prices for train " + self.name)

    def __repr__(self):
        return "{0} (ID: {1}) from {2} to {3}".format(
            self.name,
            self.id,
            self.departure_station.name,
            self.destination_station.name
        )