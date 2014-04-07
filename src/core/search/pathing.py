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
from collections import OrderedDict
from core import timeconverter, logger, webrequest
from core.search.search import TrainQuery, TicketPricing, TicketDirection
from core.processing.containers import ValueRange, FlagSet


class StopPathSearch(Exception):
    pass


class MultiTrainPath:
    def __init__(self, train_list):
        self.train_list = train_list

    @property
    def departure_time(self):
        return self.train_list[0].departure_time

    @property
    def arrival_time(self):
        return self.train_list[-1].arrival_time

    @property
    def duration(self):
        return self.arrival_time - self.departure_time

    def __iter__(self):
        for train in self.train_list:
            yield train


class PathFinder:
    def __init__(self, station_list, path_selector):
        # A list of stations (used for querying the station list)
        self.__station_list = station_list
        # This is a callback function that takes a list of
        # trains and returns a selected train path
        self.path_selector = path_selector
        # The type of ticket pricing -- normal ("adult") or student
        self.pricing = TicketPricing.NORMAL
        # Whether to allow "fuzzy searching" for the overall
        # departure and destination stations.
        self.exact_departure_station = False
        self.exact_destination_station = False
        # Whether to require that all train transfers take place
        # in the same station -- that is, you will not have to travel
        # between train stations to transfer. Setting this to true
        # is HIGHLY RECOMMENDED unless you know what you are doing!
        self.exact_substations = True
        # If true, when searching for stations from, say, A->C,
        # a train that can go from A->C and A->B will only show
        # up once with the path A->C.
        self.only_show_longest_path = True
        # The time range (ValueRange<datetime.timedelta>) between successive trains.
        # Set a minimum that is long enough to allow you to get from one
        # train to the other, and a maximum to prevent waiting for too long.
        # Note that THIS VALUE IS REQUIRED, and is NOT a filter!
        self.transfer_time_range = ValueRange()
        # A list of stations to avoid
        self.station_blacklist = FlagSet()
        # (Optional) An instance of the TrainFilter class that
        # filters out unwanted trains. This filter is applied
        # BEFORE the "longest path only" filter, which can be
        # very useful in removing unbuyable trains.
        self.train_filter = None

    @staticmethod
    def __get_train_data_query_params(train):
        return [
            ("train_no", train.id),
            ("from_station_telecode", train.departure_station.id),
            ("to_station_telecode", train.destination_station.id),
            # Apparently you're not supposed to use the actual
            # train date here, not the date returned in the
            # train query data. And yes, they can be different.
            ("depart_date", timeconverter.date_to_str(train.data["alt_date"].strftime("%Y%m%d")))
        ]

    @staticmethod
    def __get_dates_between(date_start, date_end):
        if isinstance(date_start, datetime):
            date_start = date_start.date()
        if isinstance(date_end, datetime):
            date_end = date_end.date()
        for i in range((date_end - date_start).days + 1):
            yield date_start + timedelta(days=i)

    def __get_substations(self, train):
        # Gets stations in (train.departure, train.destination]
        url = "https://kyfw.12306.cn/otn/czxx/queryByTrainNo"
        params = self.__get_train_data_query_params(train)
        json = webrequest.get_json(url, params=params)
        json_station_list = json["data"]["data"]
        logger.debug("Fetched station data for train " + train.name)
        istart = None
        iend = len(json_station_list)
        for i in range(len(json_station_list)):
            is_in_path = json_station_list[i]["isEnabled"]
            if is_in_path and istart is None:
                istart = i
            elif not is_in_path and istart is not None:
                iend = i
                break
        assert istart is not None
        assert json_station_list[istart]["station_name"] == train.departure_station.name
        assert json_station_list[iend-1]["station_name"] == train.destination_station.name
        station_list = []
        for i in range(istart+1, iend-1):
            station_name = json_station_list[i]["station_name"]
            if self.station_blacklist[station_name]:
                continue
            station = self.__station_list.get_by_name(station_name)
            station_list.append(station)
        station_list.append(train.destination_station)
        return station_list

    def __get_path_recursive(self, train_list, station_list, query, is_first):
        # Note that the "example" train is passed in as the first
        # item in the train list. After our path has been built,
        # we have to remove this item from the list.
        prev_train = train_list[-1]
        last_station = station_list[-1]

        if is_first:
            query.exact_departure_station = self.exact_departure_station
            departure_station = prev_train.departure_station
            date_range = [prev_train.departure_time.date()]
        else:
            query.exact_departure_station = self.exact_substations
            departure_station = prev_train.destination_station
            date_range_begin = prev_train.arrival_time + self.transfer_time_range.lower
            date_range_end = prev_train.arrival_time + self.transfer_time_range.upper
            date_range = list(self.__get_dates_between(date_range_begin, date_range_end))

        query.departure_station = departure_station

        # Need to maintain a dict of train destination stations.
        # These destinations are the QUERIED stations, NOT the ones
        # returned by search queries, which can be fuzzy. This is
        # used to determine what stations remain in the trip.
        # Use an ordered dictionary to preserve station order,
        # which might be useful if the client doesn't sort the
        # results themselves.
        next_train_dict = OrderedDict()

        for next_station in station_list:
            # Make sure the destination fuzzy search option is set
            # correctly based on which station we're traveling to
            if next_station == last_station:
                query.exact_destination_station = self.exact_destination_station
            else:
                query.exact_destination_station = self.exact_substations

            query.destination_station = next_station

            # Our inter-train transfer period can span multiple days.
            # Generally, this is very rare, but it can happen anyways.
            # For example, if our train arrives at 11:30PM, and our
            # transfer time range is [10, 120] minutes, we want to
            # search for tickets on both the current and the next day.
            for date in date_range:
                query.date = date
                for next_train in query.execute():
                    transfer_time = next_train.departure_time - prev_train.arrival_time
                    # For the first train there's obviously no previous train to check
                    if not is_first and not self.transfer_time_range.check(transfer_time):
                        continue
                    if self.train_filter is not None and self.train_filter.check(next_train):
                        continue
                    if self.only_show_longest_path:
                        for train in next_train_dict:
                            if train.id == next_train.id and train.departure_time == next_train.departure_time:
                                # Found a clash, replace the old train.
                                # Technically, we should compare the station indices,
                                # but since we are looping in order from closest to
                                # furthest station, we can just replace the previous train.
                                # Since we don't iterate over anything after this,
                                # we can safely modify the collection in the loop.
                                next_train_dict.pop(train)
                                break
                    next_train_dict[next_train] = next_station

        # Oh no, there is no way to get from our current station to
        # the target destination station!
        if len(next_train_dict) == 0:
            logger.debug("No trains found in sub-path from {0} to {1}".format(
                departure_station.name, last_station.name))
            # Let the client handle no-result cases
            # return None

        while True:
            # Call the user-defined train selector function with the train list
            selected_train = self.path_selector(list(next_train_dict.keys()))

            # Accept None as a sentinel value to "undo" to the higher level
            # To prematurely exit the search, simply raise StopPathSearch
            # in the path selector function; get_path() will catch this
            # exception and return None to the caller.
            if selected_train is None:
                return None

            train_list.append(selected_train)

            # This is not the actual station that we are at, but the
            # one that was in the original train's station path, which
            # is obviously guaranteed to be in the station list.
            curr_station = next_train_dict[selected_train]

            # "Slice" off the stations that we have already passed
            remaining_stations = station_list[station_list.index(curr_station)+1:]

            # If there are no stations left, we are at our destination!
            if len(remaining_stations) == 0:
                return MultiTrainPath(train_list[1:])

            # Otherwise, we have to search in the remaining section of the trip
            next_search = self.__get_path_recursive(train_list, remaining_stations, query, False)

            # Note that at this point the query object has probably been
            # modified, so don't rely on it to store information across calls

            if next_search is not None:
                return next_search

            logger.debug("Undoing from {0} to {1}".format(
                query.departure_station.name, departure_station.name))

    def get_path(self, train):
        query = TrainQuery(self.__station_list)
        query.pricing = self.pricing
        query.direction = TicketDirection.ONE_WAY
        substations = self.__get_substations(train)
        try:
            return self.__get_path_recursive([train], substations, query, True)
        except StopPathSearch:
            return None