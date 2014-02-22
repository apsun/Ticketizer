# -*- coding: utf-8 -*-
from core import logger


class SessionCookies(dict):
    @property
    def session_id(self):
        # noinspection PyTypeChecker
        return self.get("JSESSIONID")

    @classmethod
    def __handle_cookie_changed(cls, name, value):
        return {
            "JSESSIONID": cls.__handle_session_id,
            "BIGipServerotn": cls.__handle_server_ip
        }.get(name, cls.__handle_other_cookie)(name, value)

    @staticmethod
    def __handle_other_cookie(name, value):
        pass

    # noinspection PyUnusedLocal
    @staticmethod
    def __handle_session_id(name, value):
        logger.debug("Got new session ID: " + value)

    # noinspection PyUnusedLocal
    @staticmethod
    def __handle_server_ip(name, value):
        logger.debug("Got new server IP: " + value)
        # Decoding the server IP for fun (plus it's a security flaw!)
        # http://support.f5.com/kb/en-us/solutions/public/6000/900/sol6917.html
        ip_split = value.split(".")
        assert len(ip_split) == 3
        assert ip_split[2] == "0000"
        ip_encoded = int(ip_split[0])
        port_encoded = int(ip_split[1])
        ip_encoded, ip_0 = divmod(ip_encoded, 256)
        ip_encoded, ip_1 = divmod(ip_encoded, 256)
        ip_3, ip_2 = divmod(ip_encoded, 256)
        port_1, port_0 = divmod(port_encoded, 256)
        port = port_0 * 256 + port_1
        logger.debug("Decoded server IP: {0}.{1}.{2}.{3}:{4}".format(ip_0, ip_1, ip_2, ip_3, port))

    def update_cookies(self, response):
        # This function parses an HTTP response and sets the
        # session ID/server IP tokens accordingly (if found).
        cookies = response.headers.get("Set-Cookie")
        if cookies is None:
            return
        for cookie in map(lambda x: x.split("="), cookies.replace(",", ";").split(";")):
            key, value = cookie[0].strip(), cookie[1].strip()
            if key.lower() == "path":
                continue
            self[key] = value
            self.__handle_cookie_changed(key, value)