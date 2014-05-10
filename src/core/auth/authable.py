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
import functools
from core.auth.captcha import Captcha


class CaptchaUnsolvedError(Exception):
    pass


class Authable:
    def __init__(self, cookies, captcha_type):
        self.cookies = cookies
        self.captcha = Captcha(cookies, captcha_type)

    @staticmethod
    def consumes_captcha(reset_on_exception=True):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(this, *args, **kwargs):
                if this.captcha.answer is None:
                    raise CaptchaUnsolvedError()
                no_exception = True
                try:
                    return func(this, *args, **kwargs)
                except:
                    no_exception = False
                    raise
                finally:
                    if no_exception or reset_on_exception:
                        this.captcha.image_data = None
                        this.captcha.answer = None
            return wrapped
        return decorator