from ipystream.voila import run_raw
from tests.voila_raw_widgets.slow_connection import slow_connection

use_xpython = True
POOL_SIZE = 1

slow_connection()
run_raw.run(
    disable_logging=True,
    POOL_SIZE=POOL_SIZE,
    use_xpython=use_xpython,
    enforce_PARAM_KEY_TOKEN=False,
    log_user_fun=None,
    token_to_user_fun=None,
    extra_args_override=None,
)