import asyncio
import subprocess
import time
from datetime import datetime

from ipystream.voila.auth_wall_limit import KERNEL_CLEANUP_TIMEOUT_SEC
from ipystream.voila.error_handler import html
from ipystream.voila.patch_voila import _schedule_kernel_shutdown
from ipystream.voila.kernel import get_kernel_manager

LOG_FILE = "/home/charles/Downloads/log.txt"
ENABLE_LOG = False

def clear_log():
    if not ENABLE_LOG:
        return

    try:
        with open(LOG_FILE, 'w') as _: pass
    except: pass

def log_to_file(message):
    if not ENABLE_LOG:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except: pass

# TODO sometimes kernel leak and are not killed. kill them even if busy after long time in cleanup_dead_kernels()
async def force_kill_kernel(kernel_id):
    log_to_file(f"Shielded kill task started for: {kernel_id}")
    try:
        mgr = get_kernel_manager()
        kernel = mgr.get_kernel(kernel_id)

        # 1. Get the actual System PID
        pid = kernel.provisioner.process.pid

        # 2. Attempt standard shutdown
        _schedule_kernel_shutdown(mgr, kernel_id)

        # 3. Give it a moment, then force kill via Bash
        await asyncio.sleep(0.5)
        subprocess.run(["kill", "-9", str(pid)], check=False)

        log_to_file(f"Successfully forced termination for {kernel_id} (PID: {pid})")
    except Exception as e:
        log_to_file(f"Failed to kill kernel {kernel_id}: {str(e)}")

def timeout(_original_get_generator, timeout_spinner):
    clear_log()

    async def patched_get_generator(self, *args, **kwargs):
        log_to_file("get_generator started")

        agen = _original_get_generator(self, *args, **kwargs)
        start_time = time.time()
        curr_kernel_id = None
        chunks_yielded = 0

        try:
            while True:
                # Polling for ID
                if not curr_kernel_id:
                    curr_kernel_id = getattr(self, "kernel_id", None) or \
                                     getattr(self, "_recovered_kernel_id", None)
                    if not curr_kernel_id and hasattr(self, "kernel_manager"):
                        curr_kernel_id = getattr(self.kernel_manager, "kernel_id", None)

                try:
                    # Fetch next chunk
                    html_chunk = await asyncio.wait_for(agen.__anext__(), timeout=timeout_spinner)
                    chunks_yielded += 1
                    yield html_chunk

                except (StopAsyncIteration, asyncio.CancelledError, asyncio.TimeoutError) as e:
                    elapsed = time.time() - start_time
                    if isinstance(e, asyncio.TimeoutError) or elapsed >= (timeout_spinner - 0.05):
                        log_to_file(f"TIMEOUT DETECTED ({elapsed:.2f}s)")

                        # Resolve the ID
                        final_id = curr_kernel_id
                        if not final_id and hasattr(self, "kernel_manager"):
                            ids = self.kernel_manager.list_kernel_ids()
                            if ids: final_id = ids[-1]

                        if final_id:
                            # SHIELD the cleanup so refresh doesn't cancel the kill
                            asyncio.create_task(force_kill_kernel(final_id))
                            yield f"<div style='background:red; color:white; padding:10px;'>Timeout: Kernel {final_id} killed.</div>"
                        else:
                            log_to_file("Could not find kernel ID to kill!")
                        break
                    else:
                        # Clean finish or immediate DeadKernelError
                        break

        except Exception as e:
            custom_html = html(e, KERNEL_CLEANUP_TIMEOUT_SEC)
            if custom_html:
                yield custom_html
            else:
                log_to_file(f"UNCAUGHT EXCEPTION: {type(e).__name__}: {str(e)}")
                raise

    return patched_get_generator