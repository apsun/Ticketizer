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
from core.errors import InvalidOperationError, RequestError
from core.errors import InvalidUsernameError, InvalidPasswordError, TooManyLoginAttemptsError
from core.auth.cookies import SessionCookies
from core.auth.captcha import CaptchaType, Captcha
from core.auth.purchase import TicketPurchaser


class LoginManager:
    def __init__(self):
        self.__cookies = SessionCookies()

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
        url = "https://kyfw.12306.cn/otn/login/checkUser"
        json = webrequest.post_json(url, cookies=self.__cookies)
        return json["data"].get_bool("flag")

    def get_purchaser(self):
        if not self.__is_logged_in():
            raise InvalidOperationError("Cannot purchase tickets without logging in")
        return TicketPurchaser(self.__cookies)

    def login(self, email, password, captcha):
        data = self.__get_login_params(email, password, captcha.answer)
        url = "https://kyfw.12306.cn/otn/login/loginAysnSuggest"
        try:
            json = webrequest.post_json(url, data=data, cookies=self.__cookies)
            json["data"].assert_true("loginCheck")
        except RequestError as ex:
            if len(ex.args) > 0:
                msg = ex.args[0]
                if msg == "登录名不存在!":
                    raise InvalidUsernameError() from ex
                if msg.startswith("密码输入错误"):
                    raise InvalidPasswordError() from ex
                if msg.startswith("您的用户已经被锁定"):
                    raise TooManyLoginAttemptsError() from ex
            raise

    def logout(self):
        webrequest.get("https://kyfw.12306.cn/otn/login/loginOut", cookies=self.__cookies, allow_redirects=False)
        if self.__username is not None:
            # noinspection PyTypeChecker
            logger.debug("Logged out of user: " + self.__username)
        else:
            logger.warning("Logged out of unknown user")

    def get_login_captcha(self):
        return Captcha(CaptchaType.LOGIN, self.__cookies)