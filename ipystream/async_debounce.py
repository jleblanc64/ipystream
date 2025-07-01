import asyncio
from functools import wraps


class AsyncDebouncer:
    def __init__(self, wait: float):
        self.wait = wait
        self._task = None

    def __call__(self, func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            loop = asyncio.get_running_loop()
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

            self._task = loop.create_task(delayed_call())

        return wrapped
