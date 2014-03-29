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

from core.enums import TicketStatus, TicketType


class TicketList:
    def __init__(self, ticket_dict):
        self.__tickets = ticket_dict

    def __getitem__(self, ticket_type):
        return self.__tickets[ticket_type]

    def __iter__(self):
        for ticket in self.__tickets.values():
            yield ticket

    def __len__(self):
        return len(self.__tickets)


class Ticket:
    def __init__(self, train, ticket_type, count_text, count_num):
        # The train this object corresponds to
        self.train = train
        # The seat type (from TicketType enum)
        self.type = ticket_type
        # The number of tickets remaining
        self.count = count_num
        # Ticket status: not yet sold, sold out, or normal
        self.status = TicketStatus.REVERSE_TEXT_LOOKUP.get(count_text, TicketStatus.NORMAL)
        if self.status != TicketStatus.NORMAL:
            assert count_num == 0
        else:
            assert count_num != 0
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

    def __repr__(self):
        count_info = {
            TicketStatus.NOT_APPLICABLE: "not applicable",
            TicketStatus.NOT_YET_SOLD: "not yet sold",
            TicketStatus.SOLD_OUT: "sold out",
            TicketStatus.NORMAL: "{0} remaining"
        }[self.status].format(self.count)
        return "{0} -> {1} ({2})".format(
            self.train.name,
            TicketType.FULL_NAME_LOOKUP[self.type],
            count_info
        )