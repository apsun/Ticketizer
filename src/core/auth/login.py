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

from core import logger, webrequest
from core.errors import LoginFailedError, InvalidOperationError
from core.auth.cookies import SessionCookies
from core.auth.captcha import CaptchaType, Captcha
from core.auth.purchase import TicketPurchaser


class LoginManager:
    def __init__(self):
        self.__cookies = SessionCookies()
        self.__username = None

    def __del__(self):
        # Doesn't matter if this throws an exception; it will be ignored anyways
        # if self.__username is not None:
        #     self.logout()
        pass

    @staticmethod
    def __get_login_params(username, password, captcha_answer):
        return {
            "loginUserDTO.user_name": username,
            "userDTO.password": password,
            "randCode": captcha_answer
        }

    def __is_logged_in(self):
        if self.__username is None:
            return False
        url = "https://kyfw.12306.cn/otn/login/checkUser"
        return webrequest.post_json(url, cookies=self.__cookies)["data"]["flag"] is True

    def get_purchaser(self):
        if not self.__is_logged_in():
            raise InvalidOperationError("Cannot purchase tickets without logging in")
        return TicketPurchaser(self.__cookies)

    def login(self, email, password, captcha):
        data = self.__get_login_params(email, password, captcha.answer)
        url = "https://kyfw.12306.cn/otn/login/loginUserAsyn"
        json = webrequest.post_json(url, data=data, cookies=self.__cookies)
        webrequest.check_json_flag(json, "data", "status", exception=LoginFailedError)
        username = json["data"]["username"]
        logger.debug("Successfully logged in with username " + username)
        self.__username = username
        return self

    def logout(self):
        webrequest.get("https://kyfw.12306.cn/otn/login/loginOut", cookies=self.__cookies, allow_redirects=False)
        if self.__username is not None:
            # noinspection PyTypeChecker
            logger.debug("Logged out of user: " + self.__username)
        else:
            logger.warning("Logged out of unknown user")
        return self

    def get_login_captcha(self):
        return Captcha(CaptchaType.LOGIN, self.__cookies)