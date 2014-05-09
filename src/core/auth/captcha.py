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
#
# TODO: Improve API for GUI callers

import threading
from core import webrequest
from core.webrequest import HTTPError


# Global lock for all captcha solvers
__captcha_lock = threading.Lock()
__cached_answer = None


def on_begin():
    pass


def on_new_image(image_data):
    raise NotImplementedError()


def on_input_answer():
    raise NotImplementedError()


def on_incorrect_answer():
    pass


def on_end():
    pass


def solve_login_captcha(cookies):
    return __do_captcha("login", cookies)


def solve_purchase_captcha(cookies):
    return __do_captcha("purchase", cookies)


def get_login_image(cookies):
    return __get_image("login", cookies)


def get_purchase_image(cookies):
    return __get_image("purchase", cookies)


def check_login_answer(answer, cookies):
    return __check_answer("login", answer, cookies)


def check_purchase_answer(answer, cookies):
    return __check_answer("purchase", answer, cookies)


def set_cache(value):
    global __cached_answer
    __cached_answer = value


def reset_cache():
    global __cached_answer
    __cached_answer = None


def __do_captcha(captcha_type, cookies):
    if __cached_answer is not None:
        return __cached_answer
    try:
        __captcha_lock.acquire()
        on_begin()
        while True:
            image_data = __get_image(captcha_type, cookies)
            on_new_image(image_data)
            while True:
                answer = on_input_answer()
                if answer is None:
                    break
                if __check_answer(captcha_type, answer, cookies):
                    return answer
                on_incorrect_answer()
    finally:
        on_end()
        __captcha_lock.release()


def __get_request_params(captcha_type):
    return {
        "login": {
            "module": "login",
            "rand": "sjrand"
        },
        "purchase": {
            "module": "passenger",
            "rand": "randp"
        }
    }[captcha_type]


def __get_check_data(captcha_type, answer):
    return {
        "login": {
            "rand": "sjrand",
            "randCode": answer
        },
        "purchase": {
            "rand": "randp",
            "randCode": answer
        }
    }[captcha_type]


def __get_image(captcha_type, cookies):
    # Note: Requesting a login captcha while logged in seems to be okay,
    # but requesting a purchase captcha while logged out fails.
    url = "https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew.do"
    params = __get_request_params(captcha_type)
    response = webrequest.get(url, params=params, cookies=cookies)
    content_type = response.headers["Content-Type"].split(";")[0]
    assert content_type == "image/jpeg"
    return response.content


def __check_answer(captcha_type, answer, cookies):
    url = "https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn"
    data = __get_check_data(captcha_type, answer)
    try:
        json = webrequest.post_json(url, data=data, cookies=cookies)
        return json.get_bool("data")
    except HTTPError as ex:
        if ex.response.status_code == 406:
            # 406 means the request was okay, but the
            # server said our answer's format was invalid
            return False

        # Otherwise, propagate the exception to the caller
        raise