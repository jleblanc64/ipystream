def get_logo_html(_LOGO_B64):
    return (
        f"""
        <style>
            /* 1. HIDE LOADING STATUS */
            #loading_text, 
            .voila-spinner-status, 
            .jp-Spinner-label, 
            #loading h2 {{
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
            }}

            /* 2. ENHANCED LOGO STYLING */
            #voila-logo-wrapper {{ display: none; }}
            #voila-logo {{
                position: absolute;
                top: 20px;          /* Slightly more breathing room */
                right: 25px;
                height: 120px;      /* INCREASED SIZE FROM 80px */
                width: auto;
                z-index: 10000;
                background: white;
                padding: 10px;      /* Increased padding for the larger size */
                border-radius: 12px;
                border: 1px solid #ddd;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1); /* Softer shadow for the larger element */
            }}
            
            /* Ensure the notebook container allows absolute positioning for the logo */
            #rendered_cells {{ 
                position: relative !important; 
            }}
        </style>

        <div id="voila-logo-wrapper">
            <img id="voila-logo" src="data:image/png;base64,{_LOGO_B64}" />
        </div>

        <script>
        (function() {{
            // 3. JAVASCRIPT HIJACK
            window.update_loading_text = function(cell_index, cell_count, text) {{
                // Muted
            }};
            window.voila_process = window.update_loading_text;

            // 4. LOGO MOVER
            var moveAttempts = 0;
            var logoMover = setInterval(function() {{
                var scrollContainer = document.getElementById('rendered_cells');
                var logo = document.getElementById('voila-logo-wrapper');
                if (scrollContainer && logo) {{
                    scrollContainer.prepend(logo);
                    logo.style.display = 'block';
                    clearInterval(logoMover);
                }}
                moveAttempts++;
                if (moveAttempts > 100) clearInterval(logoMover);
            }}, 100);
        }})();
        </script>
        """
    )