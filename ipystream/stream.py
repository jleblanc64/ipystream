import threading
from typing import Any, Callable

import pandas as pd
import solara
from ipydatagrid import DataGrid
from IPython.core.display import Javascript
from IPython.core.display_functions import clear_output, display, update_display
from ipywidgets import HTML, HBox, IntText
from pydantic import BaseModel

from ipystream.async_debounce import AsyncDebouncer

display_sep = "---------------------------------------------------------"
internal_counter_desc = "#{[34_9azerfcd"
quiet_display_key = "quiet_display"
logs_key = "logs"


def is_internal_counter(widget):
    if not isinstance(widget, IntText):
        return False

    return widget.description == internal_counter_desc


def remove_internal_counter(l):
    return [x for x in l if not is_internal_counter(x)]


def proxy_display(widg, display_id, cache):
    if quiet_display_key in cache:
        log(widg, display_id, cache)
    else:
        display(widg, display_id=display_id)


def proxy_update_display(widg, display_id, cache):
    if quiet_display_key in cache:
        log(widg, display_id, cache)
    else:
        update_display(widg, display_id=display_id)


def log(widg, display_id, cache):
    if logs_key not in cache:
        cache[logs_key] = {}

    cache[logs_key][display_id] = widg


class Handle(BaseModel):
    display_id: str
    cache: dict

    def update(self, widget):
        proxy_update_display(widget, self.display_id, self.cache)


class WidgetCurrentsChildren(BaseModel):
    parents: list[Any]
    currents: list[Any]
    cache: dict
    currents_level: int
    current_idx: int = 0
    vertical: bool

    def remove_counter(self):
        clean_parents = self.parents.copy()
        clean_currents = self.currents.copy()

        if is_internal_counter(clean_parents[-1]):
            clean_parents.pop(-1)

        if is_internal_counter(clean_currents[-1]):
            clean_currents.pop(-1)

        return WidgetCurrentsChildren(
            parents=clean_parents,
            currents=clean_currents,
            cache=self.cache,
            currents_level=self.currents_level,
            current_idx=self.current_idx,
            vertical=self.vertical,
        )

    def display_id(self, index):
        return f"{str(self.currents_level)}_{str(index)}"

    def display_or_update(self, widget) -> Handle:
        id = self.display_id(self.current_idx)
        h = Handle(idx=self.current_idx, w=self, display_id=id, cache=self.cache)

        is_update = self.current_idx < len(self.currents)
        if is_update:
            existing = self.currents[self.current_idx]
            # in this case re use existing, as it is certainly observed (eg. SelectMultiple, RadioButtons)
            if hasattr(existing, "options") and hasattr(existing, "value"):
                opts = widget.options
                value = widget.value

                with existing.hold_trait_notifications():
                    existing.options = opts
                existing.value = value

                self.current_idx = self.current_idx + 1
                return h
            elif hasattr(existing, "value"):
                value = widget.value

                existing.value = value
                self.current_idx = self.current_idx + 1
                return h
            elif self.vertical:
                h.update(widget)

        else:
            self.currents.append(None)

        self.currents[self.current_idx] = widget
        self.current_idx = self.current_idx + 1
        return h

    def sub_title(self, x):
        x = f"<font color='red'>-- {x} --</font>"
        self.display_or_update(HTML(x))


