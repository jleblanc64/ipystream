import ipywidgets as widgets
from IPython.display import display, HTML
import time
import threading

# Global Widgets
spinner_chars = ["|", "/", "-", "\\"]
spinner_html = widgets.HTML(value="", layout=widgets.Layout(display="none"))
out_area = widgets.Output()
stop_spinner = threading.Event()

def count_button():
    btn = widgets.Button(description="Run Task", button_style='info')

    def spinner_thread_func():
        i = 0
        while not stop_spinner.is_set():
            spinner_html.value = f"<pre style='display:inline; font-size:16px;'>{spinner_chars[i % len(spinner_chars)]} Processing...</pre>"
            i += 1
            time.sleep(0.1)
        spinner_html.value = ""

    def on_click_action(b):
        # 1. Reset UI
        out_area.clear_output()
        spinner_html.layout.display = "inline-block"
        stop_spinner.clear()

        # 2. Start Spinner
        threading.Thread(target=spinner_thread_func, daemon=True).start()

        # 3. Execution Logic
        def run_logic():
            try:
                # In xpython, append_stdout is much more reliable than 'print' inside a thread
                out_area.append_stdout("Starting counter...\n")

                for i in range(1, 6):
                    out_area.append_stdout(f"Seconds: {i}\n")
                    time.sleep(1)

                # For HTML displays, we still use the 'with' block but locally
                with out_area:
                    display(HTML("<b style='color:green;'>Task Completed Successfully!</b>"))

            except Exception as e:
                with out_area:
                    display(HTML(f"<span style='color:red;'>Error: {str(e)}</span>"))
            finally:
                stop_spinner.set()
                # Use a tiny sleep to ensure the last message is rendered before hiding the spinner
                time.sleep(0.2)
                spinner_html.layout.display = "none"

        # Start the main logic in a separate thread so it doesn't block the UI thread
        threading.Thread(target=run_logic, daemon=True).start()

    btn.on_click(on_click_action)
    return widgets.VBox([btn, spinner_html, out_area])
