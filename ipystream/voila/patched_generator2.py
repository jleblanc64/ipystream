import asyncio
import time
from nbclient.exceptions import DeadKernelError
from voila.execute import VoilaExecutor

from ipystream.voila.auth_wall_limit import KERNEL_CLEANUP_TIMEOUT_SEC
from ipystream.voila.error_handler import html
from ipystream.voila.kernel import get_kernel_manager
from ipystream.voila.patch_voila import _schedule_kernel_shutdown
from ipystream.voila.utils_log import log_to_file

def kill_kernel(kernel_id):
    if not kernel_id or str(kernel_id) == "None":
        return

    try:
        mgr = get_kernel_manager()
        _schedule_kernel_shutdown(mgr, kernel_id)

        log_to_file(f"[KILL] Killed kernel {kernel_id}")
    except Exception as e:
        log_to_file(f"[KILL] Error during cleanup: {e}")

_original_execute_cell = VoilaExecutor.execute_cell

async def patched_execute_cell(self, *args, **kwargs):
    # Retrieve ID early
    kid = getattr(self, "kernel_id", None) or \
          (getattr(self.km, "kernel_id", None) if hasattr(self, "km") else None)

    try:
        return await _original_execute_cell(self, *args, **kwargs)
    except (DeadKernelError, Exception) as e:
        # If the cell crashes or times out, trigger the kill immediately
        log_to_file(f"[EXECUTOR] Error: {type(e).__name__}. Killing {kid}")
        kill_kernel(kid)

        # Flag this instance so the generator knows the death was handled
        self._intentional_death = True

        # Return the cell object to prevent the 'Error Page' from rendering
        return args[0] if len(args) > 0 else None

VoilaExecutor.execute_cell = patched_execute_cell


def timeout(_original_get_generator, timeout_spinner):
    async def patched_get_generator(self, *args, **kwargs):
        log_to_file("--- WATCHDOG START ---")
        agen = _original_get_generator(self, *args, **kwargs)
        start_time = time.perf_counter()

        # ID resolution from generator or executor
        curr_id = getattr(self, "kernel_id", None)
        if not curr_id and hasattr(self, "executor"):
            curr_id = getattr(self.executor, "kernel_id", None)

        try:
            while True:
                elapsed = time.perf_counter() - start_time
                remaining = timeout_spinner - elapsed

                if remaining <= 0:
                    raise asyncio.TimeoutError()

                try:
                    # Request next chunk
                    yield await asyncio.wait_for(agen.__anext__(), timeout=max(0.01, remaining))
                except StopAsyncIteration:
                    break

        except (asyncio.TimeoutError, DeadKernelError, asyncio.CancelledError) as e:
            log_to_file(f"[WATCHDOG EXIT] Reason: {type(e).__name__}")
            kill_kernel(curr_id)
            return

        except Exception as e:
            custom_html = html(e, KERNEL_CLEANUP_TIMEOUT_SEC)
            if custom_html:
                yield custom_html
            else:
                log_to_file(f"UNCAUGHT EXCEPTION: {type(e).__name__}: {str(e)}")
                raise

    return patched_get_generator