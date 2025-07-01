from typing import Callable

import pytest
from ipywidgets import HTML, RadioButtons
from ipystream.stream import Stream, WidgetCurrentsChildren
from tests.utils import wait_stream_async


def drop(v):
    return RadioButtons(options=[v])


def drop_l(l):
    return RadioButtons(options=l)


tree = {"a": [["a1"]], "c": [["a2", "d2"]]}


def updaterI(lvl) -> Callable[[WidgetCurrentsChildren], None]:
    def updater(w: WidgetCurrentsChildren):
        if "lvl" not in w.cache:
            w.cache["lvl"] = []
        w.cache["lvl"].append(lvl)

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
                    html = f"<div style='border-style: solid;padding: 10px;'>{str(w.cache['lvl'])}</>"
                    w.display_or_update(HTML(html))

    return updater


cache = {
    "quiet_display": True,
}

@pytest.mark.asyncio
async def test():
    s = Stream(cache=cache, debounce_sec=0.2)
    widget1 = drop_l(["a", "c"])
    s.register(1, [lambda x: widget1], title="a")
    s.register(2, [lambda x: drop("c")], updaterI(1), title="b")
    s.register(3, [lambda x: drop("f"), lambda x: HTML("f2")], updaterI(2), title="c", vertical=True)

    s.display_registered()

    #
    radio = s.cache["logs"]["3_0"]
    html = s.cache["logs"]["3_1"]
    assert radio.value == "a1_0"
    assert "[1, 2]" in html.value

    widget1.value = "c"
    await wait_stream_async(1, s)
    assert len(s.cache["lvl"]) == 4

    radio = s.cache["logs"]["3_0"]
    html = s.cache["logs"]["3_1"]
    assert radio.value == "a2_0"
    assert "[1, 2, 1, 2]" in html.value

    #
    widget1.value = "a"
    await wait_stream_async(2, s)
    assert len(s.cache["lvl"]) == 6

    radio = s.cache["logs"]["3_0"]
    html = s.cache["logs"]["3_1"]
    assert radio.value == "a1_0"
    assert "[1, 2, 1, 2, 1, 2]" in html.value
