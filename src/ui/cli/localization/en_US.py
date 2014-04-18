# -*- coding: utf-8 -*-

ENTER_USERNAME = "Enter your username: "
ENTER_PASSWORD = "Enter your password: "
CAPTCHA_BEGIN = "Please answer the captcha. To change the captcha image, " \
                "simply press ENTER directly without typing anything."
CAPTCHA_SAVED = "The captcha image has been saved at: {0}"
ENTER_CAPTCHA = "Enter the 4 characters in the captcha image: "
INCORRECT_USERNAME = "Incorrect username!"
INCORRECT_PASSWORD = "Incorrect password!"
INCORRECT_CAPTCHA = "Incorrect captcha answer! Please check your answer and " \
                    "try again, or hit ENTER without typing anything to get " \
                    "a new captcha image."
ENTER_DATE = "Enter the train date (format: YYYY-mm-dd): "
INVALID_DATE = "Invalid date format! Accepted format is 'YYYY-mm-dd' " \
               "(for example: '{0}')."
ENTER_STATION_NAME = "Enter the {0} station name. (use either the full name " \
                     "in Chinese or Pinyin, or the initial letters of the " \
                     "name in Pinyin): "
DEPARTURE = "departure"
DESTINATION = "destination"
INVALID_STATION_NAME = "Invalid station name! Accepted format is '上海', " \
                       "'shanghai', or 'sh'."
ENTER_STATION_INDEX = "Multiple matches found, enter the number " \
                      "corresponding to your desired station: "
INVALID_STATION_INDEX = "Invalid station index! Valid range is {0}-{1}."
ENTER_TRAIN_NAME = "Enter the name of the train you wish to purchase " \
                   "tickets for: "
INVALID_TRAIN_NAME = "Invalid train name!"
ENTER_PASSENGER_INDEX = "Enter the numbers corresponding to the passengers " \
                        "you are purchasing tickets for (separate multiple " \
                        "passengers by commas): "
INVALID_PASSENGER_INDEX = "Invalid passenger index! Valid range is {0}-{1}."
ENTER_TICKET_INDEX = "Enter the number corresponding to the ticket for {0}: "
INVALID_TICKET_INDEX = "Invalid ticket index! Valid range is {0}-{1}."
QUEUE_WAIT = "Waiting in queue... (Length: {0})"
UNFINISHED_TRANSACTIONS = "You have unfinished transactions associated with " \
                          "your account! Either complete or cancel them and " \
                          "try again. "
ALL_TRAINS_FILTERED = "{0} trains were found, but all were blocked " \
                      "by filters. Try disabling some filters and try again."
NO_TRAINS_FOUND = "No trains were found between these two stations!"
RETRYING_SEARCH = "Searching again in {0} secs."
ORDER_COMPLETED = "Order completed! Order ID: {0}"
ORDER_INTERRUPTED = "Order interrupted! Please check your order ID manually!"
ENTER_TRANSFER_TIME = "Enter the {0} transfer time (format: HH:MM): "
MINIMUM = "minimum"
MAXIMUM = "maximum"
TOO_MANY_LOGIN_ATTEMPTS = "Too many login attempts! Use a different account " \
                          "or try again at a later time!"
SYSTEM_OFFLINE = "12306 is currently offline for maintenance, try again later!"
DATE_OUT_OF_RANGE = "You cannot purchase tickets on {0} (yet), choose a " \
                    "different date!"
PASSENGER_DOES_NOT_EXIST = "Passenger {0} does not exist! Please add their " \
                           "credentials to your account and try again."
PASSENGERS_MISSING_OVERALL = "One or more passengers specified in the " \
                             "config do not exist. Please reselect your " \
                             "passengers:"
OVERWROTE_PASSENGER = "Passenger {0} as defined in the custom passenger " \
                      "config overwrote an existing passenger in your " \
                      "account with the same name!"