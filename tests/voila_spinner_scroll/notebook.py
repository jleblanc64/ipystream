import time
from IPython.core.display_functions import display
from ipywidgets import widgets, HTML
from ipystream.voila.spinned_print_out import get_spinner_html, Spinned


def run():
    # buttons
    button2 = widgets.Button(description="Button 2", layout=widgets.Layout(width="250px"))

    space = HTML("<br/>")
    buttons = [button2]
    for btn in buttons:
        btn.layout.margin = "0 30px 0 0"
    display(space, widgets.HBox(buttons))

    # spinner area display
    vbox = widgets.VBox()
    spinner_html = get_spinner_html()
    display(space, spinner_html, vbox)

    # bind spinner area, functions and buttons
    def f2(out):
        out.print("looping over list")
        for i in range(0, 50):
            out.print(i)
            time.sleep(.05)

    spinned = Spinned(vbox, spinner_html)
    spinned.bind(f2, button2)
