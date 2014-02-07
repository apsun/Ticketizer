# -*- coding: utf-8 -*-
import re
import requests
import os
import logger
import session
import sys


class CaptchaType:
    LOGIN = 0
    PURCHASE = 1


class LoginState:
    LOGGED_OUT = 0
    LOGGED_IN = 1


class CaptchaData:

    def __init__(self, captcha_type, session_id, image_data):
        self.captcha_type = captcha_type
        self.session_id = session_id
        self.image_data = image_data


class AuthenticationManager:

    def __init__(self):
        self.login_state = LoginState.LOGGED_OUT
        self.session_data = session.SessionData()
        self.username = None
        self.captcha_image = None
        self.captcha_solver = self._console_captcha_solver

    @staticmethod
    def _console_captcha_solver(image_data):
        # This is the default captcha "solver".
        # All it does is write the captcha image to disk,
        # then prompt the user to answer through the console.
        # Obviously, you should replace this method if you want
        # to use a GUI or OCR to provide the answer.
        # The solver function takes a single parameter, which is the
        # image as a sequence of bytes, and returns the answer as a string.
        
        with open("captcha.jpg", "wb") as f:
            f.write(image_data)
        
        # 'raw_input' was removed in Python 3 and is now just named 'input'.
        if sys.version_info[0] < 3:
            answer = raw_input("Enter answer: ")
        else:
            answer = input("Enter answer: ")

        # Use empty input (user just hits "enter" without typing anything)
        # as our sentinel value to skip remaining retries
        if answer == "":
            answer = None

        # Optionally delete the captcha image after obtaining an answer.
        # It's usually more convenient to keep it, since image viewers can
        # automatically refresh when a new captcha image is downloaded.
        delete_captcha_file = False
        if delete_captcha_file:
            os.remove("captcha.jpg")
        return answer

    @staticmethod
    def _get_login_data(username, password, captcha_answer):
        return {
            "loginUserDTO.user_name": username,
            "userDTO.password": password,
            "randCode": captcha_answer
        }

    @staticmethod
    def _get_captcha_request_params(captcha_type):
        if captcha_type == CaptchaType.LOGIN:
            return {
                "module": "login",
                "rand": "sjrand"
            }
        elif captcha_type == CaptchaType.PURCHASE:
            return {
                "module": "passenger",
                "rand": "randp"
            }

    @staticmethod
    def _get_captcha_check_data(captcha_type, answer):
        if captcha_type == CaptchaType.LOGIN:
            return {
                "rand": "sjrand",
                "randCode": answer
            }
        elif captcha_type == CaptchaType.PURCHASE:
            return {
                "rand": "randp",
                "randCode": answer
            }

    def _check_logged_in(self):
        url = "https://kyfw.12306.cn/otn/login/checkUser"
        cookies = self.session_data.get_session_cookies()
        response = requests.post(url, data=None, cookies=cookies, verify=False)
        response.raise_for_status()
        json = response.json()
        json_data = json.get("data")
        return json_data is not None and json_data.get("flag") is True

    def _get_state_vars(self):
        # WARNING: VERY HACKY THINGS AHEAD
        # (and I'm not even using regex! >_<)

        url = "https://kyfw.12306.cn/otn/index/init"
        cookies = self.session_data.get_session_cookies()
        response = requests.get(url, cookies=cookies, verify=False)
        response.raise_for_status()
        # We're reading the entire page contents into memory.
        # This is a little bit inefficient, since the state
        # vars are always near the top of the page.
        html = response.text
        state_begin = html.index("/*<![CDATA[*/") + len("/*<![CDATA[*/")
        state_end = html.index("/*]]>*/")

        # Text content is as follows:

        # ...
        # /*<![CDATA[*/
        # var ctx='/otn/';
        # var globalRepeatSubmitToken = null;
        # var global_lang = 'zh_CN';
        # var sessionInit = '';
        # var isShowNotice = null;
        # /*]]>*/
        # ...

        # I personally would rather just eval the JS and
        # get the values directly, but would rather not
        # use another dependency to do it, so we just
        # parse the string the hacky way. Honestly though,
        # I doubt the internal code to build these vars
        # is any better than this, knowing 12306...
        state_js_lines = html[state_begin:state_end].splitlines()[1:-1]
        state_dict = {}
        for line in state_js_lines:
            var_name_index = line.index("var ") + len("var ")
            var_name_index_end = line.index("=", var_name_index)
            var_name = line[var_name_index:var_name_index_end].strip()
            var_value_index = var_name_index_end + len("=")
            var_value_index_end = line.index(";")
            var_value_token = line[var_value_index:var_value_index_end].strip()
            if var_value_token == "null":
                state_dict[var_name] = None
                logger.debug("Got state var: " + var_name + " = null")
            elif var_value_token[0] == "'" and var_value_token[-1] == "'":
                var_value = var_value_token[1:-1]
                state_dict[var_name] = var_value
                logger.debug("Got state var: " + var_name + " = '" + var_value + "'")
            else:
                # Only going to handle null and single-quote strings
                # so far; if anything changes, well... we're screwed.
                assert False

        # Pretty-print state variables to log
        # dict_str = "------------------------\n"
        # if sys.version_info[0] < 3:
        #     items = state_dict.iteritems()
        # else:
        #     items = state_dict.items()
        # for key, value in items:
        #     if value is None:
        #         dict_str += key + " = None\n"
        #     else:
        #         dict_str += key + " = '" + value + "'\n"
        # dict_str += "------------------------"
        # logger.debug("Got state variables:\n" + dict_str)
        # logger.debug("Got state variables: " + str(state_dict))
        return state_dict

    def _check_captcha_needs_refresh(self, captcha_type):
        # This function checks 3 things:
        # 1. We have a captcha image saved
        # 2. The saved captcha image is from our current session
        # 3. The captcha type is correct for our context
        if self.captcha_image is None:
            return True
        if self.session_data.session_id != self.captcha_image.session_id:
            return True
        if captcha_type != self.captcha_image.captcha_type:
            return True
        return False

    def _solve_captcha_image(self):
        assert self.captcha_solver is not None
        answer = self.captcha_solver(self.captcha_image.image_data)
        if answer is not None:
            logger.debug("Captcha input: " + answer)
        return answer

    def login(self, username, password, captcha_retries=0):
        if self.login_state == LoginState.LOGGED_IN:
            logger.debug("Already logged in, if you are switching accounts, log out first!")
            return True

        # Sometimes we don't need to get a new captcha,
        # this can happen if the app has already fetched
        # one to display on the login screen.
        if self._check_captcha_needs_refresh(CaptchaType.LOGIN):
            self.request_captcha_image(CaptchaType.LOGIN)

        captcha_answer = None
        while True:
            # Call the captcha solver function
            # This function is an implementation detail of the client program,
            # which means they are free to return the value however they want.
            # It can be an OCR program, TextBox value, console input, etc.
            captcha_answer = self._solve_captcha_image()

            # Accept None as a sentinel value to skip remaining retry attempts
            # It is up to the captcha solver function to return this value
            if captcha_answer is None:
                logger.debug("Captcha aborted, login canceled")
                return False

            # Check captcha answer with the server
            # This "validates" our session ID token so we can log in
            if not self.check_captcha_answer(CaptchaType.LOGIN, captcha_answer):
                if captcha_retries <= 0:
                    logger.error("Incorrect captcha answer, login failed")
                    return False
                logger.error("Incorrect captcha answer, retrying " + str(captcha_retries) + " more time(s)")
                captcha_retries -= 1
            else:
                break

        # Whoops, I logged your password in plain-text ;)
        logger.debug("Logging in with username {0} and password {1}".format(username, password))

        # Submit user credentials to the server
        data = self._get_login_data(username, password, captcha_answer)
        url = "https://kyfw.12306.cn/otn/login/loginAysnSuggest"
        cookies = self.session_data.get_session_cookies()
        response = requests.post(url, data, cookies=cookies, verify=False)
        response.raise_for_status()
        # TODO: Do we need to check for an updated session ID here?
        # self._session_data.set_session_cookies(response)
        
        # Check server response to see if login was successful
        # response > data > loginCheck should be "Y" if we logged in
        json = response.json()
        json_data = json.get("data")
        if json_data is None or json_data.get("loginCheck") != "Y":
            messages = json.get("messages")
            if messages is not None:
                logger.error("Login failed: " + ";".join(messages), response)
            else:
                logger.error("Login failed for unknown reason", response)
            return False
        logger.debug("Login successful", response)
        self.login_state = LoginState.LOGGED_IN
        self.username = username

    def logout(self):
        if self.login_state == LoginState.LOGGED_OUT:
            logger.debug("Already logged out, no need to log out again!")
            return

        response = requests.get("https://kyfw.12306.cn/otn/login/loginOut", verify=False)
        response.raise_for_status()
        logger.debug("Logged out of user: " + self.username, response)
        # Logging out gives us a new session ID token, 
        # but it's not really that useful anyways
        self.session_data.set_session_cookies(response)
        self.login_state = LoginState.LOGGED_OUT
        self.username = None

    def request_captcha_image(self, captcha_type):
        # Login captcha is only useful if we're logged out, right?
        # And obviously, we can only purchase tickets if logged in...
        # Retrieving a login captcha while logged in seems to be okay,
        # but retrieving a purchase captcha while logged out fails.
        if captcha_type == CaptchaType.LOGIN:
            assert self.login_state == LoginState.LOGGED_OUT
        elif captcha_type == CaptchaType.PURCHASE:
            assert self.login_state == LoginState.LOGGED_IN

        url = "https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew.do"
        params = self._get_captcha_request_params(captcha_type)
        cookies = self.session_data.get_session_cookies()
        response = requests.get(url, params=params, cookies=cookies, verify=False)
        response.raise_for_status()

        # If this is our first request, we will get a new session ID token.
        self.session_data.set_session_cookies(response)

        logger.debug("Fetched captcha image: " + response.url, response)
        logger.debug("Captcha image MIME type: " + response.headers.get("Content-Type").split(";")[0])

        self.captcha_image = CaptchaData(captcha_type, self.session_data.session_id, response.content)

    def check_captcha_answer(self, captcha_type, answer):
        # Check some common errors to save a network request
        if len(answer) != 4:
            logger.debug("Captcha answer not 4 characters")
            return False
        if re.match("^[a-zA-Z0-9]+$", answer) is None:
            logger.debug("Captcha answer not alphanumeric")
            return False

        url = "https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn"
        data = self._get_captcha_check_data(captcha_type, answer)
        cookies = self.session_data.get_session_cookies()
        response = requests.post(url, data, cookies=cookies, verify=False)
        response.raise_for_status()
        # TODO: Do we need to check for an updated session ID here?
        # self._session_data.set_session_cookies(response)
        success = response.json().get("data") == "Y"
        logger.debug("Captcha entered correctly: " + str(success), response)
        return success

    def refresh_login_state(self):
        if self._check_logged_in():
            self.username = self._get_state_vars()["sessionInit"]
            self.login_state = LoginState.LOGGED_IN
            logger.debug("Status refreshed to logged in state")
        else:
            self.username = None
            self.login_state = LoginState.LOGGED_OUT
            logger.debug("Status refreshed to logged out state")