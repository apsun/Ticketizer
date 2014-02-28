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

from core.enums import PassengerType, IdentificationType


class Passenger:
    def __init__(self, passenger_data):
        self.name = passenger_data["passenger_name"]
        self.gender = passenger_data["sex_code"]
        self.id_type = passenger_data["passenger_id_type_code"]
        self.id_number = passenger_data["passenger_id_no"]
        self.type = passenger_data["passenger_type"]
        self.phone_number = passenger_data["mobile_no"]

    def __str__(self):
        return "{0} (gender: {1}, type: {2}, ID: {3}->{4})".format(
            self.name,
            self.gender,
            PassengerType.TEXT_LOOKUP[self.type],
            IdentificationType.TEXT_LOOKUP[self.id_type],
            self.id_number)

    def __repr__(self):
        return str(self)