import os
import ipystream
from ipystream.voila.utils import OS_JWT_OVERRIDE
from tests.voila_token_override.notebook import load_creds
import requests as r

u, p = load_creds("/home/charles/Desktop/SEP.properties")
url = "https://eu-north-1-api.dev.sympheny.com/backoffice/auth/ext/token"
os.environ[OS_JWT_OVERRIDE] = r.post(url, json={"email": u, "password": p}).json()["access_token"]

ipystream.run()
