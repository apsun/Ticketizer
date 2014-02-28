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

from core.enums import TrainType, TicketType, TicketStatus
from core.processing.containers import BitFlags, FlagSet, ValueRange


class TrainFilter:
    def __init__(self):
        # Filter to ignore certain train types
        self.enabled_types = BitFlags(TrainType.ALL)
        # If any trains are added to this set, they will be returned,
        # regardless of whether they meet other criteria. To ONLY allow trains
        # in this list to appear, simply set enabled_types to TrainType.NONE.
        self.whitelist = FlagSet()
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
        if self.whitelist[train.name]:
            return True
        if self.blacklist[train.name]:
            return False
        if not self.enabled_types[train.type]:
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
        self.enabled_types = BitFlags(TicketType.ALL)
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
        if not self.enabled_types[ticket.type]:
            return False
        if not self.price_range.check(lambda: ticket.price):
            return False
        return True

    def filter(self, tickets):
        return [ticket for ticket in tickets if self.check(ticket)]