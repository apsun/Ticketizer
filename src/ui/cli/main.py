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

import os
import time
import codecs
import argparse
import importlib
import webbrowser
# import getpass
from core import timeconverter, logger
from core.logger import LogType
from core.errors import *
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
        path = os.path.abspath(cls.CAPTCHA_PATH)
        with open(path, "wb") as f:
            f.write(image_data)
        print(localization.CAPTCHA_SAVED.format(path))
        webbrowser.open(path)

    @staticmethod
    def request_input():
        answer = input(localization.ENTER_CAPTCHA)
        test_answer = answer.upper()
        if test_answer == "":
            answer = None
        return answer

    @staticmethod
    def on_invalid_answer():
        print(localization.INCORRECT_CAPTCHA)

    @classmethod
    def on_end(cls):
        os.remove(os.path.abspath(cls.CAPTCHA_PATH))


def solve_captcha(image_factory, solver_factory):
    solver = solver_factory()
    solver.on_begin()
    try:
        while True:
            captcha_image = image_factory()
            solver.on_new_image(captcha_image.image_data)
            while True:
                answer = solver.request_input()
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
    sorter_obj.favorites = PriorityList(config.get("favorite_trains") or [])
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


def login(auto, retry, on_invalid_username=None, on_invalid_password=None):
    def do_login(lm, un, pw, ca):
        try:
            lm.login(un, pw, ca)
        except InvalidUsernameError:
            if on_invalid_username is None:
                print(localization.INCORRECT_USERNAME)
            elif isinstance(on_invalid_username, str):
                print(on_invalid_username)
            else:
                on_invalid_username()
            return "username"
        except InvalidPasswordError:
            if on_invalid_password is None:
                print(localization.INCORRECT_PASSWORD)
            elif isinstance(on_invalid_password, str):
                print(on_invalid_password)
            else:
                on_invalid_password()
            return "password"
        return None

    login_manager = LoginManager()
    captcha_solver = auto and config.get("captcha_solver") or ConsoleCaptchaSolver
    if auto:
        username = config.get("username")
        password = config.get("password")
    else:
        username = None
        password = None

    while True:
        try:
            if username is None:
                username = input(localization.ENTER_USERNAME)
            if password is None:
                password = input(localization.ENTER_PASSWORD)
                # Weird issue with the IntelliJ console and getpass,
                # So we fall back to input() for now.
                # password = getpass.getpass(localization.ENTER_PASSWORD)
            captcha_answer = solve_captcha(login_manager.get_login_captcha, captcha_solver)
        except KeyboardInterrupt:
            # User interrupted login info entry process
            return None
        error = do_login(login_manager, username, password, captcha_answer)
        if error is None:
            # Everything went ok!
            return login_manager
        if not retry:
            # Retrying disabled; do not proceed.
            return None
        if error == "username":
            username = None
            # Don't clear the password; what if the user
            # just misspelled their username?
            # password = None
        elif error == "password":
            password = None


def query(station_list, auto):
    searcher = TicketSearcher()
    searcher.query = create_train_query(station_list, auto)
    searcher.filter = create_train_filters()
    searcher.sorter = create_train_sorters()
    train_list = searcher.get_train_list()
    return train_list


def purchase(login_manager, train_list, auto):
    try:
        train = select_train(train_list, auto)
    except KeyboardInterrupt:
        return None

    purchaser = login_manager.get_purchaser()
    purchaser.train = train
    try:
        purchaser.begin_purchase()
    except UnfinishedTransactionError:
        print(localization.UNFINISHED_TRANSACTIONS)
        return None
    except DataExpiredError:
        # This means the user waited too long between
        # querying train data and submitting the order.
        # Caller should catch this exception and re-try
        # one time after refreshing the train data.
        raise

    passenger_list = purchaser.get_passenger_list()
    available_tickets = [t for t in train.tickets if t.status == TicketStatus.NORMAL]
    captcha_solver = auto and config.get("captcha_solver") or ConsoleCaptchaSolver
    try:
        selected_passenger_list = select_passengers(passenger_list, auto)
        selected_ticket_dict = select_tickets(selected_passenger_list, available_tickets, auto)
        captcha_answer = solve_captcha(purchaser.get_purchase_captcha, captcha_solver)
    except KeyboardInterrupt:
        return None
    order_id = purchaser.continue_purchase(selected_ticket_dict, captcha_answer, purchase_queue_callback)
    if order_id is not None:
        print(localization.ORDER_COMPLETED.format(order_id))
    return order_id


def purchase_queue_callback(queue_length):
    sleep_time = config.get("queue_refresh_rate", 1000)
    try:
        print(localization.QUEUE_WAIT.format(queue_length))
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        raise StopPurchaseQueue()


def select_train(train_list, auto):
    def train_info_repr(train):
        day_delta = train.arrival_time.day - train.departure_time.day
        day_delta_str = "" if day_delta == 0 else \
                        " (+1 day)" if day_delta == 1 else \
                        " (+{0} days)".format(day_delta)
        return "{0}\t{1}\t-> {2}\t{3} -> {4}{5}".format(
            train.name.ljust(5),
            train.departure_station.name.ljust(4),
            train.destination_station.name.ljust(4),
            train.departure_time.strftime("%H:%M"),
            train.arrival_time.strftime("%H:%M"),
            day_delta_str
        )

    # TODO: Add automation
    return prompt_value(
        header=lambda: print_list(train_list, train_info_repr, None),
        prompt=localization.ENTER_TRAIN_NAME,
        input_parser=lambda a: parse_list_value(train_list, a, lambda t: t.name),
        error_handler=localization.INVALID_TRAIN_NAME
    )


