import logging
import os
import sys
from ipystream.voila import patched_generator, auth_wall_limit, patch_voila
from ipystream.voila.utils import create_ipynb


def run(
    disable_logging,
    POOL_SIZE=2,
    use_xpython=False,
    enforce_PARAM_KEY_TOKEN=False,
    log_user_fun=None,
    token_to_user_fun=None,
    extra_args_override=None,
):
    patched_generator.patch_voila_get_generator(enforce_PARAM_KEY_TOKEN)
    auth_wall_limit.patch(log_user_fun, token_to_user_fun)

    NOTEBOOK = "jupyter.ipynb"

    os.environ["VOILA_APP"] = "1"
    extra_args = [
        "--port=8866",
        "--no-browser",
        "--Voila.ip=0.0.0.0",
        "--base_url=/",
        "--ServerApp.log_level=ERROR",
        "--show_tracebacks=True",
        "--preheat_kernel=True",
        f"--pool_size={POOL_SIZE}",
    ]

    if extra_args_override:
        extra_args = extra_args_override

    create_ipynb(NOTEBOOK, use_xpython)
    sys.argv = ["voila", NOTEBOOK] + extra_args

    # start Voila
    voila_app = patch_voila.patch()
    voila_app.initialize()
    print("VOILA: http://localhost:8866")

    if disable_logging:
        logging.disable(logging.CRITICAL)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)

    voila_app.start()
