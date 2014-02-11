import datetime


class InvalidRequestException(Exception):
    def __init__(self, messages):
        if isinstance(messages, str):
            self.messages = [messages]
        elif isinstance(messages, list):
            self.messages = messages
        else:
            raise TypeError()

    def __str__(self):
        messages = self.messages
        if messages is None or len(messages) == 0:
            reason_str = "reason unknown"
        else:
            reason_str = "reason: " + ";".join(messages)
        return "Request failed, " + reason_str


def read_json_data(response):
    json = read_json(response)
    json_data = json.get("data")
    if json_data is None:
        raise InvalidRequestException(json.get("messages"))
    return json_data


def get_dict_value_coalesce(value, *keys):
    if value is None:  # If the dictionary is null, coalesce the result to null
        return None
    if len(keys) == 0:  # No more keys to check, return the current result
        return value
    key, keys = keys[0], keys[1:]  # Pop first key from the list
    return get_dict_value_coalesce(value.get(key), *keys)


def combine_subdicts(value):
    combined = {}
    for k, v in value.items():
        if isinstance(v, dict):
            combined.update(combine_subdicts(v))
        else:
            combined[k] = v
    return combined


def read_json(response):
    if response.text == "-1":
        raise InvalidRequestException("Invalid query, check your parameters")
    return response.json()


def datetime_to_str(datetime_obj, fmt="%Y-%m-%d %H:%M"):
    return datetime_obj.strftime(fmt)


def str_to_datetime(date, time, date_fmt="%Y-%m-%d", time_fmt="%H:%M"):
    # Allow date and time parameters to be date and time objects,
    # meaning you can use this method to "concatenate" date and time objects.
    if isinstance(date, datetime.date):
        date = date.strftime(date_fmt)
    if isinstance(time, datetime.time):
        time = time.strftime(time_fmt)
    return datetime.datetime.strptime(date + " " + time, date_fmt + " " + time_fmt)


def date_to_str(date_obj, fmt="%Y-%m-%d"):
    return date_obj.strftime(fmt)


def str_to_date(date_str, fmt="%Y-%m-%d"):
    return datetime.datetime.strptime(date_str, fmt).date()


def time_to_str(time_obj, fmt="%H:%M"):
    return time_obj.strftime(fmt)


def str_to_time(time_str, fmt="%H:%M"):
    return datetime.datetime.strptime(time_str, fmt).time()


def timedelta_to_str(timedelta_obj, force_seconds=False):
    minutes, seconds = divmod(timedelta_obj.total_seconds(), 60)
    hours, minutes = divmod(minutes, 60)
    hours = int(hours)
    minutes = int(minutes)
    seconds = int(seconds)
    fmt = "{0:02d}:{1:02d}"
    if force_seconds or seconds != 0:
        fmt += "{2:02d}"
    return fmt.format(hours, minutes, seconds)


def is_true(value):
    if value is True:
        return True
    if value == "Y":
        return True
    return False