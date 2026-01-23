import asyncio
import json
from filelock import FileLock
from jupyter_server.services.kernels.kernelmanager import MappingKernelManager
from tornado.web import HTTPError
from voila import voila_kernel_manager

from ipystream.voila.kernel import (
    get_kernel_manager,
    get_original_shutdown_kernel,
    _load_kernel_to_user,
    _save_kernel_to_user,
    KERNEL_TO_TOKEN_FILE,
)
from ipystream.voila.utils import get_token_from_headers

KERNEL_CLEANUP_TIMEOUT_SEC = 20
FILE_LOCK = "kernel.lock"


def patch(log_user_fun, token_to_user_fun, MAX_KERNELS):
    # --- Monkey-patch shutdown_kernel to block external calls ---
    def controlled_shutdown_kernel(self, kernel_id, **kwargs):
        return asyncio.ensure_future(asyncio.sleep(0))  # Dummy completed awaitable

    MappingKernelManager.shutdown_kernel = controlled_shutdown_kernel

    # --- Patch kernel manager factory to assign user from handler ---
    _original_factory = voila_kernel_manager.voila_kernel_manager_factory

    def patched_voila_kernel_manager_factory(*args, **kwargs):
        VoilaKernelManagerCls = _original_factory(*args, **kwargs)

        _original_get_rendered_notebook = VoilaKernelManagerCls.get_rendered_notebook

        async def _patched_get_rendered_notebook(
            self, notebook_name: str, extra_kernel_env_variables: dict = {}, **kwargs
        ):
            running = self.list_kernel_ids()
            if len(running) >= MAX_KERNELS:
                raise HTTPError(503)

            token = None
            user = None
            headers = extra_kernel_env_variables.get("headers")
            if headers:
                headers_dict = json.loads(headers)
                token = get_token_from_headers(headers_dict)

            if token and token_to_user_fun:
                user = token_to_user_fun(token)

            with FileLock(FILE_LOCK):
                if user:
                    data = _load_kernel_to_user()
                    await check_user_kernel_conflict(user, data)

            # Call original method to get preheated kernel
            (
                render_task,
                rendered_cache,
                kernel_id,
            ) = await _original_get_rendered_notebook(
                self, notebook_name, extra_kernel_env_variables, **kwargs
            )

            # Map kernel to user if available
            if user:
                data = _load_kernel_to_user()
                data_token = _load_kernel_to_user(KERNEL_TO_TOKEN_FILE)

                data[kernel_id] = user
                data_token[kernel_id] = token

                if log_user_fun:
                    with FileLock(FILE_LOCK):
                        log_user_fun(token)

                _save_kernel_to_user(data)
                _save_kernel_to_user(data_token, KERNEL_TO_TOKEN_FILE)

            return render_task, rendered_cache, kernel_id

        VoilaKernelManagerCls.get_rendered_notebook = _patched_get_rendered_notebook
        return VoilaKernelManagerCls

    voila_kernel_manager.voila_kernel_manager_factory = (
        patched_voila_kernel_manager_factory
    )

    async def check_user_kernel_conflict(user: str, data: dict):
        global_kernel_manager = get_kernel_manager()

        count = 0
        for existing_kid, existing_user in data.items():
            if existing_user == user:
                count += 1
                km_info = global_kernel_manager.kernel_model(existing_kid)
                connections = km_info["connections"]
                if connections == 0:
                    # kill existing
                    _original_shutdown_kernel = get_original_shutdown_kernel()
                    await _original_shutdown_kernel(
                        global_kernel_manager, existing_kid, now=True
                    )
                    continue

                raise HTTPError(
                    503, f"User '{user}' already has a running kernel ({existing_kid})"
                )

        if count > 2:
            raise HTTPError(503, f"User '{user}' already has 2 running kernels")
