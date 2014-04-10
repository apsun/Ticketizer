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
import datetime
# import getpass

# Oh dear god, it's dependency hell >_<
from core import timeconverter, logger
from core.data.passenger import Passenger
from core.logger import LogType
from core.enums import TrainType, TicketType, TicketStatus, PassengerType, IdentificationType, Gender
from core.processing.containers import ValueRange, PriorityList
from core.processing.filter import TrainFilter
from core.processing.sort import TrainSorter
from core.data.station import StationList
from core.search.search import TrainQuery, DateOutOfRangeError
from core.auth.login import LoginManager
from core.auth.login import InvalidUsernameError, InvalidPasswordError
from core.auth.login import TooManyLoginAttemptsError, SystemMaintenanceError
from core.auth.purchase import TicketPurchaser
from core.auth.purchase import DataExpiredError, UnfinishedTransactionError
from core.auth.purchase import NotEnoughTicketsError, StopPurchaseQueue
# Wow! We're still alive!


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


def login(auto, retry):
    def do_login(lm, un, pw, ca):
        try:
            lm.login(un, pw, ca)
        except InvalidUsernameError:
            print(localization.INCORRECT_USERNAME)
            return "username"
        except InvalidPasswordError:
            print(localization.INCORRECT_USERNAME)
            return "password"
        except TooManyLoginAttemptsError:
            print(localization.TOO_MANY_LOGIN_ATTEMPTS)
            return "attempts"
        return None

    login_manager = LoginManager()
    captcha_solver = auto and config.get("captcha_solver", ConsoleCaptchaSolver)
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
            config["username"] = username
            config["password"] = password
            return login_manager
        if not retry:
            # Retrying disabled; do not proceed.
            return None
        if error == "username":
            # Invalid username
            username = None
            del config["username"]
        elif error == "password":
            # Invalid password
            password = None
            del config["password"]
        elif error == "attempts":
            # Too many login attempts
            username = password = None


def create_train_filters(auto):
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
    filter_obj.blacklist.add_range(config.get("train_blacklist", ()))
    filter_obj.whitelist.add_range(config.get("train_whitelist", ()))

    # Filter unbuyable trains (always enabled for auto mode)
    filter_obj.ticket_filter.filter_sold_out = auto or config.get("hide_sold_out", False)
    filter_obj.ticket_filter.filter_not_yet_sold = auto or config.get("not_yet_sold", False)

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
    sorter_obj.favorites = PriorityList(config.get("favorite_trains", ()))
    return sorter_obj


def create_train_query(station_list, auto):
    def get_date_obj(config_key):
        date = prompt_value_use_config(
            prompt=localization.ENTER_DATE,
            input_parser=timeconverter.str_to_date,
            error_handler=localization.INVALID_DATE.format(timeconverter.date_to_str(datetime.datetime.now())),
            config_key=auto and config_key
        )
        config[config_key] = timeconverter.date_to_str(date)
        return date

    def get_station_obj(config_key, name):
        station = prompt_value_use_config(
            prompt=localization.ENTER_STATION_NAME.format(name),
            input_parser=lambda a: get_station_by_name(station_list, a),
            error_handler=localization.INVALID_STATION_NAME,
            config_key=auto and config_key
        )
        config[config_key] = station.name
        return station

    query_obj = TrainQuery(station_list)
    query_obj.date = get_date_obj("date")
    query_obj.departure_station = get_station_obj("departure_station", localization.DEPARTURE)
    query_obj.destination_station = get_station_obj("destination_station", localization.DESTINATION)
    query_obj.exact_departure_station = config.get("exact_departure_station", False)
    query_obj.exact_destination_station = config.get("exact_destination_station", False)
    return query_obj


