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

import codecs
import importlib
import os
import argparse
import time
from core import timeconverter, logger
from core.logger import LogType
from core.errors import StopCaptchaRetry, StopPurchaseQueue
from core.errors import InvalidUsernameError, InvalidPasswordError
from core.errors import UnfinishedTransactionError, DataExpiredError
from core.enums import TrainType, TicketType, TicketStatus
from core.processing.containers import ValueRange
from core.processing.filter import TrainFilter
from core.processing.sort import TrainSorter, PriorityList
from core.data.station import StationList
from core.search.search import TicketSearcher, TrainQuery
from core.auth.login import LoginManager


class ConsoleCaptchaSolver:
    CAPTCHA_PATH = "captcha.jpg"

    @staticmethod
    def on_begin():
        print(localization.CAPTCHA_BEGIN)

    @classmethod
    def on_new_image(cls, image_data):
        with open(cls.CAPTCHA_PATH, "wb") as f:
            f.write(image_data)
        print(localization.CAPTCHA_SAVED.format(os.path.abspath(cls.CAPTCHA_PATH)))

    @staticmethod
    def request_input():
        try:
            answer = input(localization.ENTER_CAPTCHA)
        except KeyboardInterrupt:
            raise StopCaptchaRetry()
        test_answer = answer.upper()
        if test_answer == "":
            answer = None
        return answer

    @staticmethod
    def on_invalid_answer():
        print(localization.INCORRECT_CAPTCHA)

    @classmethod
    def on_end(cls):
        os.remove(cls.CAPTCHA_PATH)


def solve_captcha(image_factory, solver_factory):
    solver = solver_factory()
    solver.on_begin()
    try:
        while True:
            captcha_image = image_factory()
            solver.on_new_image(captcha_image.image_data)
            while True:
                try:
                    answer = solver.request_input()
                except StopCaptchaRetry:
                    return None
                if answer is not None:
                    success = captcha_image.check_answer(answer)
                    if success:
                        return captcha_image
                    else:
                        solver.on_invalid_answer()
                else:
                    break
    finally:
        solver.on_end()


def create_train_filters():
    filter_obj = TrainFilter()
    range_factory = ValueRange.from_tuple

    # Train range filters
    train_range = config.get("train_range_filters")
    if train_range is not None:
        filter_obj.departure_time_range = range_factory(train_range.get("departure_time"), timeconverter.str_to_time)
        filter_obj.arrival_time_range = range_factory(train_range.get("arrival_time"), float)
        filter_obj.duration_range = range_factory(train_range.get("duration_range"), float)

    # Ticket range filters
    ticket_range = config.get("ticket_range_filters")
    if ticket_range is not None:
        filter_obj.ticket_filter.price_range = range_factory(ticket_range.get("price_range"), float)

    # Whitelist and blacklist
    filter_obj.blacklist.add_range(config.get("train_blacklist") or [])
    filter_obj.whitelist.add_range(config.get("train_whitelist") or [])

    # Train type filter
    train_type = config.get("train_type_filter")
    if train_type is not None:
        enabled_types = filter_obj.enabled_types
        enabled_types.clear()
        for type_string in train_type:
            if type_string == "?":
                type_value = TrainType.OTHER
            else:
                type_value = TrainType.REVERSE_ABBREVIATION_LOOKUP[type_string]
            enabled_types.add(type_value)

    # Ticket type filter
    ticket_type = config.get("ticket_type_filter")
    if ticket_type is not None:
        enabled_types = filter_obj.ticket_filter.enabled_types
        enabled_types.clear()
        for type_string in ticket_type:
            type_value = TicketType.REVERSE_FULL_NAME_LOOKUP[type_string]
            enabled_types.add(type_value)

    return filter_obj


def create_train_sorters():
    sorter_obj = TrainSorter()
    sorter_obj.sort_methods = config.get("train_sorters")
    sorter_obj.favorites = PriorityList(config.get("favorite_trains"))
    return sorter_obj


def create_train_query(station_list, auto):
    def get_date_obj(config_key):
        return prompt_value_use_config(
            prompt=localization.ENTER_DATE,
            input_parser=timeconverter.str_to_date,
            error_handler=localization.INVALID_DATE,
            config_key=auto and config_key
        )

    def get_station_obj(config_key, name):
        return prompt_value_use_config(
            prompt=localization.ENTER_STATION_NAME.format(name),
            input_parser=lambda a: get_station_by_name(station_list, a),
            error_handler=localization.INVALID_STATION_NAME,
            config_key=auto and config_key
        )

    query_obj = TrainQuery(station_list)
    query_obj.date = get_date_obj("date")
    query_obj.departure_station = get_station_obj("departure_station", localization.DEPARTURE)
    query_obj.destination_station = get_station_obj("destination_station", localization.DESTINATION)
    query_obj.exact_departure_station = config.get("exact_departure_station", False)
    query_obj.exact_destination_station = config.get("exact_destination_station", False)
    return query_obj