def select_passengers(passenger_list, auto):
    # TODO: Add automation
    return prompt_value(
        header=lambda: print_list(passenger_list, lambda p: p.name),
        prompt=localization.ENTER_PASSENGER_INDEX,
        input_parser=lambda a: parse_list_index(passenger_list, a, multi_separator=","),
        error_handler=localization.INVALID_PASSENGER_INDEX.format(1, len(passenger_list))
    )


def select_tickets(passenger_list, ticket_list, auto):
    # TODO: Add automation
    print_list(ticket_list, lambda t: "{0}\t({1}元, {2} remaining)".format(
        TicketType.FULL_NAME_LOOKUP[t.type].ljust(4), t.price, t.count
    ))
    passenger_dict = {}
    for passenger in passenger_list:
        ticket = prompt_value(
            prompt=localization.ENTER_TICKET_INDEX.format(passenger.name),
            input_parser=lambda a: parse_list_index(ticket_list, a),
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
                    header=print_list(station, lambda s: s.name),
                    prompt=localization.ENTER_STATION_INDEX,
                    input_parser=lambda a: parse_list_index(station, a),
                    error_handler=localization.INVALID_STATION_INDEX.format(1, len(station))
                )
        if station is not None:
            return station
    raise KeyError(name)


def print_list(item_list, item_repr=str, starting_index=1):
    if starting_index is None:
        for item in item_list:
            print(item_repr(item))
    else:
        for index, item in enumerate(item_list):
            print("{0}. {1}".format(index + starting_index, item_repr(item)))


def parse_list_value(item_list, input_value, item_repr=str, case_sensitive=False, multi_separator=None):
    # Parses a user-inputted value from a list and returns the
    # item after ensuring that it is a valid entry in the list.
    #
    # item_list:
    #   The list to validate the input against.
    #
    # input_value:
    #   The user-inputted value. This must be a string.
    #
    # item_repr:
    #   A function that takes a list item as a parameter and
    #   returns the value that the input should be compared
    #   against to be considered equal. If the list is not
    #   a list of strings and this parameter is not specified,
    #   the input will be compared against each list item's
    #   default string representation.
    #
    # case_sensitive:
    #   Whether to consider input casing when comparing user
    #   input against list values. Unless case sensitivity
    #   matters, setting this to False is highly recommended.
    #
    # multi_separator:
    #   Allows the user to input multiple values at once. This
    #   can either be a string on which to split the user input,
    #   or None to specify that input should not be splitted.
    def get_item_as_str(value):
        value = str(item_repr(value))
        if not case_sensitive:
            value = value.upper()
        return value

    if not case_sensitive:
        # Just uppercase the entire string, since splitting an 
        # uppercase string should leave it uppercase, right? Note 
        # that if the separator is a lowercase letter, this might 
        # cause problems...
        input_value = input_value.upper()

    if multi_separator is None:
        for item in item_list:
            item_str = get_item_as_str(item)
            if item_str == input_value:
                return item
        raise KeyError()
    else:
        results = []
        check = input_value.split(multi_separator)
        for item in item_list:
            item_str = get_item_as_str(item)
            if item_str in check:
                results.append(item)
                check.remove(item_str)
        if len(results) > 0:
            raise KeyError()
        return results


def parse_list_index(item_list, input_value, starting_index=1, multi_separator=None):
    # Parses a user-inputted list index and validates it,
    # returning the item in the list at the inputted index.
    #
    # item_list:
    #   The list to validate the input against.
    #
    # input_value:
    #   The user-inputted list index. This must be a string.
    #
    # starting_index:
    #   The index which is translated to the first item in the
    #   list. For example, if you are displaying entries
    #   starting from index 1, then this value should also be 1.
    #
    # multi_separator:
    #   Allows the user to input multiple indices at once. This
    #   can either be a string on which to split the user input,
    #   or None to specify that input should not be splitted.
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
    # Prompts the user for input, with additional validation built in.
    # This is similar to the input() function, but it also allows you to
    # automate input validation and conversion.
    #
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
                    # logger.error(repr(ex))
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
    except FileNotFoundError:
        print("No configuration file found, using default values.")
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


def print_config():
    print("-" * 33 + "Config values" + "-" * 33)
    for key, value in config.items():
        # Ignore built-in keys
        if key[:2] == key[-2:] == "__":
            continue
        print(key + ": " + repr(value))
    print("-" * 79)


def main():
    auto, success = setup()
    if not success:
        return
    # print_config()

    # Get stations
    station_list = StationList()

    # Get trains for stations
    train_list = query(station_list, auto)

    # Log in to account
    try:
        login_manager = login(auto, True)
    except TooManyLoginAttemptsError:
        print(localization.TOO_MANY_LOGIN_ATTEMPTS)
    if login_manager is None:
        print("Login canceled!")
        return

    # Purchase tickets
    try:
        order_id = purchase(login_manager, train_list, auto)
    except DataExpiredError:
        train_list = query(station_list, auto)
        purchase(login_manager, train_list, auto)
    if order_id is None:
        print("Purchase interrupted!")


if __name__ == "__main__":
    main()