import asyncio
import traceback
from filelock import FileLock
from ipystream.voila.kernel import _save_kernel_to_user, _load_kernel_to_user
from tornado.web import HTTPError
from voila import voila_kernel_manager
from ipystream.voila.kernel import *
from ipystream.voila.utils import get_token_from_headers
from ipystream.voila.utils_log import log

KERNEL_CLEANUP_TIMEOUT_SEC = 20

# --- GLOBAL LOCKS ---
local_async_lock = asyncio.Lock()
file_lock = FileLock("kernel.lock")

def patch(log_user_fun, token_to_user_fun, MAX_KERNELS):
    def controlled_shutdown_kernel(self, kernel_id, **kwargs):
        return asyncio.ensure_future(asyncio.sleep(0))

    MappingKernelManager.shutdown_kernel = controlled_shutdown_kernel
    _original_factory = voila_kernel_manager.voila_kernel_manager_factory

    def patched_voila_kernel_manager_factory(*args, **kwargs):
        VoilaKernelManagerCls = _original_factory(*args, **kwargs)
        _original_get_rendered_notebook = VoilaKernelManagerCls.get_rendered_notebook

        async def _patched_get_rendered_notebook(
                self, notebook_name: str, extra_kernel_env_variables: dict = {}, **kwargs
        ):
            token = None
            user = None
            headers = extra_kernel_env_variables.get("headers")
            if headers:
                headers_dict = json.loads(headers)
                token = get_token_from_headers(headers_dict)

            if token and token_to_user_fun:
                user = token_to_user_fun(token)

            loop = asyncio.get_running_loop()

            # 1. THE DOUBLE-BARREL LOCK
            # First, serialize access within this specific async process
            async with local_async_lock:
                # Second, serialize access across all processes on the server
                await loop.run_in_executor(None, lambda: file_lock.acquire(timeout=20))

                try:
                    log(f"LOCK ACQUIRED: {user or 'unknown'}")
                    if user:
                        data = _load_kernel_to_user()
                        await check_user_kernel_conflict(user, data)

                    # 2. THE GATEKEEPER WAIT
                    # We wait until the kernel is READY in Voila's internal pool.
                    # This is the primary defense against "Kernel pool is empty"
                    max_wait = 15.0
                    start_wait = loop.time()

                    while (loop.time() - start_wait) < max_wait:
                        runnings = self.list_kernel_ids()

                        # A) Process check
                        preheated_ids = [k for k in runnings if self.kernel_model(k).get('connections', 0) == 0]

                        # B) Voila internal pool check
                        nb_pool = self._pools.get(notebook_name, [])
                        ready_in_pool = [t for t in nb_pool if t.done()]

                        if len(runnings) >= MAX_KERNELS:
                            log(f"REJECT: Server capacity reached ({len(runnings)})")
                            raise HTTPError(504, "Server is full")

                        # Only break if there is actually a kernel ready to be popped from the pool
                        if len(ready_in_pool) >= 1:
                            log(f"GATE OPEN: Pool has {len(ready_in_pool)} ready kernels.")
                            break

                        log(f"WAITING: Process Idle={len(preheated_ids)} | Pool Ready={len(ready_in_pool)}")
                        await asyncio.sleep(0.5)

                    try:
                        # 3. CALL ORIGINAL
                        # We are now guaranteed that len(ready_in_pool) >= 1
                        (
                            render_task,
                            rendered_cache,
                            kernel_id,
                        ) = await _original_get_rendered_notebook(
                            self, notebook_name, extra_kernel_env_variables, **kwargs
                        )

                    except Exception as e:
                        log(f"!!! ERROR DURING RENDER: {str(e)}")
                        log(traceback.format_exc())
                        raise e

                finally:
                    # 5. RELEASE GLOBAL BRIDGE
                    await loop.run_in_executor(None, file_lock.release)
                    log(f"LOCK RELEASED: {user or 'unknown'}")

            # 6. Map kernel to user (Outside the heavy lock)
            if user and kernel_id:
                data = _load_kernel_to_user()
                data_token = _load_kernel_to_user(KERNEL_TO_TOKEN_FILE)

                data[kernel_id] = user
                data_token[kernel_id] = token

                if log_user_fun:
                    log_user_fun(token)

                _save_kernel_to_user(data)
                _save_kernel_to_user(data_token, KERNEL_TO_TOKEN_FILE)

            return render_task, rendered_cache, kernel_id

        VoilaKernelManagerCls.get_rendered_notebook = _patched_get_rendered_notebook
        return VoilaKernelManagerCls

    voila_kernel_manager.voila_kernel_manager_factory = patched_voila_kernel_manager_factory

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