# -*- coding: utf-8 -*-
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

    def __str__(self):
        return "{0} -> {1} (count: {2})".format(
            self.train.name,
            TicketType.FULL_NAME_LOOKUP[self.type],
            TicketStatus.TEXT_LOOKUP.get(self.status, str(self.count))
        )