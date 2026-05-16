import time

import pandas as pd
from ipydatagrid import DataGrid
from IPython.core.display_functions import display
from ipywidgets import RadioButtons, widgets, HTML
from ipystream.stream import Stream
from ipystream.renderer import plotly_fig_to_html
import plotly.graph_objects as go

from ipystream.voila import spinned_print_out
from ipystream.voila.documentation import documentation_btn
from ipystream.voila.kernel import find_project_root
from ipystream.voila.spinned_print_out import get_spinner_html
from tests.voila.python.popup import popup_button
from tests.voila.python.spinner_count import count_button
from tests.voila_api_explorer.python.utils import load_creds


def run():
    print("hello")
    creds = load_creds("/home/charles/Desktop/SEP.properties")
    print(creds)

    dropdown_solars = widgets.Dropdown(description='Solar tech:', layout=widgets.Layout(width='450px', height='35px', margin='5px 40px 0 0'))
    options = []
    options.append(("a", "b"))
    options.append(("a2", "b2"))
    dropdown_solars.options = options
    dropdown_solars.value = options[0][1]
    display(dropdown_solars)

    # spinner
    vbox = widgets.VBox()
    spinner_html = get_spinner_html()

    button_create = widgets.Button(description="A", icon="play", layout=widgets.Layout(width="250px"))
    button_create.add_class("button-green")

    buttons = [button_create]
    for btn in buttons:
        btn.layout.margin = '0 30px 0 0'

    def f(out):
        out.append_display_data("a")
        time.sleep(4)
        out.append_display_data("b")

    spinned_print_out.get(f, button_create, vbox, spinner_html, buttons)
    display(widgets.HBox(buttons))

    space = HTML("<br/>")
    display(space, spinner_html, vbox)


