import requests as r
from IPython.core.display_functions import display
from ipywidgets import widgets, HTML
from ipystream.voila import spinned_print_out
from ipystream.voila.spinned_print_out import get_spinner_html
from tests.voila_api_explorer.python.utils import load_creds


def run():
    u, p = load_creds("/home/charles/Desktop/SEP.properties")
    url = "https://eu-north-1-api.dev.sympheny.com/backoffice/auth/ext/token"
    data = {"email": u, "password": p}
    headers = {"content-type": "application/json"}

    resp = r.post(url, headers=headers, json=data)
    jwt = resp.json()["access_token"]
    h = {"authorization": f"Bearer {jwt}", "content-type": "application/json"}

    # list projects
    be = "https://eu-north-1-api.dev.sympheny.com/sympheny-app/"
    projects = r.get(f"{be}projects", headers=h).json()["data"]["projects"]
    projects = [(x["projectName"], x["projectGuid"]) for x in projects]
    projects.sort(key=lambda x: x[0])

    dropdown_solars = widgets.Dropdown(description='Projects:', layout=widgets.Layout(width='450px', height='35px', margin='5px 40px 0 0'))
    dropdown_solars.options = projects
    dropdown_solars.value = projects[0][1]
    display(dropdown_solars)

    # spinner
    vbox = widgets.VBox()
    spinner_html = get_spinner_html()

    button_create = widgets.Button(description="1) List scenarios in Project", layout=widgets.Layout(width="250px"))
    button2 = widgets.Button(description="2) Button 2", layout=widgets.Layout(width="250px"))

    buttons = [button_create, button2]
    for btn in buttons:
        btn.layout.margin = '0 30px 0 0'

    def f(out):
        project_id = dropdown_solars.value
        project_name = [x[0] for x in projects if x[1] == project_id][0]
        out.append_display_data(f"Selected project: {project_name}")
        out.append_display_data(project_id)
        out.append_display_data(dropdown_solars.options)
        analyses = r.get(f"{be}projects/{project_id}", headers=h).json()["data"]["analyses"]
        analyses = [x["analysisGuid"] for x in analyses]


        scenarios = [x for y in analyses for x in r.get(f"{be}analysis/{y}", headers=h).json()["data"]["scenarios"]]
        out.append_display_data(scenarios)

    def f2(out):
        out.append_display_data("hello world")


    spinned_print_out.get(f, button_create, vbox, spinner_html, buttons)
    spinned_print_out.get(f2, button2, vbox, spinner_html, buttons)
    space = HTML("<br/>")
    display(space, widgets.HBox(buttons))
    display(space, spinner_html, vbox)

