import html
import traceback
from ipywidgets import HTML


def with_stacktrace(callable, out):
    try:
        callable()
    except:
        out.append_display_data(stacktrace_html())


def stacktrace_html():
    tb_str = html.escape(traceback.format_exc())
    return HTML(
        f"<pre class='stacktrace-text' style='"
        f"color:#b31412 !important; font-size:14px !important; "
        f'font-family:"Courier New", Consolas, monospace !important; '
        f"line-height:1.4 !important; background:#fff0f0 !important; "
        f"padding:12px; border-radius:4px; display:block; "
        f"white-space:pre-wrap !important; border:1px solid #ffccd5;'>"
        f"{tb_str}</pre>"
    )
