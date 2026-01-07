import pandas as pd
from ipydatagrid import DataGrid
from IPython.core.display_functions import display
from ipywidgets import RadioButtons, widgets, HTML
from ipystream.stream import Stream
from ipystream.renderer import plotly_fig_to_html
import plotly.graph_objects as go
from ipystream.voila.kernel import find_project_root
from tests.voila.python.documentation_page import open_documentation
from tests.voila.python.popup import popup_button


def run():
    my_html = "<html><body><h1>Hello World</h1><p>Hello world2 !</p></body></html>"
    open_documentation(my_html)
    display(HTML("<br>"))

    popup_btn, popup_dialog = popup_button()
    display(popup_btn)
    display(popup_dialog)
    display(HTML("<br>"))

    ######################################################################
    # excel cars
    excel_path = find_project_root() / "tests" / "voila" / "python" / "cars.xlsx"
    df = pd.read_excel(excel_path)
    cars = df.to_dict(orient="list")
    dicts = df.to_dict(orient="records")
    display(
        DataGrid(
            df,
            auto_fit_columns=True,
            layout={"height": "160px", "width": "auto"},
            selection_mode="cell",
        )
    )

    def couleurs(w):
        w.cache["marque"] = w.parents[0].value
        dicts_filt = [d for d in dicts if d["Marque"] == w.cache["marque"]]
        opts = sorted(list(set([d["Couleur"] for d in dicts_filt])))
        select = widgets.SelectMultiple(
            options=opts, value=opts, layout={"height": "50px"}
        )
        w.display_or_update(select)

    def annees(w):
        dicts_filt = [
            d
            for d in dicts
            if d["Marque"] == w.cache["marque"] and d["Couleur"] in w.parents[0].value
        ]
        annees = [d["Année"] for d in dicts_filt]

        annees_count = {k: 0 for k in annees}
        for a in annees:
            annees_count[a] = annees_count[a] + 1
        annees = sorted(list(set(annees)))
        counts = [annees_count[a] for a in annees]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=annees,
                    values=counts,
                    textinfo="value",
                    hoverinfo="label",
                    domain=dict(x=[0.05, 0.95], y=[0.05, 0.95]),
                )
            ]
        )
        fig.update_layout(width=300, height=250, margin=dict(l=0, r=0, t=0, b=0))
        w.display_or_update(plotly_fig_to_html(fig))

        # datagrid
        df = pd.DataFrame({"annees": annees, "counts": counts})
        grid = DataGrid(
            df,
            selection_mode="cell",
            base_column_size=200,
            base_row_header_size=300,
            layout={"height": "250px"},
        )
        w.display_or_update(widgets.VBox([grid]))

    s = Stream()
    wi = RadioButtons(options=sorted(list(set(cars["Marque"]))))
    s.register(1, [lambda x: wi], title="Marque")
    s.register(2, updater=couleurs, title="Couleur (to select multiple, hold CTRL)")
    s.register(3, updater=annees, title="Années", vertical=True)
    s.display_registered()
