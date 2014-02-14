# -*- coding: utf-8 -*-
from core.enums import TrainType, TicketType, TicketStatus
from core.processing.containers import BitFlags, FlagSet, ValueRange


class TrainFilter:
    def __init__(self):
        # Filter to ignore certain train types
        self.type_filter = BitFlags(TrainType.ALL, TrainType.ALL, TrainType.NONE)
        # Add train names (e.g. "T110") to this list to ignore them
        self.blacklist = FlagSet()
        # Departure and arrival time filters. Trains that depart/arrive
        # outside this time range will be ignored. -- ValueRange<datetime.time>
        # TODO: Change this to compare datetime.datetime for overnight trains?
        self.departure_time_range = ValueRange()
        self.arrival_time_range = ValueRange()
        # Train duration filter. Trains that have a travel time outside this
        # range will be ignored. -- ValueRange<datetime.timedelta>
        self.duration_range = ValueRange()
        self.ticket_filter = TicketFilter()

    def __filter_trains(self, trains):
        for train in trains:
            if self.blacklist[train.name]:
                continue
            if not self.type_filter[train.type]:
                continue
            if not self.departure_time_range.check(train.departure_time.time()):
                continue
            if not self.arrival_time_range.check(train.arrival_time.time()):
                continue
            if not self.duration_range.check(train.duration):
                continue
            if len(self.ticket_filter.filter(train.tickets)):
                continue
            yield train

    def filter(self, trains):
        return list(self.__filter_trains(trains))


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

    def __filter_tickets(self, tickets):
        for ticket in tickets:
            ticket_status = ticket.count.status
            if ticket_status == TicketStatus.NotApplicable:
                continue
            if self.filter_sold_out and ticket_status == TicketStatus.SoldOut:
                continue
            if self.filter_not_yet_sold and ticket_status == TicketStatus.NotYetSold:
                continue
            if self.type_filter[ticket.type]:
                continue
            if not self.price_range.check(lambda: ticket.price):
                continue
            yield ticket

    def filter(self, tickets):
        return list(self.__filter_tickets(tickets))