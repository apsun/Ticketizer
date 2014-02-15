# -*- coding: utf-8 -*-
import requests
from core.errors import StopCaptchaRetry
from core import logger, common


class CaptchaType:
    LOGIN = 0
    PURCHASE = 1


class CaptchaData:
    def __init__(self, captcha_type, session_id, image_data):
        self.captcha_type = captcha_type
        self.session_id = session_id
        self.image_data = image_data


class SessionData:
    def __init__(self):
        self.session_id = None
        self.server_ip = None

    def get_session_cookies(self):
        return {
            "JSESSIONID": self.session_id,
            "BIGipServerotn": self.server_ip
        }

    def set_session_cookies(self, response):
        # This function parses an HTTP response and sets the
        # session ID/server IP tokens accordingly (if found).
        cookies = response.headers.get("set-cookie")
        if cookies is None:
            return
        cookies_split = cookies.split(",")
        for cookie in cookies_split:
            key_value_pairs = cookie.split(";")
            for key_value_pair in key_value_pairs:
                pair_split = key_value_pair.split("=")
                assert len(pair_split) == 2
                key = pair_split[0].strip()
                if key == "JSESSIONID":
                    session_id = pair_split[1].strip()
                    if session_id != self.session_id:
                        self.session_id = session_id
                        logger.debug("Got new session ID: " + session_id)
                elif key == "BIGipServerotn":
                    server_ip = pair_split[1].strip()
                    if server_ip != self.server_ip:
                        self.server_ip = server_ip
                        logger.debug("Got new server IP: " + server_ip)
                        # Decoding the server IP for fun (plus it's a security flaw!)
                        # http://support.f5.com/kb/en-us/solutions/public/6000/900/sol6917.html
                        ip_split = server_ip.split(".")
                        assert len(ip_split) == 3
                        assert ip_split[2] == "0000"
                        ip_encoded = int(ip_split[0])
                        port_encoded = int(ip_split[1])
                        ip_encoded, ip_0 = divmod(ip_encoded, 256)
                        ip_encoded, ip_1 = divmod(ip_encoded, 256)
                        ip_3, ip_2 = divmod(ip_encoded, 256)
                        port_1, port_0 = divmod(port_encoded, 256)
                        port = port_0 * 256 + port_1
                        logger.debug("Decoded server IP: %d.%d.%d.%d:%d" % (ip_0, ip_1, ip_2, ip_3, port))


