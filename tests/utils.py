import asyncio

async def wait_stream_async(i, l):
    for _ in range(15):
        if l.stream_update_done_count == i:
            return
        await asyncio.sleep(1)  # non-blocking sleep

    raise Exception(
        f"Stream didn't finish. Expected {i}, but was {l.stream_update_done_count}"
    )
