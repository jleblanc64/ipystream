import re
import threading
import time
import traceback
import html as _html
import ipywidgets as widgets
from IPython.display import HTML, display

# --- 1. Professional Slate-Gray Console CSS ---
CODE_BLOCK_STYLE = """
<style>
    .custom-code-container {
        background-color: #f8f9fa !important; 
        border: 1px solid #e9ecef;
        border-left: 4px solid #adb5bd; 
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace !important;
        padding: 20px;
        border-radius: 8px;
        margin-top: 15px;
        line-height: 1.5;
        overflow-y: visible !important; 
        max-height: none !important; 
        height: auto !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
    }

    .custom-code-container .jupyter-widgets-output-area pre {
        font-size: 12px !important;
        margin: 0;
        white-space: pre-wrap;
        color: #212529 !important;
    }

    .console-error-wrapper {
        margin-top: 15px;
        border-top: 2px solid #ffcfd2;
        padding-top: 10px;
    }

    .stacktrace-text {
        color: #b31412 !important;
        font-size: 11px !important;
        line-height: 1.4 !important;
        background: #fff0f0 !important;
        padding: 12px;
        border-radius: 4px;
        display: block;
        white-space: pre-wrap !important;
        border: 1px solid #ffccd5;
    }
</style>
"""
display(HTML(CODE_BLOCK_STYLE))

# --- 2. Spinner Template ---
spinner_template = """
    <style>
    .loader {{ 
        border: 4px solid #f3f3f3; 
        border-top: 4px solid #ff4d4d;
        border-radius: 50%; 
        width: 30px;
        height: 30px;
        animation: spin 1s linear infinite; 
        display: inline-block;
        vertical-align: middle; 
    }}
    @keyframes spin {{ 
        0% {{ transform: rotate(0deg); }} 
        100% {{ transform: rotate(360deg); }} 
    }}
    .spinner-text {{ 
        font-size: 18px;
        margin-left: 12px; 
        vertical-align: middle; 
        font-family: sans-serif; 
        color: #b91c1c !important;
        font-weight: bold;
    }}
    .spinner-time {{ 
        color: #ff4d4d; 
        font-weight: 900; 
    }}
    </style>
    <div style="margin: 15px 0;">
        <div class="loader" style="display:{vis};"></div>
        <span class="spinner-text">{label} <span class="spinner-time">{t_str}</span></span>
    </div>
    """


# --- 3. Helper Functions ---
def get_spinner_html():
    return widgets.HTML(value=spinner_template.format(vis="none", label="", t_str=""))


def compute_elapsed(start_time):
    elapsed = int(time.time() - start_time)
    m, s = divmod(elapsed, 60)
    return f"{m:02d}:{s:02d}"


_URL_RE = re.compile(r"(https?://\S+)")


def _linkify(text: str) -> str:
    return _URL_RE.sub(
        r'<a href="\1" target="_blank" style="color:#0d6efd;text-decoration:underline">\1</a>',
        text,
    )


# --- 4. LiveOutput ---
class LiveOutput:
    """
    Passed to fun(out) exactly like the old widgets.Output.
    append_display_data() routes HTML fragments into a stable
    widgets.HTML node (in-place update, scroll-stable) and proper
    Jupyter widgets directly as VBox children.
    The VBox itself carries the custom-code-container class so all
    children sit inside one unified styled block.
    """

    def __init__(self, vbox: widgets.VBox, lock: threading.Lock):
        self._vbox = vbox
        self._lock = lock
        self._buf = []
        self._html_w = widgets.HTML()
        self._vbox.add_class("custom-code-container")

    def _commit(self):
        self._html_w.value = "".join(self._buf) if self._buf else ""

    def _ensure_html_in_vbox(self):
        if not self._vbox.children or self._vbox.children[-1] is not self._html_w:
            self._vbox.children = self._vbox.children + (self._html_w,)

    def _flush_text(self, text: str, color: str = "#212529"):
        safe = _linkify(_html.escape(text))
        self._buf.append(
            f'<pre style="font-size:12px;margin-block:0;line-height:1.6;color:{color}">{safe}</pre>'
        )
        self._ensure_html_in_vbox()
        self._commit()

    def append_stdout(self, text: str):
        with self._lock:
            self._flush_text(text)

    def append_stderr(self, text: str):
        with self._lock:
            self._flush_text(text, color="#b31412")

    def append_display_data(self, obj):
        with self._lock:
            if isinstance(obj, widgets.Widget):
                self._commit()
                self._buf = []
                self._html_w = widgets.HTML()
                self._vbox.children = self._vbox.children + (obj,)
                return

            if isinstance(obj, HTML):
                self._buf.append(obj.data)
                self._ensure_html_in_vbox()
                self._commit()
                return

            if hasattr(obj, "_repr_html_"):
                html_str = obj._repr_html_() or ""
                self._buf.append(html_str)
                self._ensure_html_in_vbox()
                self._commit()
                return

            safe = _linkify(_html.escape(repr(obj)))
            self._buf.append(
                f'<pre style="font-size:12px;margin-block:0;line-height:1.6">{safe}</pre>'
            )
            self._ensure_html_in_vbox()
            self._commit()

    def new_inplace_node(self) -> widgets.HTML:
        """Each tqdm_out call gets its own fresh HTML node at the current position."""
        with self._lock:
            node = widgets.HTML()
            self._commit()
            self._buf = []
            self._html_w = widgets.HTML()
            self._vbox.children = self._vbox.children + (node,)
            return node

    def print(self, obj):
        if isinstance(obj, str):
            self.append_stdout(f"{obj}\n")
        else:
            self.append_display_data(obj)


# --- 5. Spinned Instance ---
class Spinned:
    def __init__(self, vbox: widgets.VBox, spinner_html):
        self.vbox = vbox
        self.spinner_html = spinner_html
        self.all_buttons = []

    def get(self, fun, btn):
        self.all_buttons.append(btn)
        is_running = False

        def on_click_action(b):
            nonlocal is_running
            if is_running:
                return

            is_running = True

            self.vbox.children = ()
            self.vbox.remove_class("custom-code-container")

            for button in self.all_buttons:
                button.disabled = True

            start_time = time.time()
            lock = threading.Lock()
            out = LiveOutput(self.vbox, lock)

            def update_timer():
                while is_running:
                    self.spinner_html.value = spinner_template.format(
                        vis="inline-block",
                        label="Running:",
                        t_str=compute_elapsed(start_time),
                    )
                    time.sleep(1)

            def run_logic():
                nonlocal is_running
                try:
                    fun(out)
                except Exception:
                    stack_trace = traceback.format_exc()
                    error_html = f"""
                    <div class="console-error-wrapper">
                        <pre class="stacktrace-text">{stack_trace}</pre>
                    </div>
                    """
                    out.append_display_data(HTML(error_html))
                finally:
                    self.spinner_html.value = spinner_template.format(
                        vis="none",
                        label="Finished in",
                        t_str=compute_elapsed(start_time),
                    )
                    for button in self.all_buttons:
                        button.disabled = False
                    is_running = False

            threading.Thread(target=update_timer, daemon=True).start()
            threading.Thread(target=run_logic, daemon=True).start()

        btn.on_click(on_click_action)
