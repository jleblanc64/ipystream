import ipywidgets as widgets
from IPython.display import display, HTML
import time
from ipystream.voila.spinned import get

def count_button():
    def fun(out):
        out.append_stdout("Starting counter...\n")

        for i in range(1, 3):
            out.append_stdout(f"Seconds: {i}\n")
            time.sleep(1)

        # For HTML displays, we still use the 'with' block but locally
        with out:
            display(HTML("<b style='color:green;'>Task Completed Successfully!</b>"))

    btn = widgets.Button(description="Run Task", button_style='info')
    out = widgets.Output()
    spinner_html = get(fun, btn, out)
    return widgets.VBox([btn, spinner_html, out])
