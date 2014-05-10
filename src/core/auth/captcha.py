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
from core import webrequest
from core.webrequest import HTTPError


class Captcha:
    def __init__(self, cookies, captcha_type):
        self.__cookies = cookies
        self.__type = captcha_type
        self.answer = None

    def __get_request_params(self):
        return {
            "login": {
                "module": "login",
                "rand": "sjrand"
            },
            "purchase": {
                "module": "passenger",
                "rand": "randp"
            }
        }[self.__type]

    def __get_check_data(self, answer):
        return {
            "login": {
                "rand": "sjrand",
                "randCode": answer
            },
            "purchase": {
                "rand": "randp",
                "randCode": answer
            }
        }[self.__type]

    def refresh_image(self):
        # Note: Requesting a login captcha while logged in seems to be okay,
        # but requesting a purchase captcha while logged out fails.
        url = "https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew.do"
        params = self.__get_request_params()
        response = webrequest.get(url, params=params, cookies=self.__cookies)
        content_type = response.headers["Content-Type"].split(";")[0]
        assert content_type == "image/jpeg"
        # When changing the image, invalidate the old answer (if any)
        self.answer = None
        return response.content

    def submit_answer(self, answer):
        url = "https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn"
        data = self.__get_check_data(answer)
        try:
            json = webrequest.post_json(url, data=data, cookies=self.__cookies)
            success = json.get_bool("data")
            if success:
                self.answer = answer
            return success
        except HTTPError as ex:
            if ex.response.status_code == 406:
                # 406 means the request was okay, but the
                # server said our answer's format was invalid
                return False

            # Otherwise, propagate the exception to the caller
            raise