def query(station_list, auto, retry):
    cfg_query = create_train_query(station_list, auto)
    cfg_filter = create_train_filters(auto)
    cfg_sorter = create_train_sorters()
    custom_filter = config.get("custom_filter", lambda tl: None)
    custom_sorter = config.get("custom_sorter", lambda tl: None)
    sleep_time = config.get("search_retry_rate", 1)
    while True:
        try:
            train_list = cfg_query.execute()
        except DateOutOfRangeError:
            print(localization.DATE_OUT_OF_RANGE.format(cfg_query.date))
            del config["date"]
            cfg_query = create_train_query(station_list, auto)
            continue
        original_count = len(train_list)
        train_list = cfg_filter.filter(train_list)
        custom_filter(train_list)
        filtered_count = len(train_list)
        if filtered_count == 0:
            if original_count > 0:
                print(localization.ALL_TRAINS_FILTERED.format(original_count))
                if retry:
                    print(localization.RETRYING_SEARCH.format(sleep_time))
                    try:
                        time.sleep(sleep_time)
                    except KeyboardInterrupt:
                        return None
            else:
                print(localization.NO_TRAINS_FOUND)
                return None
        else:
            cfg_sorter.sort(train_list)
            custom_sorter(train_list)
            return train_list


def purchase(login_manager, train_list, auto):
    try:
        train = select_train(train_list, auto)
    except KeyboardInterrupt:
        return None

    purchaser = TicketPurchaser(login_manager)
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

    passenger_list = get_passenger_list(purchaser)
    available_tickets = [t for t in train.tickets if t.status == TicketStatus.NORMAL]
    captcha_solver = auto and config.get("captcha_solver", ConsoleCaptchaSolver)
    try:
        selected_passenger_list = select_passengers(passenger_list, auto)
        selected_ticket_dict = select_tickets(selected_passenger_list, available_tickets, auto)
        captcha_answer = solve_captcha(purchaser.get_purchase_captcha, captcha_solver)
        order_id = purchaser.continue_purchase(selected_ticket_dict, captcha_answer, purchase_queue_callback)
    except KeyboardInterrupt:
        return None
    if order_id is not None:
        print(localization.ORDER_COMPLETED.format(order_id))
    return order_id


def get_passenger_list(purchaser):
    passenger_list = purchaser.get_passenger_list()
    extra_passengers = config.get("custom_passengers")
    if extra_passengers is not None:
        for key, value in extra_passengers.items():
            passenger = Passenger()
            passenger.name = key
            passenger.gender = Gender.REVERSE_TEXT_LOOKUP[value["gender"]]
            passenger.id_type = IdentificationType.REVERSE_TEXT_LOOKUP[value["id_type"]]
            passenger.id_number = value["id_number"]
            passenger.type = PassengerType.REVERSE_TEXT_LOOKUP[value["type"]]
            passenger.phone_number = value["phone_number"]
            for i, existing_passenger in enumerate(passenger_list):
                if existing_passenger.name == key:
                    if existing_passenger != passenger:
                        passenger_list[i] = passenger
                        print(localization.OVERWROTE_PASSENGER.format(key))
                    break
            else:
                passenger_list.append(passenger)
    return passenger_list


def purchase_queue_callback(queue_length):
    sleep_time = config.get("queue_refresh_rate", 1)
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
            timeconverter.time_to_str(train.departure_time),
            timeconverter.time_to_str(train.arrival_time),
            day_delta_str
        )

    if auto:
        # Assuming the list is sorted from most relevant to least relevant
        return train_list[0]

    return prompt_value(
        header=lambda: print_list(train_list, train_info_repr, None),
        prompt=localization.ENTER_TRAIN_NAME,
        input_parser=lambda a: parse_list_value(train_list, a, lambda t: t.name),
        error_handler=localization.INVALID_TRAIN_NAME
    )


