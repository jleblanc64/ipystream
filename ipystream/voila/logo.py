def get_logo_html(_LOGO_B64):
    return (
        f"""
        <style>
            /* 1. CSS BLUNT FORCE: Hide the loading container text and the H2 specifically */
            #loading_text, 
            .voila-spinner-status, 
            .jp-Spinner-label, 
            #loading h2 {{
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
            }}

            /* 2. LOGO POSITIONING (Fixed for your template) */
            #voila-logo-wrapper {{ display: none; }}
            #voila-logo {{
                position: absolute;
                top: 16px;
                right: 20px;
                height: 80px;
                z-index: 10000;
                background: white;
                padding: 5px;
                border-radius: 8px;
                border: 1px solid #ddd;
            }}
            #rendered_cells {{ position: relative !important; }}
        </style>

        <div id="voila-logo-wrapper">
            <img id="voila-logo" src="data:image/png;base64,{_LOGO_B64}" />
        </div>

        <script>
        (function() {{
            // 3. JAVASCRIPT HIJACK: Overwrite Voila's update function so it does NOTHING
            window.update_loading_text = function(cell_index, cell_count, text) {{
                console.log("Voila tried to show text, but we blocked it.");
                // We leave this empty so no text is ever injected
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