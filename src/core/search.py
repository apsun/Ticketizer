# -*- coding: utf-8 -*-
import datetime
import requests
from . import data


class TicketPricing:
    NORMAL = "ADULT"
    STUDENT = "0X00"


class TicketDirection:
    ONE_WAY = "dc"
    ROUND_TRIP = "fc"


class ValueRange:

    def __init__(self, lower=None, upper=None):
        self.lower = lower
        self.upper = upper

    def check_value(self, value):
        lower = self.lower
        upper = self.upper
        if lower is None:
            if upper is None:
                return True
            else:
                return value <= upper
        else:
            if upper is None:
                return lower <= value
            else:
                return lower <= value <= upper
        

class TrainSorter:
    
    def __init__(self):
        self.favorites = {}
        self.sort_method = self.sort_by_type
        self.reverse_sort = False
        
    def set_train_favorited(self, train_name, favorite):
        self.favorites[train_name] = favorite

    def get_train_favorited(self, train_name):
        return self.favorites.get(train_name, False)

    def toggle_train_favorited(self, train_name):
        self.set_train_favorited(train_name, not self.get_train_favorited(train_name))

    def sort(self, train_list):
        self.sort_method(train_list, self.reverse_sort)

    def sort_by_departure_time(self, train_list, reverse):
        self._sort_by_key(train_list, lambda x: x.departure_time, reverse)

    def sort_by_arrival_time(self, train_list, reverse):
        self._sort_by_key(train_list, lambda x: x.arrival_time, reverse)

    def sort_by_duration(self, train_list, reverse):
        self._sort_by_key(train_list, lambda x: x.duration, reverse)

    def sort_by_price(self, train_list, reverse):
        # No idea why anyone would want to sort by maximum price, but whatever...
        if reverse:
            self._sort_by_key(train_list, lambda x: max(x.tickets, lambda t: t.price), True)
        else:
            self._sort_by_key(train_list, lambda x: min(x.tickets, lambda t: t.price), False)

    def sort_by_type(self, train_list, reverse):
        self._sort_by_key(train_list, TrainSorter._type_key, reverse)

    @staticmethod
    def _type_key(train):
        types = data.TrainType
        return {
            types.OTHER: 0,
            types.K: 1,
            types.T: 2,
            types.Z: 3,
            types.D: 4,
            types.G: 5
        }[train.type]

    def _sort_by_key(self, train_list, compare_key, reverse):
        # Sorts the train list using the specified key,
        # keeping "favorite" trains in the front.
        # The sorting algorithm used must be stable for this to work!
        train_list.sort(key=compare_key, reverse=reverse)
        train_list.sort(key=lambda x: 0 if self.favorites.get(x.name, False) else 1)
        

class TrainFilter:
    
    def __init__(self):
        # Type mask to filter out certain train types.
        # 0 bit = ignored, 1 bit = OK
        self.train_type_filter = data.TrainType.ALL
        # Dictionary of train names to blacklist
        # True = ignored, False/no key = OK
        self.blacklist = {}
        # Departure time filter. Trains that leave
        # outside this time range will be ignored. (ValueRange)
        self.departure_time_range = None
        # Arrival time filter. Trains that arrive
        # outside this time range will be ignored. (ValueRange)
        self.arrival_time_range = None
        # Duration time filter. Trains that have
        # a travel time outside this range will be ignored. (ValueRange)
        self.duration_range = None
        # Whether to ignore trains that aren't selling tickets yet (bool)
        self.filter_not_sold = False

        # Below are ticket filters

        # Type mask to filter ticket types, just like train_type_filter
        self.ticket_type_filter = data.TicketType.ALL
        # Price filter. Tickets with prices outside
        # this range will be ignored. (ValueRange)
        self.price_range = None
        # Whether to ignore trains that are completely sold out.
        self.filter_sold_out = False

    def set_train_type_enabled(self, train_type, enable):
        if enable:
            self.train_type_filter |= train_type
        else:
            self.train_type_filter &= ~train_type

    def get_train_type_enabled(self, train_type):
        return (self.train_type_filter & train_type) == train_type

    def toggle_train_type_enabled(self, train_type):
        self.train_type_filter ^= train_type
    
    def set_train_enabled(self, train_name, enable):
        self.blacklist[train_name] = not enable
    
    def get_train_enabled(self, train_name):
        return not self.blacklist.get(train_name, False)

    def toggle_train_enabled(self, train_name):
        self.set_train_enabled(train_name, not self.get_train_enabled(train_name))

    def set_ticket_type_enabled(self, ticket_type, enable):
        if enable:
            self.ticket_type_filter |= ticket_type
        else:
            self.ticket_type_filter &= ~ticket_type

    def get_ticket_type_enabled(self, ticket_type):
        return (self.ticket_type_filter & ticket_type) == ticket_type

    def toggle_ticket_type_enabled(self, ticket_type):
        self.ticket_type_filter ^= ticket_type

    @staticmethod
    def filter_tickets(ticket_list, ticket_type_filter, price_range, filter_sold_out):
        for ticket in ticket_list:
            if (ticket_type_filter & ticket.type) != ticket.type:
                continue
            if price_range is not None and not price_range.check_value(ticket.price):
                continue
            if filter_sold_out and ticket.count == 0:
                continue
            yield ticket
    
    def filter_trains(self, train_list):
        # Optimized for speed when filtering a large number of trains.
        # Use this when working with lists of trains instead of calling 
        # individual check functions one at a time.

        # Train filters
        train_type_filter = self.train_type_filter
        blacklist = self.blacklist
        filter_not_sold = self.filter_not_sold
        departure_time_range = self.departure_time_range
        arrival_time_range = self.arrival_time_range
        duration_range = self.duration_range

        # Ticket filters
        ticket_type_filter = self.ticket_type_filter
        price_range = self.price_range
        filter_sold_out = self.filter_sold_out
        ticket_filter = self.filter_tickets

        for train in train_list:
            if (train_type_filter & train.type) != train.type:
                continue
            if blacklist.get(train.name, False):
                continue
            if filter_not_sold and not train.has_begun_selling:
                continue
            if departure_time_range is not None and not departure_time_range.check_value(train.departure_time):
                continue
            if arrival_time_range is not None and not arrival_time_range.check_value(train.arrival_time):
                continue
            if duration_range is not None and not duration_range.check_value(train.duration):
                continue
            # Basically, if there are no tickets that meet our criterion,
            # we just ignore the train completely.
            if len(list(ticket_filter(train.tickets, ticket_type_filter, price_range, filter_sold_out))) == 0:
                continue
            yield train


