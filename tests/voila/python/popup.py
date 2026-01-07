import ipyvuetify as v
from ipywidgets import HTML, Button


def popup_button():
    current_color = {"value": "blue"}
    # 1. The "Hello" Text Widget
    hello_html = HTML(
        "<h2 style='text-align:center; margin-top:20px; color:blue'>Hello</h2>"
    )

    # 2. Toggle Color Button
    toggle_btn = v.Btn(children=["Toggle Color"], color="success", class_="ma-2")

    def on_toggle_click(widget, event, data):
        # Logic to switch colors
        if current_color["value"] == "blue":
            current_color["value"] = "red"
        else:
            current_color["value"] = "blue"

        # Update the HTML content
        hello_html.value = f"<h2 style='text-align:center; margin-top:20px; color:{current_color['value']}'>Hello</h2>"

    toggle_btn.on_event("click", on_toggle_click)

    # 3. Close Buttons
    close_icon_btn = v.Btn(
        icon=True, color="red", children=[v.Icon(children=["mdi-close"])]
    )
    close_text_btn = v.Btn(children=["Close"], color="red", text=True)

    # 4. Define the Dialog
    popup_dialog = v.Dialog(
        v_model=False,
        width="350",
        children=[
            v.Card(
                children=[
                    v.CardTitle(
                        class_="headline grey lighten-2",
                        children=["Message Settings", v.Spacer(), close_icon_btn],
                    ),
                    v.CardText(
                        children=[
                            hello_html,
                            v.Layout(justify_center=True, children=[toggle_btn]),
                        ]
                    ),
                    v.CardActions(children=[v.Spacer(), close_text_btn]),
                ]
            )
        ],
    )

    # --- Event Handlers for Closing ---
    def close_popup(widget, event, data):
        popup_dialog.v_model = False

    close_icon_btn.on_event("click", close_popup)
    close_text_btn.on_event("click", close_popup)

    # Trigger Button
    open_btn = Button(description="Open Popup", button_style="info")
    open_btn.on_click(lambda b: setattr(popup_dialog, "v_model", True))
    return open_btn, popup_dialog
