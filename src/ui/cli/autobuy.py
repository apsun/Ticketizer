# -*- coding: utf-8 -*-
import codecs
import os
from core import common
from core.errors import StopCaptchaRetry
from core.enums import TrainType, TicketType
from core.data.station import StationList
from core.processing.containers import ValueRange
from core.search.search import TicketSearcher, TrainQuery
from core.processing.filter import TrainFilter
from core.processing.sort import TrainSorter
from core.auth.login import LoginManager


def main(config):
    def get_and_solve_captcha(getter, solver):
        on_init, on_new, on_input, on_invalid, on_end = solver()
        on_init()
        try:
            while True:
                captcha_image = getter()
                on_new(captcha_image.image_data)
                while True:
                    try:
                        answer = on_input()
                    except StopCaptchaRetry:
                        return None
                    if answer is not None:
                        success = captcha_image.check_answer(answer)
                        if success:
                            return captcha_image
                        else:
                            on_invalid()
                    else:
                        break
        finally:
            on_end()

    def console_captcha_solver():
        # noinspection PyUnresolvedReferences
        captcha_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captcha.jpg")

        def on_init():
            print("Please input the captcha answer. You may enter 'change' to ")
            print("get a new captcha, or enter 'abort' to cancel the purchase.")

        def on_new(image_data):
            with open(captcha_path, "wb") as f:
                f.write(image_data)
            print("The captcha image has been saved at: " + captcha_path)

        def on_input():
            answer = input("Enter captcha answer: ")
            test_answer = answer.upper()
            if test_answer == "CHANGE":
                answer = None
            elif test_answer == "ABORT":
                raise StopCaptchaRetry()
            return answer

        def on_invalid():
            print("Incorrect captcha answer! Please check your answer and ")
            print("try again, or type 'change' to get a new captcha image.")

        def on_end():
            os.remove(captcha_path)

        return on_init, on_new, on_input, on_invalid, on_end

    def construct_filter():
        def construct_time_filter(data):
            if data is None:
                return ValueRange()
            lower, upper = data
            if lower is None and upper is None:
                return None
            if lower is not None:
                lower = common.str_to_time(lower)
            if upper is not None:
                upper = common.str_to_time(upper)
            return ValueRange(lower, upper)

        def construcct_real_filter(data):
            if data is None:
                return ValueRange()
            lower, upper = data
            if lower is None and upper is None:
                return None
            if lower is not None:
                lower = float(lower)
            if upper is not None:
                upper = float(upper)
            return ValueRange(lower, upper)

        filters = config.get("range_filters")
        if filters is None:
            return None

        filter_obj = TrainFilter()
        filter_obj.departure_time_range = construct_time_filter(filters.get("departure_time"))
        filter_obj.arrival_time_range = construct_time_filter(filters.get("arrival_time"))
        filter_obj.duration_range = construcct_real_filter(filters.get("duration_range"))
        filter_obj.ticket_filter.price_range = construcct_real_filter(filters.get("price_range"))
        filter_obj.blacklist.add_range(config.get("blacklist") or [])
        filter_obj.whitelist.add_range(config.get("whitelist") or [])
        train_types = config.get("train_type_filter")
        if train_types is not None:
            filter_obj.enabled_types.clear()
            for type_string in train_types:
                if type_string == "":
                    type_value = TrainType.OTHER
                else:
                    type_value = TrainType.REVERSE_ABBREVIATION_LOOKUP[type_string]
                filter_obj.enabled_types[type_value] = True
        ticket_types_raw = config["passengers"].values()
        for ticket_type_list in ticket_types_raw:
            for type_string in ticket_type_list:
                real_type = TicketType.REVERSE_FULL_NAME_LOOKUP[type_string]
                filter_obj.ticket_filter.enabled_types.add(real_type)
        return filter_obj

    def construct_sorters():
        sorters = config.get("train_sorters")
        if sorters is None:
            return None
        if len(sorters) == 0:
            return None

        sorter_obj = TrainSorter()

        built_in_sorters = {
            "price": sorter_obj.sort_by_price,
            "deparuture_time": sorter_obj.sort_by_departure_time,
            "arrival_time": sorter_obj.sort_by_arrival_time,
            "duration": sorter_obj.sort_by_duration
        }

        for sorter in sorters:
            if isinstance(sorter, str):
                if sorter[0] == "!":
                    sorter = built_in_sorters[sorter[1:]], True
                else:
                    sorter = built_in_sorters[sorter], False
            sorter_obj.sort_methods.append(sorter)
        return sorter_obj

    def construct_query(stations):
        query_obj = TrainQuery(stations)
        query_obj.date = common.str_to_date(config["train_date"])
        query_obj.departure_station = stations.get_by_name(config["departure_station"])
        query_obj.destination_station = stations.get_by_name(config["destination_station"])
        query_obj.exact_departure_station = config.get("exact_departure_station", False)
        query_obj.exact_destination_station = config.get("exact_destination_station", False)
        return query_obj

    def further_filter_trains(trains):
        filters = config.get("custom_train_filters")
        if filters is None:
            return trains
        return [t for t in trains for f in filters if f(t)]

    def get_optimal_train(trains):
        # returns:
        # (train object, {passenger obj:ticket type}
        # TODO
        pass

    searcher = TicketSearcher()
    station_list = StationList()
    searcher.query = construct_query(station_list)
    searcher.filter = construct_filter()
    searcher.sorter = construct_sorters()
    train_list = searcher.get_train_list()
    train_list = further_filter_trains(train_list)
    train, ticket_dict = get_optimal_train(train_list)

    if config.get("confirm_purchase", True):
        print("-------[Confirm Purchase]-------")
        print("Train: " + train.name)
        print("Departure time: " + train.departure_time)
        print("Arrival time: " + train.arrival_time)
        print("Duration: " + train.duration)
        print("Tickets: ")
        for passenger, ticket_type in ticket_dict.items():
            print(passenger.name + ": " + TicketType.FULL_NAME_LOOKUP[ticket_type])
        print("--------------------------------")
        while True:
            response = input("Do you wish to continue with this purchase? (y/n): ").upper()
            if response == "N":
                return None
            if response == "Y":
                break
            print("Invalid response! Enter either 'y' or 'n'!")

    login_manager = LoginManager()
    captcha_solver = config["captcha_solver"] or console_captcha_solver
    captcha = get_and_solve_captcha(login_manager.get_login_captcha, captcha_solver)
    if captcha is None:
        return None
    login_manager.login(config["login_username"], config["login_password"], captcha)


def load_config(config_script_path):
    config = {}
    with codecs.open(config_script_path, encoding="utf8") as config_file:
        exec(config_file.read(), config)
    return config

if __name__ == "__main__":
    main(load_config("config.py"))