import ipywidgets as widgets
from IPython.display import display, HTML
import time
import threading


def get(fun, btn, out):
    spinner_chars = ["|", "/", "-", "\\"]
    spinner_html = widgets.HTML(value="", layout=widgets.Layout(display="none"))
    stop_spinner = threading.Event()
    is_running = False  # The Guard

    def spinner_thread_func():
        i = 0
        while not stop_spinner.is_set():
            spinner_html.value = f"<pre style='display:inline; font-size:16px;'>{spinner_chars[i % len(spinner_chars)]} Processing...</pre>"
            i += 1
            time.sleep(0.1)
        spinner_html.value = ""

    def on_click_action(b):
        nonlocal is_running
        if is_running: return # Exit if already active

        is_running = True
        b.disabled = True
        out.outputs = ()
        spinner_html.layout.display = "inline-block"
        stop_spinner.clear()

        threading.Thread(target=spinner_thread_func, daemon=True).start()

        def run_logic():
            nonlocal is_running
            try:
                fun(out)
            except Exception as e:
                with out:
                    display(HTML(f"<span style='color:red;'>Error: {str(e)}</span>"))
            finally:
                stop_spinner.set()
                time.sleep(0.2)
                spinner_html.layout.display = "none"
                b.disabled = False
                is_running = False # Release the Guard

        threading.Thread(target=run_logic, daemon=True).start()

    btn.on_click(on_click_action)
    return spinner_html
