import asyncio
import time
from functools import wraps


class AsyncDebouncerGemini:
    def __init__(self, wait: float):
        self.wait = wait
        self._handle = None
        self._last_args = None
        self._last_kwargs = None
        self._last_invocation_time = 0.0

    def __call__(self, func):
        @wraps(func)
        def debounced_wrapper(*args, **kwargs):
            self._last_args = args
            self._last_kwargs = kwargs
            self._last_invocation_time = time.time()

            if self._handle and not self._handle.cancelled():
                self._handle.cancel()

            loop = asyncio.get_running_loop()

            self._handle = loop.call_later(self.wait, self._execute_debounced_func, func)

        return debounced_wrapper

    def _execute_debounced_func(self, func):
        try:
            if time.time() - self._last_invocation_time >= self.wait:
                func(*self._last_args, **self._last_kwargs)
        finally:
            self._handle = None
