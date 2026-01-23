from datetime import datetime
from tornado.web import StaticFileHandler
from ipystream.voila.patched_generator2 import LOG_FILE


def slow_connection():
    clear_log()

    _original_write = StaticFileHandler.write
    _original_prepare = StaticFileHandler.prepare

    def patched_prepare(self):
        path = self.request.path
        log_to_file(f"prepare(): {path}")

        if "widget" in path: raise Exception("a")

        return _original_prepare(self)

    def patched_write(self, chunk):
        path = self.request.path
        log_to_file(f"write(): {path}")

        if "widget" in path: raise Exception("a")

        return _original_write(self, chunk)

    StaticFileHandler.prepare = patched_prepare
    StaticFileHandler.write = patched_write

def clear_log():
    try:
        with open(LOG_FILE, 'w') as _: pass
    except: pass

def log_to_file(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except: pass
