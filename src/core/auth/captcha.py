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

from requests.exceptions import HTTPError
from core import logger, webrequest


class CaptchaType:
    LOGIN = 0
    PURCHASE = 1


class Captcha:
    def __init__(self, captcha_type, cookies, request_params=None, check_params=None):
        self.__type = captcha_type
        self.__cookies = cookies
        self.__answer = None
        self.__request_params = request_params
        self.__check_params = check_params
        self.__image_data = self.__request_captcha_image()

    @property
    def answer(self):
        return self.__answer

    @property
    def image_data(self):
        return self.__image_data

    def __get_captcha_request_params(self):
        params = {
            CaptchaType.LOGIN: {
                "module": "login",
                "rand": "sjrand"
            },
            CaptchaType.PURCHASE: {
                "module": "passenger",
                "rand": "randp"
            }
        }[self.__type]
        if self.__request_params is not None:
            params.update(self.__request_params)
        return params

    def __get_captcha_check_data(self, answer):
        data = {
            CaptchaType.LOGIN: {
                "rand": "sjrand",
                "randCode": answer
            },
            CaptchaType.PURCHASE: {
                "rand": "randp",
                "randCode": answer
            }
        }[self.__type]
        if self.__check_params is not None:
            data.update(self.__check_params)
        return data

    def __request_captcha_image(self):
        # Note: Requesting a login captcha while logged in seems to be okay,
        # but requesting a purchase captcha while logged out fails.
        url = "https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew.do"
        params = self.__get_captcha_request_params()
        response = webrequest.get(url, params=params, cookies=self.__cookies)
        content_type = response.headers["Content-Type"].split(";")[0]
        assert content_type == "image/jpeg"
        return response.content

    def check_answer(self, answer):
        url = "https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn"
        data = self.__get_captcha_check_data(answer)
        try:
            json = webrequest.post_json(url, data=data, cookies=self.__cookies)
            success = json.get_bool("data")
        except HTTPError as ex:
            if ex.response.status_code == 406:
                success = False
            else:
                raise
        if success:
            self.__answer = answer
        logger.debug("Captcha entered correctly (answer: {0}): {1}".format(answer, success))
        return success