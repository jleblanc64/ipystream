def get_logo_html(_LOGO_B64):
    return (
        # 1. Create the logo hidden so it doesn't 'flash' in the wrong spot
        f"<div id='voila-logo-wrapper' style='display:none;'>"
        f"  <img id='voila-logo' src='data:image/png;base64,{_LOGO_B64}' "
        "    style='position:absolute; top:16px; right:20px; height:80px; z-index:10000; "
        "    pointer-events:none; border:4px solid #333; border-radius:8px; "
        "    padding:6px; background:white; box-shadow:0 2px 8px rgba(0,0,0,0.15);' />"
        "</div>"

        # 2. Use Javascript to relocate it to the specific scrolling div from your source
        "<script>"
        "(function() {"
        "    var tryMove = setInterval(function() {"
        "        /* Target the specific ID found in your source code */"
        "        var scrollContainer = document.getElementById('rendered_cells');"
        "        var logo = document.getElementById('voila-logo-wrapper');"
        "        "
        "        if (scrollContainer && logo) {"
        "            /* Ensure the container is the 'anchor' for the absolute logo */"
        "            scrollContainer.style.position = 'relative';"
        "            /* Prepend puts it at the very top of the scrollable content */"
        "            scrollContainer.prepend(logo);"
        "            logo.style.display = 'block';"
        "            clearInterval(tryMove);"
        "        }"
        "    }, 100);" # Check every 100ms
        "})();"
        "</script>"
    )