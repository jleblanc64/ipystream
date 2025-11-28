from typing import Any
from pydantic import BaseModel
from ipywidgets import HTML
from ipystream.utils import is_internal_counter, proxy_update_display


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
            elif hasattr(existing, "children"):
                existing.children = widget.children

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
