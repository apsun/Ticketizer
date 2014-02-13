# -*- coding: utf-8 -*-
from core.processing.containers import ToggleList


class TrainSorter:
    def __init__(self):
        self.favorites = ToggleList()
        self.sorters = []
        self.reverse = False

    def sort(self, train_list):
        for sorter in self.sorters:
            sorter(train_list, self.reverse)

    def sort_by_number(self, train_list, reverse):
        # Note: does NOT take into account the train type!
        # To sort by the type as well, call sort_by_type after this!
        type_stripper = lambda x: x.name[1:] if str.isalpha(x.name[0]) else x.name
        self.__sort_by_key(train_list, lambda x: int(type_stripper(x)), reverse)

    def sort_by_type(self, train_list, reverse):
        self.__sort_by_key(train_list, lambda x: x.type, reverse)

    def sort_by_departure_time(self, train_list, reverse):
        self.__sort_by_key(train_list, lambda x: x.departure_time, reverse)

    def sort_by_arrival_time(self, train_list, reverse):
        self.__sort_by_key(train_list, lambda x: x.arrival_time, reverse)

    def sort_by_duration(self, train_list, reverse):
        self.__sort_by_key(train_list, lambda x: x.duration, reverse)

    def sort_by_price(self, train_list, reverse):
        # No idea why anyone would want to sort by maximum price, but whatever...
        # This method intelligently uses the min/max price of the train's tickets.
        # That means that doing an ascending sort and reversing is NOT the same as
        # doing a descending sort! It MIGHT be (if you're lucky), but not guaranteed!
        if reverse:
            ticket_price_func = lambda x: 0 if x.price is None else x.price
            train_price_func = lambda x: max(map(ticket_price_func, x.tickets))
        else:
            ticket_price_func = lambda x: float("inf") if x.price is None else x.price
            train_price_func = lambda x: min(map(ticket_price_func, x.tickets))
        self.__sort_by_key(train_list, train_price_func, reverse)

    def __sort_by_key(self, train_list, compare_key, reverse):
        # Sorts the train list using the specified key,
        # keeping "favorite" trains in the front.
        # The sorting algorithm used must be stable for this to work!
        train_list.sort(key=compare_key, reverse=reverse)
        train_list.sort(key=lambda x: 0 if self.favorites[x.name] else 1)