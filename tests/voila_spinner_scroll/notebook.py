import time
from IPython.core.display_functions import display
from ipywidgets import widgets
from ipystream.voila.spinned_print_out import get_spinner_html, Spinned


def run():
    button = widgets.Button(description="Button", layout=widgets.Layout(width="250px"))
    display(button)

    # spinner area display
    vbox = widgets.VBox()
    spinner_html = get_spinner_html()
    display(spinner_html, vbox)

    # bind spinner area, functions and button
    def f(out):
        for i in range(0, 200):
            out.print(i)
            time.sleep(0.1)

    # Spinned(vbox, spinner_html, max_lines=15).bind(f, button)
    Spinned(vbox, spinner_html, max_lines=5).bind(f, button)
    # Spinned(vbox, spinner_html).bind(f, button)
