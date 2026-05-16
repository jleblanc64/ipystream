from ipystream.voila import run_raw
from tests.voila_api_explorer.python.utils import load_creds

load_creds("/home/charles/Desktop/SEP.properties")
run_raw.run(MAX_KERNELS=3)
