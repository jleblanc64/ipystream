import asyncio
import time
from ipystream.voila.auth_wall_limit import KERNEL_CLEANUP_TIMEOUT_SEC
from ipystream.voila.error_handler import html
from ipystream.voila.patch_voila import _schedule_kernel_shutdown
from ipystream.voila.kernel import get_kernel_manager

timeout_seconds = 20
LOG_FILE = "/home/charles/Downloads/log.txt"

def clear_log():
    pass
    # try:
    #     with open(LOG_FILE, 'w') as _: pass
    # except: pass

def log_to_file(message):
    pass
    # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    # try:
    #     with open(LOG_FILE, "a") as f:
    #         f.write(f"[{timestamp}] {message}\n")
    # except: pass

# TODO sometimes kernel leak and are not killed. kill them even if busy after long time in cleanup_dead_kernels()
async def force_kill_kernel(kernel_id):
    log_to_file(f"Shielded kill task started for: {kernel_id}")
    try:
        mgr = get_kernel_manager()
        # 1. Try the standard Voila shutdown
        _schedule_kernel_shutdown(mgr, kernel_id)
        # 2. Aggressive: Direct manager shutdown request
        if hasattr(mgr, 'shutdown_kernel'):
            await asyncio.sleep(0.1) # Give it a tiny moment to process
            await asyncio.shield(mgr.shutdown_kernel(kernel_id, now=True))
        log_to_file(f"Successfully sent shutdown command for {kernel_id}")
    except Exception as e:
        log_to_file(f"Failed to kill kernel {kernel_id}: {str(e)}")

def timeout_spinner(_original_get_generator):
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
                    html_chunk = await asyncio.wait_for(agen.__anext__(), timeout=timeout_seconds)
                    chunks_yielded += 1
                    yield html_chunk

                except (StopAsyncIteration, asyncio.CancelledError, asyncio.TimeoutError) as e:
                    elapsed = time.time() - start_time
                    if isinstance(e, asyncio.TimeoutError) or elapsed >= (timeout_seconds - 0.05):
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