class TicketQuery:

    def __init__(self):
        # The type of ticket pricing -- normal ("adult") or student
        self.type = TicketPricing.NORMAL
        # The trip type -- one-direction or round-trip
        self.direction = TicketDirection.ONE_WAY

        # Strings are allowed for the following parameters
        # to make testing easier (don't need to instantiate
        # any complex objects, just use the date/ID directly).

        # The departure date -- can be datetime.datetime, datetime.date, or str
        # (If using str, the format must be YYYY-mm-dd)
        self.date = None
        # The origin station -- can be data.Station or str
        # (If using str, use the station's 3-letter ID)
        self.origin = None
        # The destination station -- can be data.Station or str
        # (If using str, use the station's 3-letter ID)
        self.destination = None

    def _get_query_string(self):
        # WTF! Apparently the order of the params DOES MATTER; if you
        # mess up the order, you get an invalid result.
        # Instead of using the built-in method with dicts,
        # now we have to manually concatenate the query parameters.
        train_date = self._get_date()
        from_station = self._get_origin_id()
        to_station = self._get_destination_id()
        purpose_codes = self.type
        return "leftTicketDTO.train_date=%s&" \
               "leftTicketDTO.from_station=%s&" \
               "leftTicketDTO.to_station=%s&" \
               "purpose_codes=%s" % (train_date, from_station, to_station, purpose_codes)

    def _get_destination_id(self):
        destination = self.destination
        if isinstance(destination, str):
            return destination
        if isinstance(destination, data.Station):
            return destination.id
        assert False

    def _get_origin_id(self):
        origin = self.origin
        if isinstance(origin, str):
            return origin
        if isinstance(origin, data.Station):
            return origin.id
        assert False

    def _get_date(self):
        date = self.date
        if isinstance(date, str):
            return date
        elif isinstance(date, datetime.date) or isinstance(date, datetime.datetime):
            return date.strftime("%Y-%m-%d")
        assert False

    def execute(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/query?" + self._get_query_string()
        response = requests.get(url, verify=False)
        response.raise_for_status()
        # If the content is -1, our query was invalid
        assert response.content != "-1"
        # TODO: Return a list of tickets


class TicketSearcher:

    def __init__(self):
        self.query = None
        self.train_filter = None
        self.sorter = None

    def filter_by_train(self, train_list):
        if self.train_filter is not None:
            return list(self.train_filter(train_list))
        else:
            return train_list

    def sort_trains(self, train_list):
        if self.sorter is not None:
            self.sorter.sort(train_list)

    def get_train_list(self):
        train_list = self.query.execute()
        train_list = self.filter_by_train(train_list)
        self.sort_trains(train_list)
        return train_list


class QueryResultParser:

    @staticmethod
    def convert_ticket_count(count_string):
        # For god's sake, 12306. For god's sake.
        # TODO: What does the * character mean?
        if count_string == "--":  # Not applicable (train doesn't have this type of ticket)
            return None
        if count_string == "有":  # Large amount of tickets remaining, count unknown
            return -1
        if count_string == "无":  # No tickets remaining
            return 0
        return int(count_string)

    @staticmethod
    def convert_ticket_type(type_string):
        return {
            "swz": data.TicketType.BUSINESS,
            "tz": data.TicketType.SPECIAL,
            "zy": data.TicketType.FIRST_CLASS,
            "ze": data.TicketType.SECOND_CLASS,
            "gr": data.TicketType.SOFT_SLEEPER_PRO,
            "rw": data.TicketType.SOFT_SLEEPER,
            "yw": data.TicketType.HARD_SLEEPER,
            "rz": data.TicketType.SOFT_SEAT,
            "yz": data.TicketType.HARD_SEAT,
            "wz": data.TicketType.NO_SEAT,
            "qt": data.TicketType.OTHER
        }[type_string]