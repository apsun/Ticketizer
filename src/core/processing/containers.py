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
    def __init__(self, default_flags, all_flags=None, no_flags=None):
        self.__flags = default_flags
        self.__all = all_flags
        self.__none = no_flags

    def __setitem__(self, flag, enable):
        if enable:
            self.__flags |= flag
        else:
            self.__flags &= ~flag

    def __getitem__(self, flag):
        return (self.__flags & flag) == flag

    def enable_all(self):
        if self.__all is None:
            raise ValueError("No full flag set provided in constructor")
        self.__flags = self.__all

    def disable_all(self):
        if self.__none is None:
            raise ValueError("No empty flag set provided in constructor")
        self.__flags = self.__none


class FlagSet:
    def __init__(self):
        self.__list = {}

    def __setitem__(self, item, value):
        self.__list[item] = value

    def __getitem__(self, item):
        return self.__list.get(item, False)

    def __iter__(self):
        for key, value in self.__list.items():
            if value:
                yield key

    def add(self, item):
        self[item] = True

    def remove(self, item):
        self[item] = False

    def clear(self):
        self.__list.clear()