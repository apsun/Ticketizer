# -*- coding: utf-8 -*-
class InvalidRequestError(Exception):
    pass


class InvalidOperationError(Exception):
    pass


class LoginFailedError(Exception):
    pass


class PurchaseFailedError(Exception):
    pass


class CaptchaUnsolvedError(Exception):
    pass


class StopPathSearch(Exception):
    pass


class StopCaptchaRetry(Exception):
    pass


class UnfinishedTransactionError(Exception):
    pass


class DataExpiredError(Exception):
    pass