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
    def __init__(self, passenger_data=None):
        if passenger_data is not None:
            self.name = passenger_data["passenger_name"]
            self.gender = passenger_data["sex_code"]
            self.id_type = passenger_data["passenger_id_type_code"]
            self.id_number = passenger_data["passenger_id_no"]
            self.type = passenger_data["passenger_type"]
            self.phone_number = passenger_data["mobile_no"]
        else:
            self.name = None
            self.gender = None
            self.id_type = None
            self.id_number = None
            self.type = None
            self.phone_number = None

    def __eq__(self, other):
        if not isinstance(other, Passenger):
            return False
        return self.name == other.name and \
            self.gender == other.gender and \
            self.id_type == other.id_type and \
            self.id_number == other.id_number and \
            self.type == other.type and \
            self.phone_number == other.phone_number

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "{0} (gender: {1}, type: {2}, ID: <{3}> {4})".format(
            self.name,
            self.gender,
            PassengerType.TEXT_LOOKUP[self.type],
            IdentificationType.TEXT_LOOKUP[self.id_type],
            self.id_number)