import asyncio
from functools import wraps


class AsyncDebouncer:
    def __init__(self, wait: float):
        self.wait = wait
        self._task = None

    def __call__(self, func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop — skip the call entirely
                return

            if self._task:
                self._task.cancel()

            async def delayed_call():
                try:
                    await asyncio.sleep(self.wait)
                    res = func(*args, **kwargs)
                    if asyncio.iscoroutine(res):
                        await res
                except asyncio.CancelledError:
                    pass

            try:
                self._task = loop.create_task(delayed_call())
            except RuntimeError:
                # Loop closed or invalid — skip
                pass

        return wrapped
