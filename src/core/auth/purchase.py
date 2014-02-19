# -*- coding: utf-8 -*-
import urllib.parse
from core.enums import TicketPricing, TicketDirection
from core.errors import UnfinishedTransactionError, InvalidRequestError, PurchaseFailedError
from core.auth.captcha import Captcha, CaptchaType
from core.data.credentials import Credentials
from core import common, webrequest, logger


class TicketPurchaser:
    def __init__(self, cookies):
        self.__cookies = cookies
        self.direction = TicketDirection.ONE_WAY
        self.pricing = TicketPricing.NORMAL
        self.train = None

    def __get_purchase_captcha(self, submit_token):
        check_params = self.__get_captcha_check_params(submit_token)
        return Captcha(CaptchaType.PURCHASE, self.__cookies, check_params=check_params)

    @staticmethod
    def __get_captcha_check_params(submit_token):
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "_json_att": ""
        }

    def __get_purchase_submit_params(self):
        return {
            "back_train_date": common.date_to_str(self.train.departure_time.date()),  # TODO
            "purpose_codes": self.pricing,
            "query_from_station_name": self.train.departure_station.name,
            "query_to_station_name": self.train.destination_station.name,
            "secretStr": urllib.parse.unquote(self.train.secret_key),
            "tour_flag": self.direction,
            "train_date": common.date_to_str(self.train.departure_time.date()),
            "undefined": ""
        }

    @staticmethod
    def __get_passenger_query_params(submit_token):
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "_json_att": ""
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
            seat_type="M",
            ticket_type="1",
            phone_no=passenger.phone_number
        )
        old_passenger_str = "_".join(map(lambda x: format_func(x, old_format), passenger_list)) + "_"
        new_passenger_str = "_".join(map(lambda x: format_func(x, new_format), passenger_list))
        return old_passenger_str, new_passenger_str

    def __get_check_order_params(self, passenger_list, submit_token, captcha_answer):
        old_pass_str, new_pass_str = self.__get_passenger_strs(passenger_list)
        return {
            "REPEAT_SUBMIT_TOKEN": submit_token,
            "_json_att": "",
            "bed_level_order_num": "000000000000000000000000000000",
            "cancel_flag": "2",
            "oldPassengerStr": old_pass_str,
            "passengerTicketStr": new_pass_str,
            "randCode": captcha_answer,
            "tour_flag": self.direction
        }

    def __get_purchase_confirm_url(self):
        return {
            TicketDirection.ONE_WAY: "https://kyfw.12306.cn/otn/confirmPassenger/initDc",
            TicketDirection.ROUND_TRIP: "https://kyfw.12306.cn/otn/confirmPassenger/initWc"
        }[self.direction]

    def __get_state_vars(self, url):
        # WARNING: VERY HACKY THINGS AHEAD
        # (and I'm not even using regex! >_<)
        cookies = self.__cookies
        response = webrequest.get(url, cookies=cookies, params={"_json_att": ""})
        # We're reading the entire page contents into memory.
        # This is a little bit inefficient, since the state
        # vars are always near the top of the page.

        # Text content is as follows:
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

        # I personally would rather just eval the JS and
        # get the values directly, but would rather not
        # use another dependency to do it, so we just
        # parse the string the hacky way. Honestly though,
        # I doubt the internal code to build these vars
        # is any better than this, knowing 12306...
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
                # Only going to handle null and single-quote strings
                # so far; if anything changes, well... we're screwed.
                # That means no expressions or anything like that.
                assert False
        return state_dict

    def __submit_order_request(self):
        url = "https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest"
        params = self.__get_purchase_submit_params()
        cookies = self.__cookies
        json = webrequest.post_json(url, params=params, cookies=cookies)
        if json["status"] is not True:
            # TODO: is this right?
            messages = json["messages"]
            for message in messages:
                if str(message).startswith("您还有未处理的订单"):
                    raise UnfinishedTransactionError()
            raise InvalidRequestError(common.join_list(messages))

    def __get_passenger_list(self, submit_token):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs"
        params = self.__get_passenger_query_params(submit_token)
        cookies = self.__cookies
        json = webrequest.post_json(url, params=params, cookies=cookies)
        passenger_data_list = json["data"]["normal_passengers"]
        logger.debug("Fetched passenger list ({0} passengers)".format(len(passenger_data_list)))
        return [Credentials(data) for data in passenger_data_list]

    def __check_order_info(self, passenger_list, submit_token, captcha_answer):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo"
        params = self.__get_check_order_params(passenger_list, submit_token, captcha_answer)
        json = webrequest.post_json(url, params=params)
        webrequest.check_json_flag(json, "data", "submitStatus", exception=PurchaseFailedError)

    def __get_queue_count(self):
        pass

    def purchase_tickets(self, pasenger_selector, captcha_solver):
        self.__submit_order_request()
        purchase_url = self.__get_purchase_confirm_url()
        submit_token = self.__get_state_vars(purchase_url)["globalRepeatSubmitToken"]
        passenger_list = self.__get_passenger_list(submit_token)
        selected_passengers = pasenger_selector(passenger_list)
        captcha = self.__get_purchase_captcha(submit_token)
        captcha_answer = captcha.solve(captcha_solver).answer
        self.__check_order_info(selected_passengers, submit_token, captcha_answer)
