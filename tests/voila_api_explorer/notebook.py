import time
import requests as r
from IPython.core.display_functions import display
from ipydatagrid import DataGrid
from ipywidgets import widgets, HTML
from jproperties import Properties
from ipystream.voila.spinned_print_out import get_spinner_html, Spinned
from ipystream.voila.utils_tdqm import tqdm_out
import pandas as pd


def run():
    # get header
    u, p = load_creds("/home/charles/Desktop/SEP.properties")
    url = "https://eu-north-1-api.dev.sympheny.com/backoffice/auth/ext/token"
    jwt = r.post(url, json={"email": u, "password": p}).json()["access_token"]
    h = {"authorization": f"Bearer {jwt}", "content-type": "application/json"}

    # list projects
    be = "https://eu-north-1-api.dev.sympheny.com/sympheny-app/"
    projects = r.get(f"{be}projects", headers=h).json()["data"]["projects"]
    projects = [(x["projectName"], x["projectGuid"]) for x in projects]
    projects.sort(key=lambda x: x[0])

    # fill dropdown with projects
    dropdown_solars = widgets.Dropdown(
        description="Projects:",
        layout=widgets.Layout(width="450px", height="35px", margin="5px 40px 0 0"),
    )
    dropdown_solars.options = projects
    dropdown_solars.value = projects[0][1]
    display(dropdown_solars)

    # buttons
    button_create = widgets.Button(description="1) List scenarios in Project", layout=widgets.Layout(width="250px"))
    button2 = widgets.Button(description="2) Button 2", layout=widgets.Layout(width="250px"))

    space = HTML("<br/>")
    buttons = [button_create, button2]
    for btn in buttons:
        btn.layout.margin = "0 30px 0 0"
    display(space, widgets.HBox(buttons))

    # spinner area display
    vbox = widgets.VBox()
    spinner_html = get_spinner_html()
    display(space, spinner_html, vbox)

    # bind spinner area, functions and buttons
    def f(out):
        project_id = dropdown_solars.value
        project_name = [x[0] for x in projects if x[1] == project_id][0]
        out.print(f"Selected project: {project_name}")

        analyses = r.get(f"{be}projects/{project_id}", headers=h).json()["data"]["analyses"]
        analyses = [x["analysisGuid"] for x in analyses]
        scenarios = [x for y in analyses for x in r.get(f"{be}analysis/{y}", headers=h).json()["data"]["scenarios"]]

        df = pd.DataFrame(scenarios)
        datagrid = DataGrid(df, selection_mode="row", layout={"height": "180px"})
        datagrid.auto_fit_columns = True
        out.print(datagrid)

    def f2(out):
        out.print("looping over list")
        for i in tqdm_out(range(0, 10), out):
            # simulate work within loop
            time.sleep(0.5)

    spinned = Spinned(vbox, spinner_html)
    spinned.bind(f, button_create)
    spinned.bind(f2, button2)


def load_creds(path: str) -> tuple[str, str]:
    props = Properties()
    with open(path, "rb") as f:
        props.load(f)

    username = props.get("username").data
    password = props.get("password").data
    return username, password
