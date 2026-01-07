from functools import wraps
from threading import Timer


class AsyncDebouncer:
    def __init__(self, wait: float):
        self.wait = wait
        self.timer = None

    def __call__(self, func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            # 1. Cancel the existing timer if it exists
            if self.timer is not None:
                self.timer.cancel()

            # 2. Define the work to be done
            def call_it():
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    # Catch errors so they don't silently kill the thread
                    print(f"Error in debounced function: {e}")

            # 3. Start a new timer (in a separate thread)
            self.timer = Timer(self.wait, call_it)
            self.timer.start()

        return wrapped
