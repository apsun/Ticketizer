# -*- coding: utf-8 -*-
import logger


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