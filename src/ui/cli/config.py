# -*- coding: utf-8 -*-

# Auto-buy only
username = "__USERNAME__"
password = "__PASSWORD__"
date = "2014-05-26"
departure_station = "南京"
destination_station = "上海"
passengers = {
    "__YOUR_NAME__": ["硬座", "软座", "无座"]
}
search_retry = True
search_retry_rate = 1
auto_select_single = True
station_list_path = "./"

# Non-auto only
hide_sold_out = False
hide_not_yet_sold = False

# Normal helpful config
train_type_filter = ["T", "D", "?"]
ticket_type_filter = ["一等座", "二等座"]
train_range_filters = {
    "departure_time": (None, None),
    "arrival_time": (None, None),
    "duration": (None, None),
}
ticket_range_filters = {
    "price": (None, None)
}
custom_passengers = {
    "__YOUR_NAME__": {
        "gender": "男",
        "type": "成人",
        "id_type": "二代身份证",
        "id_number": "1234567890",
        "phone_number": "1234567890"
    }
}
# train_sorters = ["name", "duration"]
# train_blacklist = ["G21"]
# train_whitelist = ["T222"]
# favorite_trains = ({"T7786", "T123"}, ["T22", "K143"], {"T122", "T221"})

# Other config
save_session = True
confirm_purchase = True
exact_departure_station = False
exact_destination_station = False
open_purchase_page = True
queue_refresh_rate = 1

# Programming knowledge required
# captcha_solver = None  # class
# custom_sorter = None  # func(train_list) -> void
# custom_filter = None  # func(train_list) -> void