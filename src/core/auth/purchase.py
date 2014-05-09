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
#
# TODO: Return variables required to auto-open the purchase site
# TODO: Add not-logged-in error

import re
import urllib.parse
from core import timeconverter, webrequest, logger
from core.auth import captcha
from core.enums import TicketPricing, TicketType, TicketStatus
from core.jsonwrapper import RequestError
from core.data.passenger import Passenger


class StopPurchaseQueue(Exception):
    pass


class PurchaseFailedError(Exception):
    pass


class InvalidOperationError(Exception):
    pass


class UnfinishedTransactionError(PurchaseFailedError):
    pass


class DataExpiredError(PurchaseFailedError):
    pass


class NotEnoughTicketsError(PurchaseFailedError):
    pass


class NotLoggedInError(PurchaseFailedError):
    pass


class TicketPurchaser:
    def __init__(self, cookies):
        self.__cookies = cookies
        self.pricing = TicketPricing.NORMAL
        self.train = None

    def __get_purchase_submit_data(self):
        return {
            "back_train_date": timeconverter.date_to_str(self.train.departure_time.date()),
            "purpose_codes": TicketPricing.PURCHASE_LOOKUP[self.pricing],
            "query_from_station_name": self.train.departure_station.name,
            "query_to_station_name": self.train.destination_station.name,
            # Need to unescape this string or else it will become
            # double-escaped when we send the request.
            "secretStr": urllib.parse.unquote(self.train.data["secret_key"]),
            "tour_flag": "dc",
            "train_date": timeconverter.date_to_str(self.train.departure_time.date())
        }

    @staticmethod
    def __get_check_order_data(passenger_strs, submit_token, captcha_answer):
        old_pass_str, new_pass_str = passenger_strs
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "bed_level_order_num": "000000000000000000000000000000",
            "cancel_flag": "2",
            "oldPassengerStr": old_pass_str,
            "passengerTicketStr": new_pass_str,
            "randCode": captcha_answer,
            "tour_flag": "dc"
        }

    def __get_queue_count_data(self, passenger_strs, submit_token):
        date_str = self.train.departure_time.date().strftime(
            "%a %b %d %Y 00:00:00 GMT+0800 (China Standard Time)")
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "fromStationTelecode": self.train.departure_station.id,
            "toStationTelecode": self.train.destination_station.id,
            "leftTicket": self.train.data["ticket_count"],
            "purpose_codes": TicketPricing.PURCHASE_LOOKUP[self.train.pricing],
            # Relying on the fact that the first character of
            # the new-type passenger string is a ticket type ID.
            "seatType": passenger_strs[1][0],
            "stationTrainCode": self.train.name,
            "train_no": self.train.id,
            "train_date": date_str
        }

    def __get_confirm_purchase_data(self, passenger_strs, submit_token, purchase_key, captcha_answer):
        old_pass_str, new_pass_str = passenger_strs
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "key_check_isChange": purchase_key,
            "train_location": self.train.data["location_code"],
            "leftTicketStr": self.train.data["ticket_count"],
            "purpose_codes": TicketPricing.PURCHASE_LOOKUP[self.train.pricing],
            "oldPassengerStr": old_pass_str,
            "passengerTicketStr": new_pass_str,
            "randCode": captcha_answer
        }

    @staticmethod
    def __get_queue_time_params(submit_token):
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "tourFlag": "dc"
        }

    @staticmethod
    def __get_queue_result_data(submit_token, order_id):
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "orderSequence_no": order_id
        }

    @staticmethod
    def __get_passenger_strs(passenger_dict):
        old_format = "{name},{id_type},{id_no},{passenger_type}"
        new_format = "{seat_type},0,{ticket_type},{name},{id_type},{id_no},{phone_no},N"
        format_func = lambda passenger, format_str: format_str.format(
            name=passenger.name,
            id_type=passenger.id_type,
            id_no=passenger.id_number,
            passenger_type=passenger.type,
            seat_type=TicketType.ID_LOOKUP[passenger_dict[passenger].type],
            ticket_type=passenger.type,
            phone_no=passenger.phone_number
        )
        old_passenger_str = "_".join(map(lambda x: format_func(x, old_format), passenger_dict)) + "_"
        new_passenger_str = "_".join(map(lambda x: format_func(x, new_format), passenger_dict))
        return old_passenger_str, new_passenger_str

    @staticmethod
    def __get_submit_token(text):
        return re.match(".*var\s+globalRepeatSubmitToken\s*=\s*['\"]([^'\"]*).*", text, flags=re.S).group(1)

    @staticmethod
    def __get_purchase_key(text):
        return re.match(".*['\"]key_check_isChange['\"]\s*:\s*['\"]([^'\"]*).*", text, flags=re.S).group(1)

    def __get_purchase_page(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/initDc"
        response = webrequest.post(url, cookies=self.__cookies)
        return response.text

    def __submit_order_request(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest"
        data = self.__get_purchase_submit_data()
        try:
            webrequest.post_json(url, data=data, cookies=self.__cookies)
        except RequestError as ex:
            msg = ex.args[0]
            if msg.startswith("您还有未处理的订单"):
                raise UnfinishedTransactionError() from ex
            if msg.startswith("车票信息已过期"):
                raise DataExpiredError() from ex
            raise

    def __check_order_info(self, passenger_strs, submit_token, captcha_answer):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo"
        data = self.__get_check_order_data(passenger_strs, submit_token, captcha_answer)
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        json["data"].assert_true("submitStatus")

    def __get_queue_count(self, passenger_dict, submit_token):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount"
        data = self.__get_queue_count_data(passenger_dict, submit_token)
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        if json["data"].get_bool("op_2"):
            raise NotEnoughTicketsError()
        queue_length = int(json["data"]["countT"])
        if queue_length > 0:
            logger.debug("{0} people left in queue".format(queue_length))

    def __confirm_purchase(self, passenger_strs, submit_token, purchase_key, captcha_answer):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue"
        data = self.__get_confirm_purchase_data(passenger_strs, submit_token, purchase_key, captcha_answer)
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        json["data"].assert_true("submitStatus")

    def __get_queue_data(self, submit_token):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime"
        params = self.__get_queue_time_params(submit_token)
        json = webrequest.get_json(url, params=params, cookies=self.__cookies)
        json["data"].assert_true("queryOrderWaitTimeStatus")
        return json["data"]["waitCount"], json["data"].get("orderId")

    def __wait_for_queue(self, submit_token, callback):
        while True:
            length, order_id = self.__get_queue_data(submit_token)
            if length == 0 and order_id is not None:
                return order_id
            callback(length)

    def __get_queue_result(self, submit_token, order_id):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue"
        data = self.__get_queue_result_data(submit_token, order_id)
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        json["data"].assert_true("submitStatus")

    def __get_order_id(self, submit_token, callback):
        order_id = self.__wait_for_queue(submit_token, callback)
        self.__get_queue_result(submit_token, order_id)
        return order_id

    @staticmethod
    def __ensure_tickets_valid(passenger_dict):
        if len(passenger_dict) == 0:
            raise InvalidOperationError("No passengers selected")
        for ticket in passenger_dict.values():
            if ticket.status != TicketStatus.NORMAL:
                raise InvalidOperationError("Invalid ticket selection")

    def get_passenger_list(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs"
        json = webrequest.post_json(url, cookies=self.__cookies)
        passenger_data_list = json["data"]["normal_passengers"]
        logger.debug("Fetched passenger list ({0} passengers)".format(len(passenger_data_list)))
        return [Passenger(data) for data in passenger_data_list]

    def execute(self, passengers, queue_callback):
        if not self.train.can_buy:
            raise InvalidOperationError("No tickets available for purchase")
        self.__ensure_tickets_valid(passengers)
        passenger_strs = self.__get_passenger_strs(passengers)

        logger.debug("Purchasing tickets for train " + self.train.name)

        # Begin purchase
        self.__submit_order_request()

        # Parse page for tokens
        purchase_page = self.__get_purchase_page()
        submit_token = self.__get_submit_token(purchase_page)
        purchase_key = self.__get_purchase_key(purchase_page)

        # Solve purchase captcha
        captcha_answer = captcha.solve_purchase_captcha(self.__cookies)

        # Confirm purchase
        self.__check_order_info(passenger_strs, submit_token, captcha_answer)
        self.__get_queue_count(passenger_strs, submit_token)
        self.__confirm_purchase(passenger_strs, submit_token, purchase_key, captcha_answer)

        order_id = self.__get_order_id(submit_token, queue_callback)
        return order_id