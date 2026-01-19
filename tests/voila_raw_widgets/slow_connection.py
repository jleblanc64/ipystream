import time

from tornado.web import StaticFileHandler


def slow_connection():
    LATENCY_PER_CHUNK = 1.0   # seconds per chunk
    BYTES_PER_CHUNK = 1024    # send in small pieces
    _triggered = False

    _original_write = StaticFileHandler.write
    _original_prepare = StaticFileHandler.prepare

    def patched_prepare(self):
        path = self.request.path

        global _triggered
        if not _triggered and path.endswith(".js") and "require" not in path:
            _triggered = True
            print(f"⏳ Streaming JS slowly to trigger RequireJS timeout: {path}")
            self._slow_stream = True
        else:
            self._slow_stream = False

        return _original_prepare(self)

    def patched_write(self, chunk):
        if getattr(self, "_slow_stream", False):
            # send chunk-by-chunk with delay
            if isinstance(chunk, (bytes, str)):
                for i in range(0, len(chunk), BYTES_PER_CHUNK):
                    piece = chunk[i:i + BYTES_PER_CHUNK]
                    _original_write(self, piece)
                    _original_write(self, b"")  # force flush
                    time.sleep(LATENCY_PER_CHUNK)
                return  # prevent original write from sending the whole buffer
        return _original_write(self, chunk)

    StaticFileHandler.prepare = patched_prepare
    StaticFileHandler.write = patched_write