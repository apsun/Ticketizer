# -*- coding: utf-8 -*-
from core import logger, common, webrequest
from core.errors import LoginFailedError, InvalidOperationError
from core.auth.cookies import SessionCookies
from core.auth.captcha import CaptchaType, Captcha


class LoginManager:
    def __init__(self):
        self.__cookies = SessionCookies()
        self.__username = None

    def __del__(self):
        # Doesn't matter if this throws an exception; it will be ignored anyways
        if self.__username is not None:
            self.logout()

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
        response = webrequest.post(url, cookies=self.__cookies)
        return common.read_json_data(response)["flag"] is True

    def login(self, username, password, captcha):
        if captcha.answer is None:
            raise LoginFailedError("Captcha answer not provided or is incorrect, login failed")

        # Submit user credentials to the server
        data = self.__get_login_params(username, password, captcha.answer)
        url = "https://kyfw.12306.cn/otn/login/loginAysnSuggest"
        response = webrequest.post(url, data=data, cookies=self.__cookies)
        # Check server response to see if login was successful
        # response > data > loginCheck should be "Y" if we logged in
        # otherwise, loginCheck will be absent
        json = common.read_json(response)
        success = common.is_true(json["data"]["loginCheck"])
        if success:
            logger.debug("Successfully logged in with username " + username, response)
            self.__username = username
        else:
            message = common.join_list(json.get("messages"))
            logger.error("Logging in with username {0} failed, reason: {1}".format(username, message), response)
            raise LoginFailedError(message)

    def logout(self):
        response = webrequest.get("https://kyfw.12306.cn/otn/login/loginOut", cookies=self.__cookies)
        if self.__username is not None:
            logger.debug("Logged out of user: " + self.__username, response)
        else:
            logger.warning("Logged out of unknown user", response)

    def get_login_captcha(self):
        return Captcha(CaptchaType.LOGIN, self.__cookies)

    def get_purchase_captcha(self):
        if not self.__is_logged_in():
            raise InvalidOperationError("Cannot get purchase captcha without logging in")
        return Captcha(CaptchaType.PURCHASE, self.__cookies)