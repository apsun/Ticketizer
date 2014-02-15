# -*- coding: utf-8 -*-


class InvalidRequestError(Exception):
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


class StopPathSearch(Exception):
    pass


class StopCaptchaRetry(Exception):
    pass