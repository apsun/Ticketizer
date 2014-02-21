# -*- coding: utf-8 -*-
import urllib.parse
from core import common, webrequest, logger
from core.enums import TicketPricing, TicketDirection
from core.errors import UnfinishedTransactionError, DataExpiredError
from core.errors import PurchaseFailedError, InvalidRequestError, InvalidOperationError
from core.auth.captcha import Captcha, CaptchaType
from core.data.credentials import Credentials


class TicketPurchaser:
    def __init__(self, cookies):
        self.__cookies = cookies
        self.__submit_token = None
        self.direction = TicketDirection.ONE_WAY
        self.pricing = TicketPricing.NORMAL
        self.train = None

    def __get_captcha_check_params(self):
        return {
            "REPEAT_SUBMIT_TOKEN": self.__submit_token
        }

    def __get_passenger_query_data(self):
        return {
            "REPEAT_SUBMIT_TOKEN": self.__submit_token
        }

    def __get_purchase_submit_data(self):
        return {
            "back_train_date": common.date_to_str(self.train.departure_time.date()),  # TODO
            "purpose_codes": self.pricing,
            "query_from_station_name": self.train.departure_station.name,
            "query_to_station_name": self.train.destination_station.name,
            "secretStr": urllib.parse.unquote(self.train.secret_key),
            "tour_flag": self.direction,
            "train_date": common.date_to_str(self.train.departure_time.date())
        }

    @staticmethod
    def __get_passenger_strs(passenger_list):
        old_format = "{name},{id_type},{id_no},{passenger_type}"
        new_format = "{seat_type},0,{ticket_type},{name},{id_type},{id_no},{phone_no},N"
        format_func = lambda passenger, format_str: format_str.format(
            name=passenger.name,
            id_type=passenger.id_type,
            id_no=passenger.id_number,
            passenger_type="1",  # TODO
            seat_type="2",
            ticket_type="1",
            phone_no=passenger.phone_number
        )
        old_passenger_str = "_".join(map(lambda x: format_func(x, old_format), passenger_list)) + "_"
        new_passenger_str = "_".join(map(lambda x: format_func(x, new_format), passenger_list))
        return old_passenger_str, new_passenger_str

    def __get_check_order_data(self, passengers, captcha):
        old_pass_str, new_pass_str = self.__get_passenger_strs(passengers)
        return {
            "REPEAT_SUBMIT_TOKEN": self.__submit_token,
            "bed_level_order_num": "000000000000000000000000000000",
            "cancel_flag": "2",
            "oldPassengerStr": old_pass_str,
            "passengerTicketStr": new_pass_str,
            "randCode": captcha.answer,
            "tour_flag": self.direction
        }

    def __get_purchase_confirm_url(self):
        return {
            TicketDirection.ONE_WAY: "https://kyfw.12306.cn/otn/confirmPassenger/initDc",
            TicketDirection.ROUND_TRIP: "https://kyfw.12306.cn/otn/confirmPassenger/initWc"
        }[self.direction]

    def __get_state_vars(self, url):
        response = webrequest.post(url, cookies=self.__cookies)

        # TODO: Don't load entire contents of page into memory; stream the
        # TODO: data until the state var block is found and load that region only.
        # TODO: This can save a bit of memory (although not much...)

        # Text content of response is as follows:
        # (note the space on each line other than the first)
        # ...
        # /*<![CDATA[*/
        #  var ctx='/otn/';
        #  var globalRepeatSubmitToken = 'hex string';
        #  var global_lang = 'zh_CN';
        #  var sessionInit = 'username';
        #  var isShowNotice = null;
        #  /*]]>*/
        # ...
        state_js_lines = common.between(response.text, "/*<![CDATA[*/\n", "\n /*]]>*/").splitlines()
        state_dict = {}
        for line in state_js_lines:
            var_name_index = line.index(" var ") + len(" var ")
            var_name_index_end = line.index("=", var_name_index)
            var_name = line[var_name_index:var_name_index_end].strip()
            var_value_index = var_name_index_end + len("=")
            var_value_index_end = line.index(";")
            var_value_token = line[var_value_index:var_value_index_end].strip()
            if var_value_token == "null":
                state_dict[var_name] = None
                logger.debug("Got state var: " + var_name + " = null")
            elif var_value_token[0] == "'" and var_value_token[-1] == "'":
                var_value = var_value_token[1:-1]
                state_dict[var_name] = var_value
                logger.debug("Got state var: " + var_name + " = '" + var_value + "'")
            else:
                # Only going to handle null and single-quoted strings
                # so far; if anything changes, well... we're screwed.
                # That means no expressions or anything like that.
                assert False
        return state_dict

    def __submit_order_request(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest"
        data = self.__get_purchase_submit_data()
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        if json["status"] is not True:
            messages = json["messages"]
            for message in messages:
                if message.startswith("您还有未处理的订单"):
                    raise UnfinishedTransactionError()
                elif message.startswith("车票信息已过期"):
                    raise DataExpiredError()
            raise InvalidRequestError(common.join_list(messages))

    def __check_order_info(self, passengers, captcha):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo"
        data = self.__get_check_order_data(passengers, captcha)
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        webrequest.check_json_flag(json, "data", "submitStatus", exception=PurchaseFailedError)

    def __get_queue_count(self):
        pass

    def __ensure_order_submitted(self):
        if self.__submit_token is None:
            raise InvalidOperationError("Order has not been submitted yet")

    def get_purchase_captcha(self):
        self.__ensure_order_submitted()
        check_params = self.__get_captcha_check_params()
        return Captcha(CaptchaType.PURCHASE, self.__cookies, check_params=check_params)

    def get_passenger_list(self):
        self.__ensure_order_submitted()
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs"
        data = self.__get_passenger_query_data()
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        passenger_data_list = json["data"]["normal_passengers"]
        logger.debug("Fetched passenger list ({0} passengers)".format(len(passenger_data_list)))
        return [Credentials(data) for data in passenger_data_list]

    def begin_purchase(self):
        # Due to the design of the 12306 API, we have to submit the
        # purchase before getting the captcha. To avoid having to use
        # a callback pattern to solve the captcha, the purchase process
        # is split into 2 steps.

        # How to use this API in a nutshell:
        # 1. Submit the order
        #    -> begin_purchase()
        # 2. Get the captcha and passenger list
        #    -> get_purchase_captcha() and get_passenger_list()
        # 3. Solve the captcha and select passengers
        #    -> (this part is for the client to implement)
        # 4. Complete the order
        #    -> continue_purchase()

        # Note: If continue_purchase() throws an exception,
        # you must call begin_purchase() again!
        logger.debug("Purchasing tickets for train " + self.train.name)
        self.__submit_order_request()
        purchase_url = self.__get_purchase_confirm_url()
        self.__submit_token = self.__get_state_vars(purchase_url)["globalRepeatSubmitToken"]

    def continue_purchase(self, passengers, captcha):
        self.__ensure_order_submitted()
        try:
            self.__check_order_info(passengers, captcha)
            # TODO: FINISH THIS
        except:
            self.__submit_token = None
            raise