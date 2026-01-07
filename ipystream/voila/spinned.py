import ipywidgets as widgets
from IPython.display import display, HTML
import time
import threading

def get(fun, btn, out):
    spinner_chars = ["|", "/", "-", "\\"]
    spinner_html = widgets.HTML(value="", layout=widgets.Layout(display="none"))
    stop_spinner = threading.Event()

    def spinner_thread_func():
        i = 0
        while not stop_spinner.is_set():
            spinner_html.value = f"<pre style='display:inline; font-size:16px;'>{spinner_chars[i % len(spinner_chars)]} Processing...</pre>"
            i += 1
            time.sleep(0.1)
        spinner_html.value = ""

    def on_click_action(b):
        out.outputs = ()
        # 1. Reset UI
        spinner_html.layout.display = "inline-block"
        stop_spinner.clear()

        # 2. Start Spinner
        threading.Thread(target=spinner_thread_func, daemon=True).start()

        # 3. Execution Logic
        def run_logic():
            try:
                fun(out)
            except Exception as e:
                with out:
                    display(HTML(f"<span style='color:red;'>Error: {str(e)}</span>"))
            finally:
                stop_spinner.set()
                # Use a tiny sleep to ensure the last message is rendered before hiding the spinner
                time.sleep(0.2)
                spinner_html.layout.display = "none"

        # Start the main logic in a separate thread so it doesn't block the UI thread
        threading.Thread(target=run_logic, daemon=True).start()

    btn.on_click(on_click_action)
    return spinner_html
