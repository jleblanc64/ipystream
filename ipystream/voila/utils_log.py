from datetime import datetime

LOG_FILE = "/home/charles/Downloads/log.txt"
ENABLE_LOG = False

def clear_log():
    if not ENABLE_LOG:
        return

    try:
        with open(LOG_FILE, 'w') as _: pass
    except: pass

def log_to_file(message):
    if not ENABLE_LOG:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except: pass
