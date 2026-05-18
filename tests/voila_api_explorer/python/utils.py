from jproperties import Properties

def load_creds(path: str) -> tuple[str, str]:
    props = Properties()
    with open(path, "rb") as f:
        props.load(f)

    username = props.get("username").data
    password = props.get("password").data
    return username, password
