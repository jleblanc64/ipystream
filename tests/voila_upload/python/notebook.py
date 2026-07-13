import io
import base64
import pandas as pd
from IPython.display import display
import ipywidgets as widgets

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class BulletproofTwoStepUploader:
    def __init__(self):
        # Memory slots to store the file state in Python
        self.current_df = None
        self.current_name = None

        # 1. Invisible communication bridges
        self.data_bridge = widgets.Textarea()
        self.data_bridge.add_class('excel-data-bridge')

        self.name_bridge = widgets.Text()
        self.name_bridge.add_class('excel-name-bridge')

        # 2. Print Button (Kept ENABLED from the start to force Voila to bind it!)
        self.print_btn = widgets.Button(
            description="📊 Print Columns",
            button_style="primary",
            layout=widgets.Layout(margin="0 0 0 10px")
        )
        self.print_btn.on_click(self.on_print_clicked)

        # UI Styling Rules
        self.ui_styles = widgets.HTML("""
            <style>
                .excel-data-bridge, .excel-name-bridge { display: none !important; }
                .custom-upload-btn {
                    background-color: #2ecc71;
                    color: white;
                    padding: 6px 16px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: bold;
                    transition: background 0.2s;
                }
                .custom-upload-btn:hover { background-color: #27ae60; }
            </style>
        """)

        # Native input with INLINE javascript execution
        self.uploader_html = widgets.HTML(f"""
            <div style="display: inline-block; vertical-align: middle;">
                <input type="file" id="native-excel-picker" accept=".xlsx, .xls" style="display: none;"
                       onchange="(function(input){{
                           var statusText = document.getElementById('file-status-text');
                           var MAX_BYTES = {MAX_FILE_SIZE_BYTES};
                           try {{
                               var file = input.files[0];
                               if (!file) return;

                               if (file.size > MAX_BYTES) {{
                                   var sizeMb = (file.size / (1024 * 1024)).toFixed(1);
                                   var maxMb = (MAX_BYTES / (1024 * 1024)).toFixed(0);
                                   statusText.style.color = '#e74c3c';
                                   statusText.innerText = '❌ ' + file.name + ' is ' + sizeMb + 'MB - max allowed is ' + maxMb + 'MB';
                                   input.value = '';
                                   return;
                               }}

                               statusText.style.color = '#3498db';
                               statusText.innerText = '⏳ Uploading: ' + file.name;

                               var reader = new FileReader();
                               reader.onload = function(evt) {{
                                   try {{
                                       var base64Data = evt.target.result.split(',')[1];

                                       var dBridge = document.getElementsByClassName('excel-data-bridge')[0].querySelector('textarea');
                                       var nBridge = document.getElementsByClassName('excel-name-bridge')[0].querySelector('input');

                                       nBridge.value = file.name;
                                       nBridge.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                       nBridge.dispatchEvent(new Event('change', {{ bubbles: true }}));

                                       dBridge.value = base64Data;
                                       dBridge.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                       dBridge.dispatchEvent(new Event('change', {{ bubbles: true }}));

                                   }} catch(innerErr) {{
                                       statusText.style.color = '#e74c3c';
                                       statusText.innerText = '❌ Reader Error';
                                   }}
                               }};
                               reader.readAsDataURL(file);
                               input.value = '';
                           }} catch(err) {{
                               statusText.style.color = '#e74c3c';
                               statusText.innerText = '❌ Setup Error';
                           }}
                       }})(this);">

                <button class="custom-upload-btn" onclick="document.getElementById('native-excel-picker').click()">
                    📁 Select Excel File
                </button>
            </div>
        """)

        # Permanent text status label next to buttons
        self.status_label = widgets.HTML(
            value="<span id='file-status-text' style='color: #7f8c8d; font-style: italic; margin-left: 10px; font-weight: bold;'>No file selected</span>",
            layout=widgets.Layout(display="inline-block", margin="5px 0 0 10px")
        )

        self.result_output = widgets.Output()

        # Attach the data watcher to stream raw strings into DataFrames
        self.data_bridge.observe(self.process_incoming_upload, names='value')

        # Combine everything into a neat horizontal toolbar layout
        self.layout = widgets.VBox([
            self.ui_styles,
            self.data_bridge,
            self.name_bridge,
            widgets.HTML("<h3 style='color: #2c3e50; margin-bottom: 15px;'>Two-Step Column Extractor</h3>"),
            widgets.HBox([self.uploader_html, self.print_btn, self.status_label], layout=widgets.Layout(align_items='center')),
            widgets.HTML("<br><hr>"),
            self.result_output
        ])

    def process_incoming_upload(self, change):
        if not change['new']:
            return

        with self.result_output:
            self.result_output.clear_output()

            try:
                # Parse the document into Python's memory space
                b64_data = change['new']
                file_bytes = base64.b64decode(b64_data)

                # Server-side backstop: the client-side check above should
                # already have blocked this, but re-check here in case it's
                # ever bypassed.
                if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                    size_mb = len(file_bytes) / (1024 * 1024)
                    print(f"❌ File is {size_mb:.1f}MB — max allowed is {MAX_FILE_SIZE_MB}MB")
                    self.current_df = None
                    self.current_name = None
                    return

                self.current_name = self.name_bridge.value
                self.current_df = pd.read_excel(io.BytesIO(file_bytes))

                # ONLY display the name on upload (as requested!)
                print(f"✅ Loaded: {self.current_name}")

            except Exception as e:
                print(f"❌ Python Data Storage Error: {e}")
                self.current_df = None

            finally:
                # Flush string bridge immediately so it can sense the next selection
                self.data_bridge.value = ''

    def on_print_clicked(self, b):
        with self.result_output:
            self.result_output.clear_output()

            # Smart Python-side guard clause instead of locking the UI element
            if self.current_df is None:
                print("⚠️ Please upload an Excel file first before attempting to print columns.")
                return

            # Print the dataframe details cleanly
            print(f"📋 Dataset Profile: {self.current_name}")
            print(f"📊 Total Columns ({len(self.current_df.columns)}):")
            print(list(self.current_df.columns))

# Instantiate and show app
def run():
    app = BulletproofTwoStepUploader()
    display(app.layout)