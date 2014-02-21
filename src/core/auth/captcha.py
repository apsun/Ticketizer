# -*- coding: utf-8 -*-
from requests.exceptions import HTTPError
from core import logger, common, webrequest
from core.errors import StopCaptchaRetry, CaptchaUnsolvedError


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
        if self.__answer is None:
            raise CaptchaUnsolvedError()
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

    def solve(self, solver):
        while True:
            # Call the captcha solver function.
            # This function is an implementation detail of the client program,
            # which means they are free to return the value however they want.
            # It can be an OCR program, TextBox value, console input, etc.
            try:
                captcha_answer = solver(self.image_data)
            except StopCaptchaRetry:
                captcha_answer = None
            if captcha_answer is None or self.check_answer(captcha_answer):
                # Return self to allow fluent API calls, such as the following:
                # captcha = get_captcha().solve(captcha_solver_func)
                return self

    def check_answer(self, answer):
        url = "https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn"
        data = self.__get_captcha_check_data(answer)
        try:
            json_data = webrequest.post_json(url, data=data, cookies=self.__cookies)["data"]
            success = common.is_true(json_data)
        except HTTPError as ex:
            if ex.response.status_code == 406:
                success = False
            else:
                raise
        if success:
            self.__answer = answer
        logger.debug("Captcha entered correctly (answer: {0}): {1}".format(answer, success))
        return success