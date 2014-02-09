# -*- coding: utf-8 -*-
import datetime
import requests
from . import data
from . import logger
from . import common
from . import enums


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
        self._sort_by_key(train_list, self._type_key, reverse)

    @staticmethod
    def _type_key(train):
        types = enums.TrainType
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
        self.train_type_filter = enums.TrainType.ALL
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
        self.ticket_type_filter = enums.TicketType.ALL
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
    
    def filter(self, train_list):
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

    @staticmethod
    def _get_station_id(station):
        if isinstance(station, str):
            return station
        if isinstance(station, data.Station):
            return station.id
        raise TypeError("Station is not a string or a Station object")

    @staticmethod
    def _get_date_str(date):
        if isinstance(date, str):
            return date
        elif isinstance(date, datetime.date) or isinstance(date, datetime.datetime):
            return common.date_to_str(date)
        raise TypeError("Date is not a string, datetime, or date instance")

    @staticmethod
    def _parse_train_time(date_string, time_string):
        return datetime.datetime.strptime(date_string + " " + time_string, "%Y%m%d %H:%M")

    def _get_query_string(self):
        # WTF! Apparently the order of the params DOES MATTER; if you
        # mess up the order, you get an invalid result.
        # Instead of using the built-in method with dicts,
        # now we have to manually concatenate the query parameters.
        train_date = self._get_date_str(self.date)
        from_station = self._get_station_id(self.origin)
        to_station = self._get_station_id(self.destination)
        purpose_codes = self.type
        return "leftTicketDTO.train_date=%s&" \
               "leftTicketDTO.from_station=%s&" \
               "leftTicketDTO.to_station=%s&" \
               "purpose_codes=%s" % (train_date, from_station, to_station, purpose_codes)

    def _parse_query_results(self, train_json):
        # The format of each item is as follows:
        # "queryLeftNewDTO": { ... },
        # "secretStr": "...",
        # "buttonTextInfo": "..."
        train_data = train_json["queryLeftNewDTO"]
        train = data.Train()

        train.name = train_data["station_train_code"]
        train.id = train_data["train_no"]
        # Kind of hacky -- we're using the first character of the train's name
        train.type = enums.TrainType.REVERSE_ABBREVIATION_LOOKUP.get(train.name[0], enums.TrainType.OTHER)
        train.departure_station = self.origin
        train.arrival_station = self.destination
        train.departure_index = train_data["from_station_no"]
        train.arrival_index = train_data["to_station_no"]
        train.has_begun_selling = common.is_true(train_data["canWebBuy"])
        train.begin_selling_time = datetime.datetime.strptime(train_data["sale_time"], "%H%M").time()
        train.secret_key = train_json["secretStr"]
        train.departure_time = self._parse_train_time(train_data["start_train_date"], train_data["start_time"])
        train.duration = datetime.timedelta(minutes=int(train_data["lishiValue"]))
        train.arrival_time = train.departure_time + train.duration
        train.seat_types = train_data["seat_types"]
        for key, value in enums.TicketType.REVERSE_ABBREVIATION_LOOKUP.items():
            ticket = data.Ticket()
            ticket.count = data.TicketCount(train_data[key + "_num"])
            ticket.type = value
            train.tickets.append(ticket)
        return train

    def execute(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/query?" + self._get_query_string()
        response = requests.get(url, verify=False)
        response.raise_for_status()
        logger.debug("Got ticket list from {0} to {1} on {2}".format(
            self._get_station_id(self.origin),
            self._get_station_id(self.destination),
            self._get_date_str(self.date)
        ), response)
        json_data = common.read_json_data(response)
        return [self._parse_query_results(train_json) for train_json in json_data]


class TicketSearcher:

    def __init__(self):
        self.query = None
        self.filter = None
        self.sorter = None

    def filter_by_train(self, train_list):
        if self.filter is not None:
            return list(self.filter.filter(train_list))
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
