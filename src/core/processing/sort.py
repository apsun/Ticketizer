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

from core.processing.containers import FlagSet


class TrainSorter:
    def __init__(self):
        self.favorites = FlagSet()
        self.sort_methods = []
        self.reverse = False

    def sort(self, train_list):
        for sorter in self.sort_methods:
            sorter(train_list)

    def sort_by_number(self, train_list):
        # Note: does NOT take into account the train type!
        # To sort by the type as well, call sort_by_type after this!
        type_stripper = lambda x: x.name[1:] if str.isalpha(x.name[0]) else x.name
        self.__sort_by_key(train_list, lambda x: int(type_stripper(x)))

    def sort_by_type(self, train_list):
        self.__sort_by_key(train_list, lambda x: x.type)

    def sort_by_departure_time(self, train_list):
        self.__sort_by_key(train_list, lambda x: x.departure_time)

    def sort_by_arrival_time(self, train_list):
        self.__sort_by_key(train_list, lambda x: x.arrival_time)

    def sort_by_duration(self, train_list):
        self.__sort_by_key(train_list, lambda x: x.duration)

    def sort_by_price(self, train_list):
        # No idea why anyone would want to sort by maximum price, but whatever...
        # This method intelligently uses the min/max price of the train's tickets.
        # That means that doing an ascending sort and reversing is NOT the same as
        # doing a descending sort! It MIGHT be (if you're lucky), but not guaranteed!
        if self.reverse:
            ticket_price_func = lambda x: 0 if x.price is None else x.price
            train_price_func = lambda x: max(map(ticket_price_func, x.tickets))
        else:
            ticket_price_func = lambda x: float("inf") if x.price is None else x.price
            train_price_func = lambda x: min(map(ticket_price_func, x.tickets))
        self.__sort_by_key(train_list, train_price_func)

    def __sort_by_key(self, train_list, compare_key):
        # Sorts the train list using the specified key,
        # keeping "favorite" trains in the front.
        # The sorting algorithm used must be stable for this to work!
        train_list.sort(key=compare_key, reverse=self.reverse)
        train_list.sort(key=lambda x: 0 if self.favorites[x.name] else 1)