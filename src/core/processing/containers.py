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


class ValueRange:
    def __init__(self, lower=None, upper=None):
        self.lower = lower
        self.upper = upper

    def check(self, value):
        lower = self.lower
        upper = self.upper

        # Accept a lambda or func that returns
        # the actual value for lazy evaluation.
        if (lower is not None or upper is not None) and callable(value):
            value = value()

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


class BitFlags:
    def __init__(self, default_flags):
        self.__flags = default_flags

    def __setitem__(self, flag, enable):
        if enable:
            self.add(flag)
        else:
            self.remove(flag)

    def __getitem__(self, flag):
        return (self.__flags & flag) == flag

    def add(self, item):
        self.__flags |= item

    def add_range(self, items):
        for item in items:
            self.add(item)

    def remove(self, item):
        self.__flags &= ~item

    def remove_range(self, items):
        for item in items:
            self.remove(item)

    def clear(self):
        self.__flags = 0


class FlagSet:
    def __init__(self):
        self.__set = set()

    def __setitem__(self, item, value):
        if value:
            self.add(item)
        else:
            self.remove(item)

    def __getitem__(self, item):
        return item in self.__set

    def __iter__(self):
        for item in self.__set:
            yield item

    def add(self, item):
        self.__set.add(item)

    def add_range(self, items):
        for item in items:
            self.add(item)

    def remove(self, item):
        self.__set.remove(item)

    def remove_range(self, items):
        for item in items:
            self.remove(item)

    def clear(self):
        self.__set.clear()