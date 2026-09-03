import os
import ipystream
from ipystream.voila.utils import OS_JWT_OVERRIDE
from tests.voila_token_override.notebook import load_creds
import requests as r

username, password = load_creds("/home/charles/Desktop/SEP.properties")
base_url = "https://eu-north-1-api.dev.sympheny.com/"

os.environ[OS_JWT_OVERRIDE] = r.post(
    f"{base_url}backoffice/auth/ext/token", json={"email": username, "password": password}
).json()["access_token"]

ipystream.run()
