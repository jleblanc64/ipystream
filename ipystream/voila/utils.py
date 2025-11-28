import os
from http.cookies import SimpleCookie

PARAM_KEY_TOKEN = "tok"


def get_token_from_headers(headers_dict):
    cookie = headers_dict.get("Cookie")
    if not cookie:
        return None

    return get_cookie_value(cookie, PARAM_KEY_TOKEN)


def get_cookie_value(cookie_str, key):
    cookie = SimpleCookie()
    cookie.load(cookie_str)
    if key in cookie:
        return cookie[key].value
    return None


def is_sagemaker():
    sm_vars = [
        "SAGEMAKER_SPACE_NAME",
        "SAGEMAKER_APP_TYPE",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    ]
    return any(var in os.environ for var in sm_vars)
