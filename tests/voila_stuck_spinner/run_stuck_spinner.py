from ipystream.voila import run_raw, utils_log
from ipystream.voila.utils_log import clear_log

utils_log.ENABLE_LOG = True
clear_log()
# run_raw.run(timeout_spinner=2)
run_raw.run(timeout_spinner=20)
