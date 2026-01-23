from tornado.web import StaticFileHandler

from ipystream.voila import utils_log
from ipystream.voila.utils_log import log_to_file, clear_log


def slow_connection():
    utils_log.ENABLE_LOG = True
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
