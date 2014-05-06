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
from core.logger import LogType
from core.auth import captcha
from core.enums import TrainType, TicketType, TicketStatus, PassengerType, IdentificationType, Gender
from core.processing.containers import ValueRange
from core.processing.filter import TrainFilter
from core.processing.sort import TrainSorter
from core.data.station import StationList
from core.data.passenger import Passenger
from core.search.search import TrainQuery, DateOutOfRangeError
from core.auth.login import LoginManager
from core.auth.login import InvalidUsernameError, InvalidPasswordError
from core.auth.login import TooManyLoginAttemptsError, SystemMaintenanceError
from core.auth.purchase import TicketPurchaser
from core.auth.purchase import DataExpiredError, UnfinishedTransactionError
from core.auth.purchase import NotEnoughTicketsError, StopPurchaseQueue
# Wow! We're still alive!


# ------------------------------Helper functions------------------------------

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


def select_train_date(auto):
    invalid_date_printer = lambda ex: localization.INVALID_DATE.format(
        timeconverter.date_to_str(datetime.datetime.now())
    )

    return prompt_value_use_config(
        prompt=localization.ENTER_DATE,
        input_parser=timeconverter.str_to_date,
        error_handler=invalid_date_printer,
        config_key=auto and "date"
    )


def select_departure_station(station_list, auto):
    return prompt_value_use_config(
        prompt=localization.ENTER_STATION_NAME.format(localization.DEPARTURE),
        input_parser=lambda a: get_station_by_name(station_list, a),
        error_handler=localization.INVALID_STATION_NAME,
        config_key=auto and "departure_station"
    )


def select_destination_station(station_list, auto):
    return prompt_value_use_config(
        prompt=localization.ENTER_STATION_NAME.format(localization.DESTINATION),
        input_parser=lambda a: get_station_by_name(station_list, a),
        error_handler=localization.INVALID_STATION_NAME,
        config_key=auto and "destination_station"
    )


def select_train(train_list, auto):
    def train_info_repr(train):
        day_delta = train.arrival_time.day - train.departure_time.day
        day_delta_str = (
            "" if day_delta == 0 else
            " (+1 day)" if day_delta == 1 else
            " (+{0} days)".format(day_delta)
        )
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
    def unique_append(container_list, seen_set, key, value):
        if key in seen_set:
            raise KeyError("Duplicate passenger entry: {0}".format(key))
        container_list.append(value)
        seen_set.add(key)

    def get_passengers_from_dict(selected, name_map):
        selected_passengers = []
        seen = set()
        for key in selected:
            if isinstance(key, str):
                unique_append(selected_passengers, seen, key, name_map[key])
            else:
                # Assuming the key is a tuple
                for subkey in key:
                    if not isinstance(subkey, str):
                        raise TypeError("Invalid passenger key: {0}".format(subkey))
                    unique_append(selected_passengers, seen, subkey, name_map[subkey])
        return selected_passengers

    cfg_passengers = config.get("passengers")
    if auto and cfg_passengers is not None:
        passenger_dict = {p.name: p for p in passenger_list}
        passengers = get_passengers_from_dict(cfg_passengers, passenger_dict)
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
    train_blacklist = config.get("train_blacklist")
    train_whitelist = config.get("train_whitelist")
    if train_blacklist is not None:
        filter_obj.blacklist.add_range(train_blacklist)
    if train_whitelist is not None:
        filter_obj.whitelist.add_range(train_whitelist)

    # Filter unbuyable trains
    filter_obj.ticket_filter.filter_sold_out = config.get("hide_sold_out", False)
    filter_obj.ticket_filter.filter_not_yet_sold = config.get("not_yet_sold", False)

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

    # Train sorters
    train_sorters = config.get("train_sorters")
    if train_sorters is not None:
        sort_funcs = []
        sort_func_map = {
            "name": TrainSorter.sort_by_name,
            "departure_time": TrainSorter.sort_by_departure_time,
            "arrival_time": TrainSorter.sort_by_arrival_time,
            "duration": TrainSorter.sort_by_duration,
            "price": TrainSorter.sort_by_price
        }

        for sorter_name in train_sorters:
            if sorter_name.startswith("!"):
                sorter_name = sorter_name[1:]
                reverse = True
            else:
                reverse = False
            sort_func = sort_func_map[sorter_name]
            wrapped_sort = lambda train_list: sort_func(train_list, reverse)
            sort_funcs.append(wrapped_sort)
        sorter_obj.sort_methods = sort_funcs

    # Favorite trains
    favorite_trains = config.get("favorite_trains")
    if favorite_trains is not None:
        favorite_map = {}

        if isinstance(favorite_trains, set):
            # Unordered favorites
            for value in favorite_trains:
                if not isinstance(value, str):
                    raise TypeError()
                # Every value gets 0, no need to worry about duplicates
                favorite_map[value] = 0
        else:
            # Ordered favorites
            for i, value in enumerate(favorite_trains):
                if isinstance(value, set):
                    # Unordered group in overall ordered list
                    for subvalue in value:
                        if not isinstance(subvalue, str):
                            raise TypeError()
                        # Each value in subgroup gets the same priority
                        favorite_map.setdefault(subvalue, i)
                elif not isinstance(value, str):
                    raise TypeError()
                favorite_map.setdefault(value, i)

        sorter_obj.favorites = favorite_map

    return sorter_obj


def get_passenger_list(purchaser):
    passenger_list = purchaser.get_passenger_list()
    custom_passengers = config.get("custom_passengers")
    if custom_passengers is not None:
        for key, value in custom_passengers.items():
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


# -----------------------------Generic utilities------------------------------
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
        if len(input_value) == 0:
            raise ValueError()
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


def print_or_call(handler, ex):
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


