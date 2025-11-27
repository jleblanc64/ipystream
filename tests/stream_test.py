from typing import Callable

import pytest
from ipywidgets import HTML, RadioButtons
from ipystream.stream import Stream, WidgetCurrentsChildren
from tests.utils import wait_stream_async


def drop(v):
    return RadioButtons(options=[v])


def drop_l(l):
    return RadioButtons(options=l)


tree = {"a": [["a1", "a2"], ["b1", "b2"]], "c": [["a1"], ["c2", "c3", "c4"]]}


def updaterI(lvl) -> Callable[[WidgetCurrentsChildren], None]:
    def updater(w: WidgetCurrentsChildren):
        if lvl == 1:
            value = w.parents[0].value
            lvl_2 = tree[value]
            for i, _ in enumerate(w.currents):
                w.display_or_update(RadioButtons(options=lvl_2[i]))

        else:
            concat = "".join([x.value for x in w.parents])
            for i, _ in enumerate(w.currents):
                if i == 0:
                    opts = [f"{concat}_{str(i)}"]
                    w.display_or_update(RadioButtons(options=opts))
                else:
                    html = f"<div style='border-style: solid;padding: 10px;'>{concat}_{str(i)}</>"
                    w.display_or_update(HTML(html))

    return updater


cache = {
    "quiet_display": True,
}

@pytest.mark.asyncio
async def test():
    s = Stream(cache=cache, debounce_sec=0.2)
    widget1 = drop_l(["a", "c"])
    s.register(1, [lambda x: widget1])
    s.register(2, [lambda x: drop("c"), lambda x: drop("d")], updaterI(1))
    s.register(3, [lambda x: drop("f"), lambda x: HTML("f2")], updaterI(2))

    s.display_registered()

    #
    widget1.value = "c"
    await wait_stream_async(1, s)
    hbox = s.cache["logs"]["3"].children
    assert hbox[0].value == "a1c2_0"
    assert ">a1c2_1<" in hbox[1].value

    widget1.value = "a"
    await wait_stream_async(2, s)
    hbox = s.cache["logs"]["3"].children
    assert hbox[0].value == "a1b1_0"
    assert ">a1b1_1<" in hbox[1].value

    # test manually_stream_down()
    s.manually_update_stream(1)
    await wait_stream_async(3, s)
