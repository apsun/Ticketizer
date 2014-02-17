# -*- coding: utf-8 -*-
from core.enums import PassengerType, IdentificationType


class Credentials:
    def __init__(self, passenger_data):
        self.name = passenger_data["passenger_name"]
        self.gender = passenger_data["sex_code"]
        self.id_type = passenger_data["passenger_id_type_code"]
        self.id_number = passenger_data["passenger_id_no"]
        self.type = passenger_data["passenger_type"]

    def __str__(self):
        return "{0} (gender: {1}, type: {2}, ID: {3}->{4})".format(
            self.name,
            self.gender,
            PassengerType.TEXT_LOOKUP[self.type],
            IdentificationType.TEXT_LOOKUP[self.id_type],
            self.id_number)