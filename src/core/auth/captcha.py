# -*- coding: utf-8 -*-
from core import logger, common, webrequest
from core.errors import StopCaptchaRetry


class CaptchaType:
    LOGIN = 0
    PURCHASE = 1


class Captcha:
    def __init__(self, captcha_type, cookies):
        self.__type = captcha_type
        self.__cookies = cookies
        self.__answer = None
        self.__image_data = self.__request_captcha_image()

    @property
    def answer(self):
        return self.__answer

    @property
    def image_data(self):
        return self.__image_data

    def __get_captcha_request_params(self):
        return {
            CaptchaType.LOGIN: {
                "module": "login",
                "rand": "sjrand"
            },
            CaptchaType.PURCHASE: {
                "module": "passenger",
                "rand": "randp"
            }
        }[self.__type]

    def __get_captcha_check_data(self, answer):
        return {
            CaptchaType.LOGIN: {
                "rand": "sjrand",
                "randCode": answer
            },
            CaptchaType.PURCHASE: {
                "rand": "randp",
                "randCode": answer
            }
        }[self.__type]

    def __request_captcha_image(self):
        # Note: Requesting a login captcha while logged in seems to be okay,
        # but requesting a purchase captcha while logged out fails.
        url = "https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew.do"
        params = self.__get_captcha_request_params()
        response = webrequest.get(url, params=params, cookies=self.__cookies)
        content_type = response.headers.get("Content-Type").split(";")[0]
        assert content_type == "image/jpeg"
        logger.debug("Fetched captcha image: " + response.url, response)
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
        response = webrequest.post(url, data=data, cookies=self.__cookies)
        success = common.is_true(common.read_json_data(response))
        if success:
            self.__answer = answer
        logger.debug("Captcha entered correctly (answer: {0}): {1}".format(answer, success), response)
        return success