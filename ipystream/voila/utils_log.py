import datetime
from ipystream.voila.kernel import find_project_root


class SimpleLogger:
    def __init__(self, filepath):
        self.filepath = filepath

    def __call__(self, message):
        with open(self.filepath, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")


# global logger
log_path = find_project_root() / "logs.txt"


def cleanup_log():
    log_path.write_text("")


log = SimpleLogger(log_path)

#
LOG_FILE = "/home/charles/Downloads/log.txt"
ENABLE_LOG = False


def clear_log():
    if not ENABLE_LOG:
        return

    try:
        with open(LOG_FILE, "w") as _:
            pass
    except:
        pass


def log_to_file(message):
    if not ENABLE_LOG:
        return

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass
