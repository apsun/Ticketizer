# -*- coding: utf-8 -*-
from numbers import Number
from core.enums import TicketStatus


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

    @property
    def status(self):
        return self.count.status


class TicketCount:

    def __init__(self, count_string):
        # Since all the workers at 12306 have a combined IQ of "banana",
        # I have to wrap their stupidity with this class (which is just as stupid).
        # It just provides easier comparisons against cases such as "有" or "无".
        # (Who the heck thought that was a good idea? Why not just give a number?)
        status = TicketStatus
        self.status = status.REVERSE_TEXT_LOOKUP.get(count_string, status.Normal)
        if self.status == status.LargeCount:
            self.value = float("inf")
        elif self.status == status.Normal:
            self.value = int(count_string)
        else:
            self.value = 0

    def __lt__(self, other):
        if isinstance(other, Number):
            return self.value < other
        if isinstance(other, TicketCount):
            return self.value < other.value
        raise TypeError()

    def __le__(self, other):
        if isinstance(other, Number):
            return self.value <= other
        if isinstance(other, TicketCount):
            return self.value <= other.value
        raise TypeError()

    def __gt__(self, other):
        return not (self <= other)

    def __ge__(self, other):
        return not (self < other)

    def __eq__(self, other):
        if isinstance(other, Number):
            return self.value == other
        if isinstance(other, TicketCount):
            return self.value == other.value
        raise TypeError()

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return TicketStatus.TEXT_LOOKUP.get(self.status, str(self.value))