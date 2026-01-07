import ipywidgets as widgets
from IPython.display import display, HTML
import time
import threading

# --- 1. Global / Persistent Widgets (The "Setup") ---
spinner_chars = ["|", "/", "-", "\\"]
spinner_html = widgets.HTML(value="", layout=widgets.Layout(display="none"))
out_area = widgets.Output()
stop_spinner = threading.Event()

def count_button():
    btn = widgets.Button(description="Run Task", button_style='info')

    # --- 2. The Spinner Thread Logic ---
    def spinner_thread_func():
        i = 0
        while not stop_spinner.is_set():
            # Mimicking your working HTML style
            spinner_html.value = f"<pre style='display:inline; font-size:16px;'>{spinner_chars[i % len(spinner_chars)]} Processing...</pre>"
            i += 1
            time.sleep(0.1)
        spinner_html.value = "" # Clear when done

    # --- 3. The Main Logic (Mimics create_enymap) ---
    def on_click_action(b):
        # Reset UI state
        out_area.clear_output()
        spinner_html.layout.display = "inline-block"
        stop_spinner.clear()

        # Start spinner thread
        threading.Thread(target=spinner_thread_func, daemon=True).start()

        with out_area:
            try:
                # Mimic your "print" and "display" logic
                print("Starting counter...", flush=True)
                for i in range(1, 6):
                    print(f"Seconds: {i}", flush=True)
                    time.sleep(1)

                display(HTML("<b style='color:green;'>Task Completed Successfully!</b>"))

            except Exception as e:
                display(HTML(f"<span style='color:red;'>Error: {str(e)}</span>"))

            finally:
                # Clean up UI (Mimics your finally block)
                stop_spinner.set()
                spinner_html.layout.display = "none"

    btn.on_click(on_click_action)

    # Return the UI container
    return widgets.VBox([btn, spinner_html, out_area])