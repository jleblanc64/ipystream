import base64

from ipywidgets import widgets
from plotly.io._utils import validate_coerce_fig_to_dict
import plotly.graph_objects as go

def plotly_fig_to_html(fig: go.Figure):
    # compute dimensions
    fig_dict = validate_coerce_fig_to_dict(fig, True)
    iframe_buffer = 20
    layout = fig_dict.get("layout", {})

    if layout.get("width", False):
        width = str(layout["width"] + iframe_buffer) + "px"
    else:
        width = "100%"

    if layout.get("height", False):
        height = layout["height"] + iframe_buffer
    else:
        height = str(525 + iframe_buffer) + "px"

    # build html
    html_content = fig.to_html(full_html=True, include_plotlyjs="cdn")
    encoded_html = base64.b64encode(html_content.encode('utf-8')).decode('ascii')
    src_url = f"data:text/html;base64,{encoded_html}"
    html_string = f'<iframe src="{src_url}" width="{width}" height="{height}" frameborder="0"></iframe>'

    return widgets.HTML(value=html_string)
