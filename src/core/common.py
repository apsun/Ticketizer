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


def read_json(response):
    if response.text == "-1":
        raise InvalidRequestException("Invalid query, check your parameters")
    return response.json()


def date_to_str(date_obj):
    return date_obj.strftime("%Y-%m-%d")


def str_to_date(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()


def time_to_str(time_obj):
    return time_obj.strftime("%H:%M")


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