class SessionManager:
    def __init__(self, captcha_solver):
        self.session_data = SessionData()
        self.logged_in = False
        self.username = None
        self.captcha_image = None
        self.captcha_solver = captcha_solver

    @staticmethod
    def __get_login_data(username, password, captcha_answer):
        return {
            "loginUserDTO.user_name": username,
            "userDTO.password": password,
            "randCode": captcha_answer
        }

    @staticmethod
    def __get_captcha_request_params(captcha_type):
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
    def __get_captcha_check_data(captcha_type, answer):
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

    def __check_logged_in(self):
        url = "https://kyfw.12306.cn/otn/login/checkUser"
        cookies = self.session_data.get_session_cookies()
        response = requests.post(url, data=None, cookies=cookies, verify=False)
        response.raise_for_status()
        return common.read_json_data(response)["flag"] is True

    def __get_state_vars(self):
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
        state_js_lines = common.islice(html[state_begin:state_end].splitlines(), start=1)
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
                # That means no expressions or anything like that.
                assert False

        return state_dict

    def __check_captcha_needs_refresh(self, captcha_type):
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

    def login(self, username, password):
        if self.logged_in:
            logger.debug("Already logged in, if you are switching accounts, log out first!")
            return True

        # Sometimes we don't need to get a new captcha,
        # this can happen if the app has already fetched
        # one to display on the login screen.
        if self.__check_captcha_needs_refresh(CaptchaType.LOGIN):
            self.request_captcha_image(CaptchaType.LOGIN)

        captcha_answer = None
        while True:
            # Call the captcha solver function
            # This function is an implementation detail of the client program,
            # which means they are free to return the value however they want.
            # It can be an OCR program, TextBox value, console input, etc.
            try:
                captcha_answer = self.captcha_solver(self.captcha_image.image_data)
            except StopCaptchaRetry:
                # If the solver function throws StopCaptchaRetry, we abort the
                # login and return immediately
                logger.debug("Captcha aborted by user, login canceled")
                return False

            # Accept None as a sentinel value to change the captcha image.
            # Arguably, this is useless, since we could just return and have
            # the client re-call the login function.
            if captcha_answer is None:
                logger.debug("User requested captcha refresh, fetching new image")
                self.request_captcha_image(CaptchaType.LOGIN)
                continue

            logger.debug("Captcha input: " + captcha_answer)

            # Check captcha answer with the server
            # This "validates" our session ID token so we can log in
            if not self.check_captcha_answer(CaptchaType.LOGIN, captcha_answer):
                logger.debug("Incorrect captcha answer, retrying")
            else:
                break

        # Whoops, I logged your password in plain-text ;)
        logger.debug("Logging in with username {0} and password {1}".format(username, password))

        # Submit user credentials to the server
        data = self.__get_login_data(username, password, captcha_answer)
        url = "https://kyfw.12306.cn/otn/login/loginAysnSuggest"
        cookies = self.session_data.get_session_cookies()
        response = requests.post(url, data, cookies=cookies, verify=False)
        response.raise_for_status()
        # Check server response to see if login was successful
        # response > data > loginCheck should be "Y" if we logged in
        # otherwise, loginCheck will be absent
        json = common.read_json(response)
        success = common.get_dict_value_coalesce(json, "data", "loginCheck")
        if success:
            logger.debug("Login successful", response)
            self.logged_in = True
            self.username = username
        else:
            logger.debug("Login failed, reason: " + ";".join(json.get("messages")), response)

    def logout(self):
        if not self.logged_in:
            logger.debug("Already logged out, no need to log out again!")
            return

        response = requests.get("https://kyfw.12306.cn/otn/login/loginOut", verify=False)
        response.raise_for_status()
        logger.debug("Logged out of user: " + self.username, response)
        # Logging out gives us a new session ID token, 
        # but it's not really that useful anyways
        self.session_data.set_session_cookies(response)
        self.logged_in = False
        self.username = None

    def request_captcha_image(self, captcha_type):
        # Note: Requesting a login captcha while logged in seems to be okay,
        # but requesting a purchase captcha while logged out fails.

        url = "https://kyfw.12306.cn/otn/passcodeNew/getPassCodeNew.do"
        params = self.__get_captcha_request_params(captcha_type)
        cookies = self.session_data.get_session_cookies()
        response = requests.get(url, params=params, cookies=cookies, verify=False)
        response.raise_for_status()
        # If this is our first request, we will get a new session ID token.
        self.session_data.set_session_cookies(response)

        content_type = response.headers.get("Content-Type").split(";")[0]
        assert content_type == "image/jpeg"
        logger.debug("Fetched captcha image: " + response.url, response)
        self.captcha_image = CaptchaData(captcha_type, self.session_data.session_id, response.content)

    def check_captcha_answer(self, captcha_type, answer):
        url = "https://kyfw.12306.cn/otn/passcodeNew/checkRandCodeAnsyn"
        data = self.__get_captcha_check_data(captcha_type, answer)
        cookies = self.session_data.get_session_cookies()
        response = requests.post(url, data, cookies=cookies, verify=False)
        response.raise_for_status()
        success = common.is_true(common.read_json_data(response))
        logger.debug("Captcha entered correctly: " + str(success), response)
        return success

    def refresh_login_state(self):
        state_changed = False
        if self.__check_logged_in():
            username = self.__get_state_vars()["sessionInit"]
            if not self.logged_in or self.username != username:
                state_changed = True
            self.username = username
            self.logged_in = True
        else:
            if self.logged_in:
                state_changed = True
            self.username = None
            self.logged_in = False

        if state_changed:
            # This should not happen, unless our session timed out.
            # If it does, someone probably stole our session token.
            logger.warning("State changed when refreshing login status")

        return self.logged_in