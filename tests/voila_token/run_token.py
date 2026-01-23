from ipystream.voila import run_raw

use_xpython = True
POOL_SIZE = 1

print("http://localhost:8866?tok=a")
print("http://localhost:8866?tok=b")
print("http://localhost:8866?tok=c")
print("http://localhost:8866?tok=d")

run_raw.run(
    disable_logging=True,
    POOL_SIZE=POOL_SIZE,
    use_xpython=use_xpython,
    enforce_PARAM_KEY_TOKEN=True,
    log_user_fun=None,
    token_to_user_fun=lambda x: x,
    extra_args_override=None,
)
