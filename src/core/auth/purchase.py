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
from core.auth.authable import Authable
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


class TicketSelectionMap:
    # TODO: Implement
    pass


class PurchaseData:
    def __init__(self, submit_token, purchase_key):
        self.submit_token = submit_token
        self.purchase_key = purchase_key
        self.ticket_map = None
        self.old_passenger_str = None
        self.new_passenger_str = None

    def update_passenger_strs(self):
        if self.ticket_map is None or len(self.ticket_map) == 0:
            raise InvalidOperationError("No passengers selected")
        for ticket in self.ticket_map.values():
            if ticket.status != TicketStatus.NORMAL:
                raise InvalidOperationError("Invalid ticket selection")

        old_format = "{name},{id_type},{id_no},{passenger_type}"
        new_format = "{seat_type},0,{ticket_type},{name},{id_type},{id_no},{phone_no},N"
        format_func = lambda passenger, format_str: format_str.format(
            name=passenger.name,
            id_type=passenger.id_type,
            id_no=passenger.id_number,
            passenger_type=passenger.type,
            seat_type=TicketType.ID_LOOKUP[self.ticket_map[passenger].type],
            ticket_type=passenger.type,
            phone_no=passenger.phone_number
        )
        self.old_passenger_str = "_".join(map(lambda x: format_func(x, old_format), self.ticket_map)) + "_"
        self.new_passenger_str = "_".join(map(lambda x: format_func(x, new_format), self.ticket_map))


class TicketPurchaser(Authable):
    def __init__(self, cookies):
        super(TicketPurchaser, self).__init__(cookies, "purchase")
        self.pricing = TicketPricing.NORMAL
        self.train = None
        self.queue_callback = None

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

    def __get_check_order_data(self, purchase_data):
        return {
            "REPEAT_SUBMIT_TOKEN": purchase_data.submit_token,
            "bed_level_order_num": "000000000000000000000000000000",
            "cancel_flag": "2",
            "oldPassengerStr": purchase_data.old_passenger_str,
            "passengerTicketStr": purchase_data.new_passenger_str,
            "randCode": self.captcha.answer,
            "tour_flag": "dc"
        }

    def __get_queue_count_data(self, purchase_data):
        return {
            "REPEAT_SUBMIT_TOKEN": purchase_data.submit_token,
            "fromStationTelecode": self.train.departure_station.id,
            "toStationTelecode": self.train.destination_station.id,
            "leftTicket": self.train.data["ticket_count"],
            "purpose_codes": TicketPricing.PURCHASE_LOOKUP[self.train.pricing],
            # Relying on the fact that the first character of
            # the new-type passenger string is a ticket type ID.
            "seatType": purchase_data.new_passenger_str[0],
            "stationTrainCode": self.train.name,
            "train_no": self.train.id,
            "train_date": self.__get_javascript_date(self.train.departure_time)
        }

    def __get_confirm_purchase_data(self, purchase_data):
        return {
            "REPEAT_SUBMIT_TOKEN": purchase_data.submit_token,
            "key_check_isChange": purchase_data.purchase_key,
            "train_location": self.train.data["location_code"],
            "leftTicketStr": self.train.data["ticket_count"],
            "purpose_codes": TicketPricing.PURCHASE_LOOKUP[self.train.pricing],
            "oldPassengerStr": purchase_data.old_passenger_str,
            "passengerTicketStr": purchase_data.new_passenger_str,
            "randCode": self.captcha.answer
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
    def __get_javascript_date(date):
        return date.strftime("%a %b %d %Y 00:00:00 GMT+0800 (China Standard Time)")

    @staticmethod
    def __get_submit_token(text):
        return re.match(".*var\s+globalRepeatSubmitToken\s*=\s*['\"]([^'\"]*).*", text, flags=re.S).group(1)

    @staticmethod
    def __get_purchase_key(text):
        return re.match(".*['\"]key_check_isChange['\"]\s*:\s*['\"]([^'\"]*).*", text, flags=re.S).group(1)

    def __get_purchase_page(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/initDc"
        response = webrequest.post(url, cookies=self.cookies)
        return response.text

    def __submit_order_request(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest"
        data = self.__get_purchase_submit_data()
        try:
            webrequest.post_json(url, data=data, cookies=self.cookies)
        except RequestError as ex:
            msg = ex.args[0]
            if msg.startswith("您还有未处理的订单"):
                raise UnfinishedTransactionError() from ex
            if msg.startswith("车票信息已过期"):
                raise DataExpiredError() from ex
            raise

    def __check_order_info(self, purchase_data):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo"
        data = self.__get_check_order_data(purchase_data)
        json = webrequest.post_json(url, data=data, cookies=self.cookies)
        if not json["data"].get_bool("submitStatus"):
            json.raise_error(json["data"]["errMsg"])

    def __get_queue_count(self, purchase_data):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount"
        data = self.__get_queue_count_data(purchase_data)
        json = webrequest.post_json(url, data=data, cookies=self.cookies)
        if json["data"].get_bool("op_2"):
            raise NotEnoughTicketsError()
        queue_length = int(json["data"]["countT"])
        if queue_length > 0:
            logger.debug("{0} people left in queue".format(queue_length))

    def __confirm_purchase(self, purchase_data):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue"
        data = self.__get_confirm_purchase_data(purchase_data)
        json = webrequest.post_json(url, data=data, cookies=self.cookies)
        if not json["data"].get_bool("submitStatus"):
            json.raise_error(json["data"]["errMsg"])

    def __get_queue_data(self, submit_token):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime"
        params = self.__get_queue_time_params(submit_token)
        json = webrequest.get_json(url, params=params, cookies=self.cookies)
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
        json = webrequest.post_json(url, data=data, cookies=self.cookies)
        json["data"].assert_true("submitStatus")

    def __get_order_id(self, submit_token):
        order_id = self.__wait_for_queue(submit_token, self.queue_callback)
        self.__get_queue_result(submit_token, order_id)
        return order_id

    def get_passenger_list(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs"
        json = webrequest.post_json(url, cookies=self.cookies)
        passenger_data_list = json["data"]["normal_passengers"]
        logger.debug("Fetched passenger list ({0} passengers)".format(len(passenger_data_list)))
        return [Passenger(data) for data in passenger_data_list]

    def begin_purchase(self):
        if not self.train.can_buy:
            raise InvalidOperationError("No tickets available for purchase")

        logger.debug("Purchasing tickets for train " + self.train.name)

        # Begin purchase
        self.__submit_order_request()

        # Parse page for tokens
        purchase_page = self.__get_purchase_page()
        submit_token = self.__get_submit_token(purchase_page)
        purchase_key = self.__get_purchase_key(purchase_page)
        return PurchaseData(submit_token, purchase_key)

    @Authable.consumes_captcha()
    def complete_purchase(self, purchase_data):
        # Generate passenger strs
        purchase_data.update_passenger_strs()

        # Confirm purchase
        self.__check_order_info(purchase_data)
        self.__get_queue_count(purchase_data)
        self.__confirm_purchase(purchase_data)

        # Wait for order ID
        order_id = self.__get_order_id(purchase_data.submit_token)
        return order_id