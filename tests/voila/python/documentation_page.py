from IPython.core.display import HTML

def open_documentation(html_content, button_text="Documentation"):
    # Escape backticks for the JavaScript template literal
    safe_html = html_content.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')

    js_code = f"""
        <button onclick="openInBlank()" style="
            background-color: #673AB7; color: white; padding: 10px 20px; 
            border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
            {button_text}
        </button>
    
        <script>
        function openInBlank() {{
            // 1. Open a new window/tab
            var newWin = window.open('about:blank', '_blank');
            
            if (newWin) {{
                // 2. Inject the HTML content
                newWin.document.open();
                newWin.document.write(`{safe_html}`);
                newWin.document.close();
            }} else {{
                alert('Pop-up blocked! Please enable pop-ups for this site.');
            }}
        }}
        </script>
        """
    return HTML(js_code)