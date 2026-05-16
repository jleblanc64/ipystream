from tests.voila_api_explorer.python.utils_properties import Properties

def load_creds(path: str) -> tuple[str, str]:
    configs = load_config(path)
    username = configs.get("username").data
    password = configs.get("password").data

    return username, password

def load_config(path: str) -> Properties:
    configs = Properties()
    with open(path, "rb") as f:
        configs.load(f)

    return configs