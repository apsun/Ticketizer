# -*- coding: utf-8 -*-
from core.enums import TrainType, TicketType, TicketStatus
from core.processing.containers import BitFlags, FlagSet, ValueRange


class TrainFilter:
    def __init__(self):
        # TODO: Add a whitelist feature
        # Filter to ignore certain train types
        self.type_filter = BitFlags(TrainType.ALL, TrainType.ALL, TrainType.NONE)
        # Add train names (e.g. "T110") to this list to ignore them
        self.blacklist = FlagSet()
        # Departure and arrival time filters. Trains that depart/arrive
        # outside this time range will be ignored. -- ValueRange<datetime.time>
        self.departure_time_range = ValueRange()
        self.arrival_time_range = ValueRange()
        # Train duration filter. Trains that have a travel time outside this
        # range will be ignored. -- ValueRange<datetime.timedelta>
        self.duration_range = ValueRange()
        self.ticket_filter = TicketFilter()

    def check(self, train):
        if self.blacklist[train.name]:
            return False
        if not self.type_filter[train.type]:
            return False
        if not self.departure_time_range.check(train.departure_time.time()):
            return False
        if not self.arrival_time_range.check(train.arrival_time.time()):
            return False
        if not self.duration_range.check(train.duration):
            return False
        if len(self.ticket_filter.filter(train.tickets)) == 0:
            return False
        return True

    def filter(self, trains):
        return [train for train in trains if self.check(train)]


class TicketFilter:
    def __init__(self):
        # Type mask to filter ticket types
        self.type_filter = BitFlags(TicketType.ALL, TicketType.ALL, TicketType.NONE)
        # Price filter. Tickets with prices outside
        # this range will be ignored. (ValueRange)
        self.price_range = ValueRange()
        # Whether to ignore trains that aren't selling tickets yet
        self.filter_not_yet_sold = False
        # Whether to ignore trains that are completely sold out
        self.filter_sold_out = False

    def check(self, ticket):
        ticket_status = ticket.status
        if ticket_status == TicketStatus.NOT_APPLICABLE:
            return False
        if self.filter_sold_out and ticket_status == TicketStatus.SOLD_OUT:
            return False
        if self.filter_not_yet_sold and ticket_status == TicketStatus.NOT_YET_SOLD:
            return False
        if not self.type_filter[ticket.type]:
            return False
        if not self.price_range.check(lambda: ticket.price):
            return False
        return True

    def filter(self, tickets):
        return [ticket for ticket in tickets if self.check(ticket)]