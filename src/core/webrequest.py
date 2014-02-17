import requests
import urllib.parse
from core.auth.cookies import SessionCookies


def request(method, url, params=None, data=None, cookies=None):
    if isinstance(params, list):
        url += "?" + urllib.parse.urlencode(params)
        params = None
    response = requests.request(method, url, params=params, cookies=cookies, data=data, verify=False)
    response.raise_for_status()
    if isinstance(cookies, SessionCookies):
        cookies.update_cookies(response)
    return response


def get(url, params=None, data=None, cookies=None):
    return request("get", url, params, data, cookies)


def post(url, params=None, data=None, cookies=None):
    return request("post", url, params, data, cookies)