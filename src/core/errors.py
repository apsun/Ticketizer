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


class InvalidOperationError(Exception):
    pass


class LoginFailedError(Exception):
    pass


class InvalidUsernameError(LoginFailedError):
    pass


class InvalidPasswordError(LoginFailedError):
    pass


class TooManyLoginAttemptsError(LoginFailedError):
    pass


class PurchaseFailedError(Exception):
    pass


class RequestError(Exception):
    def __init__(self, msg, json, response):
        super(RequestError, self).__init__(msg, json, response)


class CaptchaUnsolvedError(Exception):
    pass


class UnfinishedTransactionError(Exception):
    pass


class DataExpiredError(Exception):
    pass


class InvalidTicketDateError(Exception):
    pass


class StopPathSearch(Exception):
    pass


class StopCaptchaRetry(Exception):
    pass


class StopPurchaseQueue(Exception):
    pass