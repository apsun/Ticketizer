# TODO: Merge this into the login module
import urllib.parse
from core import common, logger, webrequest
from core.errors import UnfinishedTransactionError, InvalidRequestError
from core.enums import TicketPricing, TicketDirection, PassengerType, IdentificationType
from core.data.credentials import Credentials


class Buyer:
    def __init__(self, train, login_manager):
        self.direction = TicketDirection.ONE_WAY
        self.pricing = TicketPricing.NORMAL
        self.train = train
        self.login_manager = login_manager
        self.passenger_selector = None

    def __get_submit_params(self):
        return {
            "back_train_date": common.date_to_str(self.train.departure_time.date()),
            "purpose_codes": self.pricing,
            "query_from_station_name": self.train.departure_station.name,
            "query_to_station_name": self.train.destination_station.name,
            "secretStr": urllib.parse.unquote(self.train.secret_key),
            "tour_flag": self.direction,
            "train_date": common.date_to_str(self.train.departure_time.date())
        }

    def __get_passenger_query_params(self):
        return {
            "REPEAT_SUBMIT_TOKEN": self.__get_state_vars()["globalRepeatSubmitToken"]
        }

    def __get_purchase_confirm_url(self):
        return {
            TicketDirection.ONE_WAY: "https://kyfw.12306.cn/otn/confirmPassenger/initDc",
            TicketDirection.ROUND_TRIP: "https://kyfw.12306.cn/otn/confirmPassenger/initWc"
        }[self.direction]

    def __get_state_vars(self):
        # WARNING: VERY HACKY THINGS AHEAD
        # (and I'm not even using regex! >_<)
        url = self.__get_purchase_confirm_url()
        cookies = None  # TODO: FIX
        response = webrequest.get(url, cookies=cookies)
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
        params = self.__get_submit_params()
        cookies = None  # TODO: FIX
        response = webrequest.post(url, params=params, cookies=cookies)
        json = common.read_json(response)
        success = json["status"] is True
        if not success:
            messages = json["messages"]
            for message in messages:
                if str(message).startswith("您还有未处理的订单"):
                    raise UnfinishedTransactionError()
            raise InvalidRequestError(common.join_list(messages))
        logger.debug("Submitted ticket purchase request", response)

    def __get_passenger_list(self):
        url = "https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs"
        params = self.__get_passenger_query_params()
        cookies = None  # TODO: FIX
        response = webrequest.post(url, params=params, cookies=cookies)
        json_data = common.read_json_data(response)
        passenger_data_list = json_data["normal_passengers"]
        logger.debug("Fetched passenger list ({0} passengers)".format(len(passenger_data_list)))
        return [Credentials(data) for data in passenger_data_list]

    def buy(self):
        for passenger in self.__get_passenger_list():
            print(passenger.name + "  \t" +
                  PassengerType.TEXT_LOOKUP[passenger.type] + "\t  " + \
                  IdentificationType.TEXT_LOOKUP[passenger.id_type] + "  \t" + \
                  passenger.id_number)