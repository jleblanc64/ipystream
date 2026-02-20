def get_logo_html(_LOGO_B64):
    return (
        f"<img id='voila-logo' src='data:image/png;base64,{_LOGO_B64}' "
        "style='position:absolute;top:16px;right:20px;height:80px;z-index:10000;"
        "pointer-events:none;"
        "border:4px solid #333;"
        "border-radius:8px;"
        "padding:6px;"
        "background:white;"
        "box-shadow:0 2px 8px rgba(0,0,0,0.15);' />"
    )