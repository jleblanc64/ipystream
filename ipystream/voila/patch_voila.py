# --- Configuration ---
import asyncio
import logging
import threading
import time
from collections import defaultdict

import tornado
from tornado.ioloop import IOLoop

from ipystream.voila.cookie import add_v_cookie
from ipystream.voila.kernel import (
    get_original_shutdown_kernel,
    _load_kernel_to_user,
    KERNEL_TO_TOKEN_FILE,
    _save_kernel_to_user,
)
from ipystream.voila.auth_wall_limit import (
    KERNEL_CLEANUP_TIMEOUT_SEC,
    get_kernel_manager,
)

NOTEBOOK = "misc/demo.ipynb"
POOL_SIZE = 2
KERNEL_TO_USER_FILE = "kernel_to_user.json"
MAIN_LOOP = IOLoop.current()

# --- Global State ---
_kernel_lock = threading.Lock()
_forced_shutdowns = set()
kernel_connection_tracker = defaultdict(lambda: {"zero_connection_start": None})


def patch():
    # --- RESET kernel_to_user.json ---
    _save_kernel_to_user({})
    _save_kernel_to_user({}, KERNEL_TO_TOKEN_FILE)

    # voila logger
    voila_logger = logging.getLogger("voila")
    voila_logger.setLevel(logging.CRITICAL + 1)
    for handler in voila_logger.handlers[:]:
        voila_logger.removeHandler(handler)

    # --- Start the watchdog thread ---
    watchdog = threading.Thread(target=kernel_watchdog_thread, daemon=True)
    watchdog.start()

    # patch voila app
    from voila.app import Voila
    from voila.static_file_handler import AllowListFileHandler

    add_v_cookie(Voila)

    def patched_get_absolute_path(self, root, path):
        return super(AllowListFileHandler, self).get_absolute_path(root, path)

    AllowListFileHandler.get_absolute_path = patched_get_absolute_path
    return Voila()


# --- Shutdown Scheduler ---
def _schedule_kernel_shutdown(km_instance, kernel_id):
    async def do_shutdown():
        _original_shutdown_kernel = get_original_shutdown_kernel()
        try:
            await _original_shutdown_kernel(km_instance, kernel_id)
        except Exception:
            pass

    # Schedule on the main Tornado IOLoop
    MAIN_LOOP.add_callback(lambda: asyncio.ensure_future(do_shutdown()))


# --- EXCEPTION SWALLOWING PATCH for static_url ---
_original_static_url = tornado.web.RequestHandler.static_url


def patched_static_url(self, path, include_host=None, **kwargs):
    try:
        return _original_static_url(self, path, include_host=include_host, **kwargs)
    except Exception as e:
        if "You must define the 'static_path'" in str(e):
            return f"/voila/static/{path}"
        raise


tornado.web.RequestHandler.static_url = patched_static_url


# --- Watchdog helpers ---
def get_pool_kernel_ids(km):
    pool_ids = set()
    for tasks in km._pools.values():
        for task in tasks:
            if task.done():
                result = task.result()
                kernel_id = result.get("kernel_id")
                if kernel_id:
                    pool_ids.add(kernel_id)

    return pool_ids


def cleanup_dead_kernels():
    global_kernel_manager = get_kernel_manager()
    if global_kernel_manager is None:
        return

    pool_ids = get_pool_kernel_ids(global_kernel_manager)

    with _kernel_lock:
        now = time.time()
        running_kernels = global_kernel_manager.list_kernel_ids()

        # Remove trackers for kernels that no longer exist
        active_ids = set(running_kernels)
        dead_tracked_ids = list(kernel_connection_tracker.keys() - active_ids)
        for dead_id in dead_tracked_ids:
            del kernel_connection_tracker[dead_id]

        # Remove dead kernels from kernel_to_user.json
        data = _load_kernel_to_user()
        data_token = _load_kernel_to_user(KERNEL_TO_TOKEN_FILE)
        removed = False
        for k in list(data.keys()):
            if k not in running_kernels:
                del data[k]
                del data_token[k]
                removed = True
        if removed:
            _save_kernel_to_user(data)
            _save_kernel_to_user(data_token, KERNEL_TO_TOKEN_FILE)

        # kill duplicate user kernels
        for kernel_id in duplicates(data):
            _forced_shutdowns.add(kernel_id)
            _schedule_kernel_shutdown(global_kernel_manager, kernel_id)

        for kernel_id in running_kernels:
            if kernel_id in _forced_shutdowns:
                continue

            in_pool = kernel_id in pool_ids
            if in_pool:
                continue

            try:
                km_info = global_kernel_manager.kernel_model(kernel_id)
                connections = km_info["connections"]
                tracker = kernel_connection_tracker[kernel_id]

                if connections > 0 or km_info["execution_state"] != "idle":
                    tracker["zero_connection_start"] = None
                else:
                    if tracker["zero_connection_start"] is None:
                        tracker["zero_connection_start"] = now
                    else:
                        zero_duration = now - tracker["zero_connection_start"]
                        if zero_duration >= KERNEL_CLEANUP_TIMEOUT_SEC:
                            _forced_shutdowns.add(kernel_id)
                            _schedule_kernel_shutdown(global_kernel_manager, kernel_id)

            except Exception:
                pass

        cleanup_forced_shutdowns(_forced_shutdowns, running_kernels)


def duplicates(data: dict[str, str]) -> list[str]:
    seen = {}
    to_kill = []

    for kernel_id, username in data.items():
        if username in seen:
            to_kill.append(kernel_id)
        else:
            seen[username] = True

    return to_kill


def cleanup_forced_shutdowns(
    forced_shutdowns: set[str], running_kernels: set[str]
) -> None:
    """
    Remove any kernel IDs from forced_shutdowns that are not in running_kernels.
    Modifies forced_shutdowns in place.
    """
    forced_shutdowns.intersection_update(running_kernels)


def kernel_watchdog_thread():
    while True:
        try:
            cleanup_dead_kernels()
        except Exception:
            pass
        time.sleep(2)