def login(auto):
    login_manager = LoginManager()
    username = auto and config.get("username") or input(localization.ENTER_USERNAME)
    password = auto and config.get("password") or input(localization.ENTER_PASSWORD)
    captcha_solver = auto and config.get("captcha_solver") or ConsoleCaptchaSolver
    captcha_answer = solve_captcha(login_manager.get_login_captcha, captcha_solver)
    if captcha_answer is None:
        return
    try:
        return login_manager.login(username, password, captcha_answer)
    except InvalidUsernameError:
        print(localization.INCORRECT_USERNAME)
        return None
    except InvalidPasswordError:
        print(localization.INCORRECT_PASSWORD)
        return None


def query(station_list, auto):
    searcher = TicketSearcher()
    searcher.query = create_train_query(station_list, auto)
    searcher.filter = create_train_filters()
    searcher.sorter = create_train_sorters()
    train_list = searcher.get_train_list()
    return train_list


def purchase(login_manager, train, auto):
    purchaser = login_manager.get_purchaser()
    purchaser.train = train
    try:
        purchaser.begin_purchase()
    except UnfinishedTransactionError:
        print(localization.UNFINISHED_TRANSACTIONS)
        return
    except DataExpiredError:
        # This means the user waited too long between
        # querying train data and submitting the order.
        # Caller should catch this exception and re-try
        # one time after refreshing the train data.
        raise

    passenger_list = purchaser.get_passenger_list()
    selected_passenger_list = passenger_selector(passenger_list, auto)
    available_tickets = [t for t in train.tickets if t.status == TicketStatus.NORMAL]
    selected_ticket_dict = ticket_selector(selected_passenger_list, available_tickets, auto)
    captcha_solver = auto and config.get("captcha_solver") or ConsoleCaptchaSolver
    captcha_answer = solve_captcha(purchaser.get_purchase_captcha, captcha_solver)
    order_id = purchaser.continue_purchase(selected_ticket_dict, captcha_answer, purchase_queue_callback)
    if order_id is not None:
        print(localization.ORDER_COMPLETED.format(order_id))


def purchase_queue_callback(queue_length):
    sleep_time = config.get("queue_refresh_rate", 1000)
    try:
        print(localization.QUEUE_WAIT.format(queue_length))
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        raise StopPurchaseQueue()


def train_selector(train_list, auto):
    # TODO: Add automation
    # TODO: Fix selection (show table)
    return prompt_value(
        header=lambda: list_header_printer(train_list),
        prompt=localization.ENTER_TRAIN_NAME,
        input_parser=lambda a: list_input_parser(train_list, a)
    )


def passenger_selector(passenger_list, auto):
    # TODO: Add automation
    return prompt_value(
        header=lambda: list_header_printer(passenger_list),
        prompt=localization.ENTER_PASSENGER_INDEX,
        input_parser=lambda a: list_input_parser(passenger_list, a, multi_separator=",")
    )


def ticket_selector(passenger_list, ticket_list, auto):
    # TODO: Add automation
    # TODO: Fix selection (show table)
    passenger_dict = {}
    for passenger in passenger_list:
        ticket = prompt_value(
            prompt=localization.ENTER_TICKET_INDEX.format(passenger.name),
            input_parser=lambda a: list_input_parser(ticket_list, a),
            error_handler=localization.INVALID_TICKET_INDEX.format(1, len(ticket_list)))
        passenger_dict[passenger] = ticket
    return passenger_dict


def get_station_by_name(station_list, name):
    methods = (station_list.id_lookup,
               station_list.abbreviation_lookup,
               station_list.name_lookup,
               station_list.pinyin_lookup)
    for method in methods:
        station = method.get(name)
        if isinstance(station, list):
            if len(station) == 1:
                station = station[0]
            else:
                station = prompt_value(
                    header=list_header_printer(station, lambda s: s.name),
                    prompt=localization.ENTER_STATION_INDEX,
                    input_parser=lambda a: list_input_parser(station, a),
                    error_handler=localization.INVALID_STATION_INDEX.format(1, len(station))
                )
        if station is not None:
            return station
    raise KeyError(name)


