from IPython.display import display, HTML

def display_voila_watchdog(timeout_ms=6000):
    watchdog_html = f"""
    <style>

    /* Prevent scrollbars when the watchdog is active */
    body.watchdog-active {{
        overflow: hidden !important;
    }}

    /* The Error Overlay Container */
    #connection-watchdog {{
        display: none; /* Controlled by JS */
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: #f8f9fa;
        z-index: 999999;
        
        /* Centering */
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    .watchdog-card {{
        background: white;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
        max-width: 420px;
        margin: 20px;
    }}

    .watchdog-card h1 {{
        color: #dc3545;
        margin: 0 0 15px 0;
        font-size: 24px;
        font-weight: 600;
    }}

    .watchdog-card p {{
        color: #495057;
        margin-bottom: 25px;
        line-height: 1.6;
        font-size: 16px;
    }}

    .reload-btn {{
        padding: 12px 30px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 6px;
        transition: background 0.2s, transform 0.1s;
    }}

    .reload-btn:hover {{
        background-color: #0069d9;
    }}
    
    .reload-btn:active {{
        transform: scale(0.98);
    }}
    </style>

    <div id="connection-watchdog">
        <div class="watchdog-card">
            <h1>Connection Timeout</h1>
            <p>The application interface is taking too long to load. This usually happens on slow internet connections.</p>
            <button class="reload-btn" onclick="location.reload()">Reload Page</button>
        </div>
    </div>

    <script>
    (function() {{
        const timeout = {timeout_ms};

        function checkWidgetInitialization() {{
            const widgets = document.querySelectorAll('.jupyter-widgets');
            
            if (widgets.length === 0) {{
                // FAILURE: Show overlay and kill scrollbars
                const overlay = document.getElementById('connection-watchdog');
                overlay.style.display = 'flex';
                document.body.classList.add('watchdog-active');
                
                // Hide raw output text
                document.querySelectorAll('.jp-OutputArea-output pre').forEach(el => {{
                    el.style.display = 'none';
                }});
            }} else {{
                // SUCCESS: Reveal content
                document.body.classList.remove('watchdog-active');
                document.querySelectorAll('.jp-OutputArea-output pre').forEach(el => {{
                    el.style.opacity = '1';
                }});
            }}
        }}

        setTimeout(checkWidgetInitialization, timeout);
    }})();
    </script>
    """
    display(HTML(watchdog_html))