def select_passengers(passenger_list, auto):
    def get_passenger_from_name(name):
        for p in passenger_list:
            if p.name == name:
                return p
        return None

    def get_passengers_from_dict(passenger_dict):
        selected = []
        error = False
        # TODO: Handle duplicates -- what if passenger is in multiple keys?
        for key in passenger_dict:
            if isinstance(key, str):
                p = get_passenger_from_name(key)
                if p is None:
                    print(localization.PASSENGER_DOES_NOT_EXIST.format(key))
                    error = True
                else:
                    selected.append(p)
            else:
                # Assuming the key is a tuple
                for subkey in key:
                    p = get_passenger_from_name(subkey)
                    if p is None:
                        print(localization.PASSENGER_DOES_NOT_EXIST.format(subkey))
                        error = True
                    else:
                        selected.append(p)
        if error:
            return None
        return selected

    cfg_passengers = config.get("passengers")
    if auto and cfg_passengers is not None:
        passengers = get_passengers_from_dict(cfg_passengers)
        if passengers is not None:
            return passengers
        else:
            print(localization.PASSENGERS_MISSING_OVERALL)

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
                # Directly choose if there is only one available item
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


def parse_list_index(item_list, input_value, starting_index=1, multi_separator=None, unique=True):
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
    #
    # unique:
    #   If multi_separator is True, only returns unique indices.
    if multi_separator is None:
        index = int(input_value) - starting_index
        if index < 0:
            raise IndexError()
        return item_list[index]
    else:
        input_value = input_value.split(multi_separator)
        items = []
        # Technically we could use OrderedDict for this
        seen_indices = set()
        for istr in input_value:
            index = int(istr.strip()) - starting_index
            if index < 0:
                raise IndexError()
            if not unique or index not in seen_indices:
                items.append(item_list[index])
                seen_indices.add(index)
        return items


def print_or_call(handler, ex=None):
    if handler is None:
        # No error handler defined, allow exception to bubble
        return False

    if isinstance(handler, str):
        # Error handler is a generic string, format string with
        # exception if necessary and print the handler.
        if ex is not None:
            handler = handler.format(ex)
        print(handler)
        return True

    # Assume error handler is a callable object that takes the
    # exception as a parameter. It should return whether the
    # exception was handled or not.
    if ex is None:
        return handler()
    return handler(ex)


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
            if not print_or_call(error_handler, ex):
                raise


def prompt_value_use_config(header=None, prompt=None, input_parser=None, error_handler=None, config_key=None):
    # Does the same thing as prompt_value, except with an option to read
    # the value from the configuration database. If the config value is
    # invalid as defined by input_parser, this falls back to prompt_value.
    #
    # A good pattern to use this would be as follows:
    # prompt_value_use_config(..., config_key=auto and "<KEY_NAME_HERE>")
    #
    # config_key:
    #   The key in the configuration that holds the default value. If this
    #   is None, this function performs exactly the same as prompt_value.
    value = config_key and config.get(config_key)
    if value:
        try:
            return input_parser(value)
        except Exception as ex:
            if not print_or_call(error_handler, ex):
                raise

    return prompt_value(header=header, prompt=prompt, input_parser=input_parser, error_handler=error_handler)


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


def autobuy():
    # Get station list
    station_list = StationList()

    # Login beforehand (just in case!)
    try:
        login_manager = login(auto=True, retry=True)
    except SystemMaintenanceError:
        print(localization.SYSTEM_OFFLINE)
        return None
    if login_manager is None:
        # User cancelled login (KeyboardInterrupt)
        return None

    retry_search = config.get("search_retry", True)
    while True:
        # Search for train
        train_list = query(station_list, auto=True, retry=retry_search)
        if train_list is None:
            # No trains found and retry is False
            return None

        # Purchase tickets
        try:
            return purchase(login_manager, train_list, auto=True)
        except DataExpiredError:
            train_list = query(station_list, True)
            return purchase(login_manager, train_list, auto=True)
        except NotEnoughTicketsError:
            # Tickets ran out while we tried to purchase
            # Just jump back to the beginning of the loop
            # and try again.
            pass


def interactive():
    pass


def main():
    auto, success = setup()
    if not success:
        return

    if auto:
        autobuy()
    else:
        interactive()


if __name__ == "__main__":
    main()