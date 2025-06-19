import time


def wait_stream(i, l):
    for _ in range(40):
        if l.stream_update_done_count == i:
            return
        time.sleep(1)

    raise Exception("Stream didn't finish")