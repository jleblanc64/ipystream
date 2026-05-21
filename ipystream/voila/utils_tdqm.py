import html as _html
import ipywidgets as widgets
from tqdm import tqdm


class WidgetWriter:
    def __init__(self, node: widgets.HTML):
        self.node = node
        self._current_line = ""

    def write(self, s):
        parts = s.split("\r")
        text = parts[-1].strip("\n")
        if text:
            self._current_line = text
        safe = _html.escape(self._current_line)
        self.node.value = (
            f'<pre style="font-size:12px;margin:0;white-space:pre">{safe}</pre>'
        )

    def flush(self):
        pass


def tqdm_out(iterable, target_widget, desc="", **kwargs):
    """
    iterable      : The range or list to loop over.
    target_widget : LiveOutput instance (has .new_inplace_node()),
                    or plain widgets.Output() in tests.
    """
    if not hasattr(iterable, "__len__"):
        iterable = list(iterable)

    node = (
        target_widget.new_inplace_node()
        if hasattr(target_widget, "new_inplace_node")
        else target_widget.append_stdout
    )
    settings = {
        "file": WidgetWriter(node),
        "ncols": 80,
        "ascii": " #",
        "bar_format": "{desc}: {percentage:3.0f}%|{bar}| [ETA: {remaining}]",
        "desc": desc,
    }

    settings.update(kwargs)

    return tqdm(iterable, **settings)
