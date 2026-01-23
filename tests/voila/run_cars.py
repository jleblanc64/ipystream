from ipystream.voila import run_raw

use_xpython = True
POOL_SIZE = 1

run_raw.run(
    disable_logging=True,
    POOL_SIZE=POOL_SIZE,
    use_xpython=use_xpython,
    enforce_PARAM_KEY_TOKEN=False,
    log_user_fun=None,
    token_to_user_fun=None,
    extra_args_override=None,
)
