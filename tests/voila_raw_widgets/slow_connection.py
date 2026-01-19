from tornado.web import StaticFileHandler

def slow_connection():

    def patched_prepare(_): raise Exception("a")
    def patched_write(_, __): raise Exception("a")

    StaticFileHandler.prepare = patched_prepare
    StaticFileHandler.write = patched_write