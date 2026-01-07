from ipywidgets import widgets


def documentation_btn(html_content, button_text="Documentation"):
    # Escape backticks and double quotes for the JS string
    safe_html = html_content.replace('\\', '\\\\').replace('`', '\\`').replace('"', '\\"')

    # Inline the entire logic into the onclick attribute
    js_code = f"""
        <button onclick="
            var newWin = window.open('about:blank', '_blank');
            if (newWin) {{
                newWin.document.open();
                newWin.document.write(`{safe_html}`);
                newWin.document.close();
            }} else {{
                alert('Pop-up blocked!');
            }}
        " style="
            background-color: #673AB7; color: white; padding: 10px 20px; 
            border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
            {button_text}
        </button>
    """
    return widgets.HTML(js_code)