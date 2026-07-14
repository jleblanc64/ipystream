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


# --- Dynamic scroll-height CSS, keyed by max_lines ---
# 12px font-size * 1.6 line-height (matches the console's <pre> rendering)
_SCROLL_LINE_HEIGHT_PX = 19.2
# matches custom-code-container's 20px top + 20px bottom padding
_SCROLL_PADDING_PX = 40
_INJECTED_SCROLL_CLASSES = set()
_AUTOSCROLL_INJECTED = False


def _scroll_class_for(max_lines: int) -> str:
    return f"scrolled-lines-{max_lines}"


def _ensure_scroll_style(max_lines: int) -> str:
    """Injects (once per distinct max_lines value) a CSS rule that caps the
    console's height to roughly `max_lines` lines and turns on a scrollbar.
    Uses `display: block` (overriding VBox's default flex layout) so extra
    children overflow and scroll instead of flex-shrinking to invisible."""
    css_class = _scroll_class_for(max_lines)
    if css_class not in _INJECTED_SCROLL_CLASSES:
        height_px = int(round(_SCROLL_PADDING_PX + max_lines * _SCROLL_LINE_HEIGHT_PX))
        display(
            HTML(
                f"""
            <style>
            .custom-code-container.{css_class} {{
                display: block !important;
                max-height: {height_px}px !important;
                overflow-y: auto !important;
            }}
            .custom-code-container.{css_class} > * {{
                flex-shrink: 0 !important;
            }}
            </style>
        """
            )
        )
        _INJECTED_SCROLL_CLASSES.add(css_class)
    return css_class


def _ensure_autoscroll_script():
    """Injects (once per kernel) a small "sticky bottom" auto-scroller for
    any scrollable console container (`.custom-code-container` with a
    `scrolled-lines-*` class). New output auto-scrolls the container to
    the bottom, unless the user has manually scrolled up to read earlier
    lines — in which case it backs off until they scroll back down near
    the bottom, or a new run clears the container's content."""
    global _AUTOSCROLL_INJECTED
    if _AUTOSCROLL_INJECTED:
        return

    display(
        HTML(
            """
        <script>
        (function(){
            if (window.__consoleAutoScrollInit) return;
            window.__consoleAutoScrollInit = true;

            var NEAR_BOTTOM_PX = 40;
            var CONTAINER_SELECTOR = '.custom-code-container[class*="scrolled-lines-"]';

            function isNearBottom(el){
                return (el.scrollHeight - el.scrollTop - el.clientHeight) < NEAR_BOTTOM_PX;
            }

            // Track whether the user has manually scrolled away from the
            // bottom, so we don't yank them back down mid-read. Delegated
            // on document with capture:true since 'scroll' doesn't bubble.
            document.addEventListener('scroll', function(evt){
                var el = evt.target;
                if (!el || !el.classList || !el.classList.contains('custom-code-container')) return;
                el.dataset.userScrolledAway = isNearBottom(el) ? '' : '1';
            }, true);

            function followBottom(){
                document.querySelectorAll(CONTAINER_SELECTOR).forEach(function(el){
                    // Not overflowing yet (e.g. just cleared for a new run) —
                    // reset the "scrolled away" flag so the new run starts
                    // following the bottom again.
                    if (el.scrollHeight <= el.clientHeight + 1){
                        el.dataset.userScrolledAway = '';
                        return;
                    }
                    if (el.dataset.userScrolledAway === '1') return;
                    el.scrollTop = el.scrollHeight;
                });
            }

            var observer = new MutationObserver(function(){
                requestAnimationFrame(followBottom);
            });
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                characterData: true
            });
        })();
        </script>
        """
        )
    )
    _AUTOSCROLL_INJECTED = True


# --- 4. LiveOutput ---
class LiveOutput:
    """
    Passed to fun(out) exactly like the old widgets.Output.
    append_display_data() routes HTML fragments into a stable
    widgets.HTML node (in-place update, scroll-stable) and proper
    Jupyter widgets directly as VBox children.
    The VBox itself carries the custom-code-container class so all
    children sit inside one unified styled block. If `max_lines` is set,
    the container also gets a matching scroll class, capping its height
    to roughly that many lines and adding a scrollbar instead of growing
    indefinitely.
    """

    def __init__(self, vbox: widgets.VBox, lock: threading.Lock, max_lines: int = None):
        self._vbox = vbox
        self._lock = lock
        self._buf = []
        self._html_w = widgets.HTML()
        self._vbox.add_class("custom-code-container")
        if max_lines is not None:
            self._vbox.add_class(_scroll_class_for(max_lines))

    def _commit(self):
        self._html_w.value = "".join(self._buf) if self._buf else ""

    def _ensure_html_in_vbox(self):
        if not self._vbox.children or self._vbox.children[-1] is not self._html_w:
            self._vbox.children = self._vbox.children + (self._html_w,)

    def _flush_text(self, text: str, color: str = "#212529"):
        safe = _linkify(_html.escape(text))
        self._buf.append(f'<pre style="font-size:12px;margin-block:0;line-height:1.6;color:{color}">{safe}</pre>')
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
            self._buf.append(f'<pre style="font-size:12px;margin-block:0;line-height:1.6">{safe}</pre>')
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
    def __init__(self, vbox: widgets.VBox, spinner_html, max_lines: int = None):
        self.vbox = vbox
        self.spinner_html = spinner_html
        self.max_lines = max_lines
        self.all_buttons = []
        if max_lines is not None:
            # Inject the scroll CSS now, during normal script/app setup.
            # display() calls made later from inside a button click handler
            # aren't reliably routed into the page in Voila, so this can't
            # be deferred to LiveOutput's per-run construction.
            _ensure_scroll_style(max_lines)
            _ensure_autoscroll_script()

    def bind(self, fun, btn):
        self.all_buttons.append(btn)
        is_running = False

        def on_click_action(b):
            nonlocal is_running
            if is_running:
                return

            is_running = True

            self.vbox.children = ()
            self.vbox.remove_class("custom-code-container")
            if self.max_lines is not None:
                self.vbox.remove_class(_scroll_class_for(self.max_lines))

            for button in self.all_buttons:
                button.disabled = True

            start_time = time.time()
            lock = threading.Lock()
            out = LiveOutput(self.vbox, lock, max_lines=self.max_lines)

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