# -------------------------------One-time setup-------------------------------
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


def setup_localization():
    language_id = config.get("locale", "en_US")
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
        setup_localization()


def print_config():
    print("-" * 33 + "Config values" + "-" * 33)
    for key, value in config.items():
        # Ignore built-in keys
        if key[:2] == key[-2:] == "__":
            continue
        print(key + ": " + repr(value))
    print("-" * 79)


def register_captcha_solver():
    captcha_path = os.path.abspath(config.get("captcha_path", "captcha.jpg"))

    def on_begin():
        print(localization.CAPTCHA_BEGIN)

    def on_new_image(image_data):
        with open(captcha_path, "wb") as f:
            f.write(image_data)
        print(localization.CAPTCHA_SAVED.format(captcha_path))
        webbrowser.open(captcha_path)

    def on_input_answer():
        answer = input(localization.ENTER_CAPTCHA)
        if answer == "":
            return None
        return answer

    def on_incorrect_answer():
        print(localization.INCORRECT_CAPTCHA)

    def on_end():
        os.remove(captcha_path)

    captcha.on_begin = on_begin
    captcha.on_new_image = on_new_image
    captcha.on_input_answer = on_input_answer
    captcha.on_incorrect_answer = on_incorrect_answer
    captcha.on_end = on_end


# -------------------------------Core functions-------------------------------
def login(retry, auto):
    if auto:
        username = config.get("username")
        password = config.get("password")
    else:
        username = None
        password = None

    login_manager = LoginManager()
    while True:
        if username is None:
            username = input(localization.ENTER_USERNAME)
        if password is None:
            password = input(localization.ENTER_PASSWORD)
            # Weird issue with the IntelliJ console and getpass,
            # So we fall back to input() for now.
            # password = getpass.getpass(localization.ENTER_PASSWORD)
        try:
            login_manager.login(username, password)
        except InvalidUsernameError:
            username = None
            print(localization.INCORRECT_USERNAME)
        except InvalidPasswordError:
            password = None
            print(localization.INCORRECT_PASSWORD)
        except TooManyLoginAttemptsError:
            username = password = None
        else:
            config["username"] = username
            config["password"] = password
            return login_manager
        if not retry:
            return None


def query(station_list, retry, auto):
    # Construct query object
    query_obj = TrainQuery(station_list)
    query_obj.date = select_train_date(auto)
    query_obj.departure_station = select_departure_station(station_list, auto)
    query_obj.destination_station = select_destination_station(station_list, auto)
    query_obj.exact_departure_station = config.get("exact_departure_station", False)
    query_obj.exact_destination_station = config.get("exact_destination_station", False)

    filter_obj = create_train_filters()
    sorter_obj = create_train_sorters()
    custom_filter = config.get("custom_filter")
    custom_sorter = config.get("custom_sorter")
    sleep_time = config.get("search_retry_rate", 1)

    while True:
        try:
            # Get raw train list
            train_list = query_obj.execute()
        except DateOutOfRangeError:
            # Invalid date provided, prompt the user for a new one
            print(localization.DATE_OUT_OF_RANGE.format(timeconverter.date_to_str(query_obj.date)))
            # Forcibly disable auto mode, to avoid re-using an
            # invalid date again
            query_obj.date = select_train_date(False)
            continue

        # Now we filter the resulting list
        original_count = len(train_list)
        train_list = filter_obj.filter(train_list)
        if custom_filter is not None:
            custom_filter(train_list)
        filtered_count = len(train_list)

        # Make sure there's at least one train
        if filtered_count == 0:
            if original_count > 0:
                print(localization.ALL_TRAINS_FILTERED.format(original_count))
                if retry:
                    print(localization.RETRYING_SEARCH.format(sleep_time))
                    time.sleep(sleep_time)
                    continue
                else:
                    return None
            else:
                print(localization.NO_TRAINS_FOUND)
                return None

        # After filtering the trains, we sort the list
        sorter_obj.sort(train_list)
        if custom_sorter is not None:
            custom_sorter(train_list)

        return train_list


def purchase(login_manager, train, auto):
    purchaser = TicketPurchaser(login_manager.cookies)
    purchaser.train = train

    # Get passengers
    passenger_list = get_passenger_list(purchaser)
    selected_passenger_list = select_passengers(passenger_list, auto)

    # Select tickets
    available_tickets = [t for t in train.tickets if t.status == TicketStatus.NORMAL]
    selected_tickets = select_tickets(selected_passenger_list, available_tickets, auto)

    # Submit the order
    order_id = purchaser.execute(selected_tickets, purchase_queue_callback)
    if order_id is not None:
        print(localization.ORDER_COMPLETED.format(order_id))
    else:
        print(localization.ORDER_INTERRUPTED)
    return order_id


# ----------------------------------Main UI-----------------------------------
def autobuy():
    # Get station list
    station_list = StationList()

    # Login beforehand (just in case!)
    # TODO: Allow multiple logins
    try:
        login_manager = login(True, auto=True)
    except SystemMaintenanceError:
        # Stupid website goes offline every night for "maintenance".
        print(localization.SYSTEM_OFFLINE)
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
            train = select_train(train_list, auto=True)
            return purchase(login_manager, train, auto=True)
        except UnfinishedTransactionError:
            # TODO: Change an account if possible?
            print(localization.UNFINISHED_TRANSACTIONS)
            return None
        except DataExpiredError:
            # This means the user waited too long between
            # querying train data and submitting the order.
            # We simply re-query the train list and try again.
            train_list = query(station_list, retry_search, auto=True)
            train = select_train(train_list, auto=True)
            return purchase(login_manager, train, auto=True)
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
    register_captcha_solver()

    if auto:
        autobuy()
    else:
        interactive()


if __name__ == "__main__":
    main()