def list_header_printer(item_list, item_repr=None, starting_index=1):
    for index, item in enumerate(item_list):
        if item_repr is not None:
            item = item_repr(item)
        print("{0}. {1}".format(index + starting_index, item))


def list_input_parser(item_list, input_value, starting_index=1, multi_separator=None):
    if multi_separator is None:
        index = int(input_value) - starting_index
        if index < 0:
            raise IndexError()
        return item_list[index]
    else:
        input_value = input_value.split(multi_separator)
        items = []
        for istr in input_value:
            index = int(istr.strip()) - starting_index
            if index < 0:
                raise IndexError()
            items.append(item_list[index])
        return items


def prompt_value(header=None, prompt=None, input_parser=None, error_handler=None):
    # header:
    #   Used to print the information the user uses to select an item.
    #   Can either be a string (directly printed) or a callable object
    #   that prints the header itself. If this is None, no header is printed.
    #
    # prompt:
    #   The message to display every time before requesting user input.
    #   If this is None, no prompt is printed.
    #
    # input_parser:
    #   Responsible for converting the user input to the desired value(s).
    #   If this is None, the input is directly returned without validation.
    #
    # error_handler:
    #   Handles exceptions that occur when calling input_parser. Can either
    #   be a string (directly printed) or a callable object that takes the
    #   exception as a parameter. If this is None, exceptions will propagate
    #   to the caller.
    if header is not None:
        if isinstance(header, str):
            print(header)
        else:
            header()
    while True:
        answer = input(prompt)
        if input_parser is None:
            return answer
        try:
            return input_parser(answer)
        except Exception as ex:
            if error_handler is not None:
                if isinstance(error_handler, str):
                    logger.error(ex)
                    print(error_handler)
                else:
                    error_handler(ex)
            else:
                raise


def prompt_value_use_config(header=None, prompt=None, input_parser=None, error_handler=None, config_key=None):
    # Does the same thing as prompt_value, except with an option to read
    # the value from the configuration database. Note that the configuration
    # value is assumed to be correct, so exceptions raised from parsing the
    # configuration do NOT get handled by error_handler.
    #
    # A good pattern to use this would be as follows:
    # prompt_value_use_config(..., config_key=auto and "<KEY_NAME_HERE>")
    #
    # config_key:
    #   The key in the configuration that holds the default value. If this
    #   is None, this function performs exactly the same as prompt_value.
    value = config_key and config.get(config_key)
    if value:
        value = input_parser(value)
    else:
        value = prompt_value(
            header=header,
            prompt=prompt,
            input_parser=input_parser,
            error_handler=error_handler
        )
    return value


def load_config(config_path):
    global config
    config = {}
    try:
        with codecs.open(config_path, encoding="utf-8") as config_file:
            exec(config_file.read(), config)
        return True
    except Exception as ex:
        print("Config file could not be loaded! " + repr(ex))
        return False


def setup_localization(language_id):
    global localization
    try:
        localization = importlib.import_module("ui.cli.localization." + language_id)
        return True
    except ImportError:
        print("Locale file for language {0} could not be loaded!".format(language_id))
        return False


def setup_log_verbosity(verbosity_str):
    verbosity_str = verbosity_str.upper()
    if verbosity_str == "ALL":
        logger.enabled_log_types = LogType.ALL
    elif verbosity_str == "NONE":
        logger.enabled_log_types = LogType.NONE
    else:
        verbosity = 0
        for verbosity_flag in verbosity_str:
            try:
                verbosity |= LogType.REVERSE_NAME_LOOKUP[verbosity_flag]
            except KeyError:
                print("Invalid log verbosity value: " + verbosity_flag)
                return False
        logger.enabled_log_types = verbosity
    return True


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbosity")
    parser.add_argument("--config")
    parser.add_argument("--auto", action="store_true", default=False)
    args = vars(parser.parse_args())

    return args["auto"], \
        setup_log_verbosity(args["verbosity"] or "we") and \
        load_config(args["config"] or "config.py") and \
        setup_localization(config.get("locale", "en_US"))


def main():
    auto, success = setup()
    if not success:
        return
    station_list = StationList()
    login_manager = login(auto)
    train_list = query(station_list, auto)
    train = train_selector(train_list, auto)
    purchase(login_manager, train, auto)


if __name__ == "__main__":
    main()