import os
import asyncio
import json
from pathlib import Path
from typing import Dict

from tornado.httputil import split_host_and_port
from voila.notebook_renderer import NotebookRenderer
from voila.utils import ENV_VARIABLE, get_page_config
from nbclient.util import ensure_async
from voila.handler import VoilaHandler
from tornado.web import HTTPError
from ipystream.voila.utils import get_token_from_headers, PARAM_KEY_TOKEN

# Custom Timeout HTML
timeout_html = """
<script>
    window.stop();
    document.body.innerHTML = '<div style="padding:50px;text-align:center;font-family:sans-serif;"><h2>Resource Limit Reached</h2><p>The kernel was unresponsive and has been reaped.</p><button onclick="location.reload()">Reload</button></div>';
</script>
"""

injection = (
    "<style>"
    # Target the root, the notebook, and the main container
    ":root, body, #main, .jp-Notebook, #rendered_cells { background-color: red !important; color: black !important; }"
    ".jp-Cell, .jp-OutputArea-output { background-color: red !important; color: black !important; }"
    "label, div, span, p, li, th, td, pre { color: black !important; }"
    # This ensures that even after Voila "finishes" loading, the red persists
    ".voila-loading { background-color: red !important; }"
    "</style>"
)

def patch_voila_get_generator(enforce_PARAM_KEY_TOKEN):
    _original_prepare = VoilaHandler.prepare

    async def _patched_prepare(self):
        path = self.request.path
        if len(path) <= 1:
            headers = dict(self.request.headers)
            token = get_token_from_headers(headers) or self.get_query_argument(PARAM_KEY_TOKEN, None)
            if not token:
                raise HTTPError(403, f"Access denied: ?{PARAM_KEY_TOKEN} parameter required")
        await _original_prepare(self)

    if enforce_PARAM_KEY_TOKEN:
        VoilaHandler.prepare = _patched_prepare

    async def patched_get_generator(self, path=None, *args, **kwargs):
        if path is None and len(args) > 0:
            path = args[0]

        notebook_path = self.notebook_path or path
        cwd = os.path.dirname(notebook_path)

        request_info = {
            ENV_VARIABLE.SCRIPT_NAME: self.request.path,
            ENV_VARIABLE.PATH_INFO: "",
            ENV_VARIABLE.QUERY_STRING: str(self.request.query),
            ENV_VARIABLE.SERVER_SOFTWARE: "voila/0.5.10",
            ENV_VARIABLE.SERVER_PROTOCOL: str(self.request.version)
        }
        host, port = split_host_and_port(self.request.host.lower())
        request_info[ENV_VARIABLE.SERVER_PORT] = str(port) if port else ""
        request_info[ENV_VARIABLE.SERVER_NAME] = host

        self.set_header("Content-Type", "text/html")

        template_arg = self.get_argument("template", None)
        theme_arg = self.get_argument("theme", None)

        # Fresh Path Logic
        gen = NotebookRenderer(
            request_handler=self, voila_configuration=self.voila_configuration,
            traitlet_config=self.traitlet_config, notebook_path=notebook_path,
            template_paths=self.template_paths, config_manager=self.config_manager,
            contents_manager=self.contents_manager, base_url=self.base_url,
            kernel_spec_manager=self.kernel_spec_manager, page_config=get_page_config(
                base_url=self.base_url, settings=self.settings, log=self.log, voila_configuration=self.voila_configuration)
        )
        await gen.initialize(template=template_arg, theme=theme_arg)

        kernel_id = await ensure_async(self.kernel_manager.start_kernel(
            kernel_name=gen.notebook.metadata.kernelspec.name, path=cwd, env={**os.environ, **request_info}))

        kernel_future = self.kernel_manager.get_kernel(kernel_id)
        queue = asyncio.Queue()

        async def put_html():
            async for html_snippet, _ in gen.generate_content_generator(kernel_id, kernel_future):
                await queue.put(html_snippet)
            await queue.put(None)

        asyncio.ensure_future(put_html())

        style_injected = False
        while True:
            try:
                # Use a 20-second timeout for the queue
                html_snippet = await asyncio.wait_for(queue.get(), timeout=20)

                if html_snippet is None:
                    break

                # --- THE FIX ---
                # We only inject the style ONCE, and we do it by prepending it
                # to the first valid string chunk that comes out of the queue.
                if not style_injected and isinstance(html_snippet, str):
                    yield injection + html_snippet
                    style_injected = True
                else:
                    # For all subsequent chunks, and for the integer '1' status chunk,
                    # we yield them exactly as they are.
                    yield html_snippet

            except asyncio.TimeoutError:
                # On actual timeout, yield the clean timeout script
                yield timeout_html
                break

    VoilaHandler.get_generator = patched_get_generator