class WidgetUpdater(BaseModel):
    widgets: list[Any]
    updater: Callable[[WidgetCurrentsChildren], None] | None
    vertical: bool
    title: str | None
    split_hbox_after: int | None

    def stream_down(self, parents, currents, currents_level, level_obj, first_display: bool, last_level: bool):
        # disable all observed
        self.disable_loading(level_obj, first_display, last_level)

        with level_obj.lock:
            wca = WidgetCurrentsChildren(
                parents=parents, currents=currents, cache=level_obj.cache, currents_level=currents_level, vertical=self.vertical
            )
            wca_cleaned = wca.remove_counter()
            self.updater(wca_cleaned)

            if first_display:
                missing = len(wca_cleaned.currents) - len(currents) + 1
                for _ in range(missing):
                    currents.insert(len(currents) - 1, None)

                for i, widg in enumerate(wca_cleaned.currents):
                    currents[i] = widg

                if self.title:
                    proxy_display(title_html(self.title), None, wca.cache)

            cache = wca_cleaned.cache
            level_obj.cache = cache

            # update counter
            if is_internal_counter(currents[-1]):
                c = currents[-1]
                c.value = c.value + 1

            if self.vertical:
                for i, w in enumerate(wca_cleaned.currents):
                    id = wca_cleaned.display_id(i)
                    if first_display:
                        proxy_display(w, id, cache)
                    # else:
                    #     proxy_update_display(w, id, cache)
            else:
                self.display_horizontal(currents_level, wca_cleaned, first_display)

            if last_level:
                level_obj.stream_update_done_count = level_obj.stream_update_done_count + 1

    def display_horizontal(self, currents_level, wca_cleaned, first_display):
        cache = wca_cleaned.cache
        id = str(currents_level)
        if self.split_hbox_after and len(wca_cleaned.currents) > self.split_hbox_after:
            box1 = HBox(wca_cleaned.currents[0 : self.split_hbox_after])  # noqa: E203
            box2 = HBox(wca_cleaned.currents[self.split_hbox_after :])  # noqa: E203
            id1 = f"{id}_1"
            id2 = f"{id}_2"

            if first_display:
                proxy_display(box1, id1, cache)
                proxy_display(box2, id2, cache)
            else:
                proxy_update_display(box1, id1, cache)
                proxy_update_display(box2, id2, cache)

        else:
            box = HBox(wca_cleaned.currents)
            if first_display:
                proxy_display(box, id, cache)
            else:
                proxy_update_display(box, id, cache)

    def stream_down_obs(self, parents, currents, debouncer, currents_level, level_obj, last_level):
        @debouncer
        def widget_on_change(change):
            self.stream_down(parents, currents, currents_level, level_obj, False, last_level)

        for widget in parents:
            widget.observe(widget_on_change, names="value")

    def disable_loading(self, level_obj, first_display: bool, last_level: bool):
        if not first_display:
            level_to_widget = level_obj.level_to_widget
            levels = list(level_to_widget.keys())
            levels.sort()
            levels.pop()

            for lvl in levels:
                widgets = level_to_widget[lvl].widgets

                for w in widgets:
                    if hasattr(w, "disabled"):
                        if not last_level:
                            w.disabled = True
                        else:
                            w.disabled = False


def title_html(x):
    x = f"<font size='4' style='font-weight:bold;line-height: 50px'>{x}</font>"
    return HTML(x)

class Stream(BaseModel):
    debounce_sec: float = 1.0
    level_to_widget: dict[int, WidgetUpdater] = {}
    cache: dict = {}
    lock: Any = None
    stream_update_done_count: int = -1
    debouncer: Any = None

    def register(self, level, widgets=None, updater=None, vertical=False, title=None, split_hbox_after=None):
        if not self.level_to_widget:
            self.lock = threading.RLock()
            # check_javascript()

        if not widgets:
            widgets = []

        self.level_to_widget[level] = WidgetUpdater(
            widgets=[f(self) for f in widgets], updater=updater, vertical=vertical, title=title, split_hbox_after=split_hbox_after
        )

    def display_registered(self):
        if not self.debouncer:
            self.debouncer = AsyncDebouncer(self.debounce_sec)

        css = "<style>.widget-radio-box {margin-right: 40px;}</style>"
        display(HTML(css))

        levels = list(self.level_to_widget.keys())
        levels.sort()
        for level_i, level in enumerate(levels):

            wu = self.level_to_widget[level]
            currents = wu.widgets

            # otherwise display happens in wu.stream_down()
            if level_i == 0:
                if wu.title:
                    proxy_display(title_html(wu.title), None, self.cache)
                proxy_display(HBox(remove_internal_counter(currents)), None, self.cache)
            print(display_sep)

            level_below = level + 1
            if level_below not in self.level_to_widget:
                continue

            self.level_to_widget[level].updater = self.level_to_widget[level_below].updater
            self.level_to_widget[level].vertical = self.level_to_widget[level_below].vertical
            self.level_to_widget[level].title = self.level_to_widget[level_below].title
            self.level_to_widget[level].split_hbox_after = self.level_to_widget[level_below].split_hbox_after

            children = self.level_to_widget[level_below].widgets
            int_txt = IntText(value=0, disabled=True, description=internal_counter_desc)
            children.append(int_txt)

            # init
            last_level = level_i == len(levels) - 2
            wu.stream_down(currents, children, level_below, self, True, last_level)

            # update on change
            wu.stream_down_obs(currents, children, self.debouncer, level_below, self, last_level)


def check_javascript():
    grid = DataGrid(pd.DataFrame({"0": [0]}), layout={"height": "10px"})
    display(grid)

    dl = solara.FileDownload("a", filename="a", label="a")
    display(dl)

    js = """
var err = 'Click to show javascript ' + 'error';
var isJsError = document.body.innerHTML.includes(err);

if (isJsError){
    alert('Browser will be refreshed to fully load Jupyter widgets');
    window.location.reload();
}
"""

    display(Javascript(js))
    clear_output()
