import base64
from ipywidgets import widgets


def documentation_btn(html_content, button_text="Documentation"):
    # Base64 encode the HTML content for safe embedding
    b64_html = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")

    # Wrap button in a span to control alignment
    js_code = f"""
        <span style="display: inline-block !important; vertical-align: top !important; margin-top: -2px !important;">
            <button onclick="
                var b64 = '{b64_html}';
                var html = atob(b64);
                var newWin = window.open('about:blank', '_blank');
                if (newWin) {{
                    newWin.document.open();
                    newWin.document.write(html);
                    newWin.document.close();
                }} else {{
                    alert('Pop-up blocked!');
                }}
            " class="jupyter-button button-blue" style="
                background-color: #673AB7 !important;
                color: white !important;">
                {button_text}
            </button>
        </span>
    """
    return widgets.HTML(js_code)
