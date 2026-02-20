import os
from pathlib import Path
from typing import Dict

from tornado.httputil import split_host_and_port
from voila.notebook_renderer import NotebookRenderer
from voila.request_info_handler import RequestInfoSocketHandler
from voila.tornado.execution_request_handler import ExecutionRequestHandler
from voila.utils import ENV_VARIABLE, get_page_config
from nbclient.util import ensure_async
import asyncio
import json
from voila.handler import VoilaHandler
from tornado.web import HTTPError

from ipystream.voila.patched_generator2 import timeout
from ipystream.voila.utils import get_token_from_headers, PARAM_KEY_TOKEN

import base64

def build_injection(timeout_spinner, logo_path="/home/charles/Downloads/logo.png"):
    try:
        with open("/home/charles/Downloads/logo.png", "rb") as _f:
            _LOGO_B64 = base64.b64encode(_f.read()).decode()
        logo_html = (
            f"<img id='voila-logo' src='data:image/png;base64,{_LOGO_B64}' "
            "style='position:absolute;top:16px;right:20px;height:80px;z-index:10000;"
            "pointer-events:none;"
            "border:4px solid #333;"
            "border-radius:8px;"
            "padding:6px;"
            "background:white;"
            "box-shadow:0 2px 8px rgba(0,0,0,0.15);' />"
        )
    except Exception:
        logo_html = ""

    return (
            "<style>"
            "body.jp-Notebook, .jp-Notebook { background-color: white !important; color: black !important; }"
            ".jp-Cell { background-color: white !important; color: black !important; }"
            "label, div, span, p, li, th, td, pre { color: black !important; }"
            "select { background-color: white !important; color: black !important; }"
            ".leaflet-control-legend { background-color: white !important; color: black !important; }"
            "#voila-timeout-msg { "
            "   display: none; position: fixed; top: 10%; left: 50%; transform: translateX(-50%); "
            "   background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; "
            "   padding: 15px 30px; border-radius: 4px; z-index: 10001; font-family: sans-serif;"
            "}"
            "</style>"
            + logo_html +
            "<div id='voila-timeout-msg'>voila timeout, check your connection</div>"
            "<script>"
            "(function() {"
            "    setTimeout(function() {"
            "        var loader = document.querySelector('.voila-spinner, #loading, .jp-Spinner'); "
            "        if (loader && window.getComputedStyle(loader).display !== 'none') {"
            "            document.getElementById('voila-timeout-msg').style.display = 'block';"
            "            loader.style.display = 'none';"
            "        }"
            f"    }}, {(timeout_spinner + 5) * 1000});"
            "})();"
            "</script>"
    )


def patch_voila_get_generator(enforce_PARAM_KEY_TOKEN, timeout_spinner):
    # --- Patch VoilaHandler to require ?user=... ---
    _original_prepare = VoilaHandler.prepare

    async def _patched_prepare(self):
        path = self.request.path

        if len(path) <= 1:
            headers = dict(self.request.headers)
            token = get_token_from_headers(headers)

            # fallback use url param, useful for first query
            if not token:
                token = self.get_query_argument(PARAM_KEY_TOKEN, None)

            if not token:
                raise HTTPError(
                    403, f"Access denied: ?{PARAM_KEY_TOKEN} parameter required"
                )

        await _original_prepare(self)

    if enforce_PARAM_KEY_TOKEN:
        VoilaHandler.prepare = _patched_prepare

    """
    Monkey-patch VoilaHandler.get_generator with the exact given implementation,
    but with a corrected signature so Tornado can call it properly.
    """

    async def patched_get_generator(self, path=None, *args, **kwargs):
        # Tornado sometimes passes path via args
        if path is None and len(args) > 0:
            path = args[0]

        # --- BEGIN: exact original code block ---------------------
        # (Only the function signature changed)

        # if the handler got a notebook_path argument, always serve that
        notebook_path = self.notebook_path or path

        if (
            self.notebook_path and path
        ):  # when we are in single notebook mode but have a path
            self.redirect_to_file(path)
            return

        cwd = os.path.dirname(notebook_path)
        # Adding request uri to kernel env
        request_info = {}
        request_info[ENV_VARIABLE.SCRIPT_NAME] = self.request.path
        request_info[ENV_VARIABLE.PATH_INFO] = ""
        request_info[ENV_VARIABLE.QUERY_STRING] = str(self.request.query)
        request_info[ENV_VARIABLE.SERVER_SOFTWARE] = "voila/0.5.10"
        request_info[ENV_VARIABLE.SERVER_PROTOCOL] = str(self.request.version)
        host, port = split_host_and_port(self.request.host.lower())

        request_info[ENV_VARIABLE.SERVER_PORT] = str(port) if port else ""
        request_info[ENV_VARIABLE.SERVER_NAME] = host

        # Add HTTP Headers as env vars following rfc3875#section-4.1.18
        if len(self.voila_configuration.http_header_envs) > 0:
            for header_name in self.request.headers:
                config_headers_lower = [
                    header.lower()
                    for header in self.voila_configuration.http_header_envs
                ]
                if header_name.lower() in config_headers_lower:
                    env_name = f'HTTP_{header_name.upper().replace("-", "_")}'
                    request_info[env_name] = self.request.headers.get(header_name)

        template_arg = self.get_argument("template", None)
        theme_arg = self.get_argument("theme", None)

        self.set_header("Content-Type", "text/html")
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

        # FIX: Yield injection here so it only happens once per page load
        yield build_injection(timeout_spinner)

        try:
            current_notebook_data: Dict = self.kernel_manager.notebook_data.get(
                notebook_path, {}
            )
            pool_size: int = self.kernel_manager.get_pool_size(notebook_path)
        except AttributeError:
            current_notebook_data = {}
            pool_size = 0

        # add headers
        extra_kernel_env_variables = {
            ENV_VARIABLE.VOILA_REQUEST_URL: self.request.full_url()
        }
        if self.request.headers:
            extra_kernel_env_variables["headers"] = json.dumps(
                {k: v for k, v in self.request.headers.items()}
            )

        if self.should_use_rendered_notebook(
            current_notebook_data,
            pool_size,
            template_arg,
            theme_arg,
            self.request.arguments,
        ):
            (
                render_task,
                rendered_cache,
                kernel_id,
            ) = await self.kernel_manager.get_rendered_notebook(
                notebook_name=notebook_path,
                extra_kernel_env_variables=extra_kernel_env_variables,
            )

            RequestInfoSocketHandler.send_updates(
                {"kernel_id": kernel_id, "payload": request_info}
            )

            if len(rendered_cache) > 0:
                yield "".join(rendered_cache)

            rendered, rendering = await render_task
            if len(rendered) > len(rendered_cache):
                html_snippet = "".join(rendered[len(rendered_cache) :])
                yield html_snippet

            async for html_snippet, _ in rendering:
                yield html_snippet

        else:
            supported_file_extensions = [".ipynb"]
            supported_file_extensions.extend(
                [x.lower() for x in self.voila_configuration.extension_language_mapping]
            )
            file_extenstion = Path(notebook_path).suffix.lower()
            if file_extenstion not in supported_file_extensions:
                self.redirect_to_file(path)
                return

            mathjax_config = self.settings.get("mathjax_config")
            mathjax_url = self.settings.get("mathjax_url")

            page_config_kwargs = {
                "base_url": self.base_url,
                "settings": self.settings,
                "log": self.log,
                "voila_configuration": self.voila_configuration,
            }

            page_config = get_page_config(**page_config_kwargs)

            if self.page_config_hook:
                page_config = self.page_config_hook(
                    page_config,
                    **page_config_kwargs,
                    notebook_path=notebook_path,
                )

            gen = NotebookRenderer(
                request_handler=self,
                voila_configuration=self.voila_configuration,
                traitlet_config=self.traitlet_config,
                notebook_path=notebook_path,
                template_paths=self.template_paths,
                config_manager=self.config_manager,
                contents_manager=self.contents_manager,
                base_url=self.base_url,
                kernel_spec_manager=self.kernel_spec_manager,
                prelaunch_hook=self.prelaunch_hook,
                page_config=page_config,
                mathjax_config=mathjax_config,
                mathjax_url=mathjax_url,
            )

            await gen.initialize(template=template_arg, theme=theme_arg)

            def time_out():
                return "<script>window.voila_heartbeat()</script>\n"

            kernel_env = {**os.environ, **request_info}
            kernel_env[ENV_VARIABLE.VOILA_PREHEAT] = "False"
            kernel_env[ENV_VARIABLE.VOILA_BASE_URL] = self.base_url
            kernel_env[ENV_VARIABLE.VOILA_SERVER_URL] = self.settings.get(
                "server_url", "/"
            )
            kernel_env[ENV_VARIABLE.VOILA_REQUEST_URL] = self.request.full_url()
            kernel_env[ENV_VARIABLE.VOILA_APP_PORT] = request_info[
                ENV_VARIABLE.SERVER_PORT
            ]

            kernel_id = await ensure_async(
                self.kernel_manager.start_kernel(
                    kernel_name=gen.notebook.metadata.kernelspec.name,
                    path=cwd,
                    env=kernel_env,
                )
            )
            kernel_future = self.kernel_manager.get_kernel(kernel_id)
            queue = asyncio.Queue()

            if self.voila_configuration.progressive_rendering:
                ExecutionRequestHandler._execution_data[kernel_id] = {
                    "nb": gen.notebook,
                    "config": self.traitlet_config,
                    "show_tracebacks": self.voila_configuration.show_tracebacks,
                }

            async def put_html():
                async for html_snippet, _ in gen.generate_content_generator(
                    kernel_id, kernel_future
                ):
                    await queue.put(html_snippet)
                await queue.put(None)

            asyncio.ensure_future(put_html())

            while True:
                try:
                    html_snippet = await asyncio.wait_for(
                        queue.get(), self.voila_configuration.http_keep_alive_timeout
                    )
                except asyncio.TimeoutError:
                    yield time_out()
                else:
                    if html_snippet is None:
                        # Ensure the error message is hidden when finished
                        yield "<script>document.getElementById('voila-timeout-msg').style.display='none';</script>"
                        break
                    # --- FIX: Yield pure snippet without prepending injection ---
                    yield html_snippet

        # --- END of original code -------------

    # Bind correctly as instance method
    VoilaHandler.get_generator = timeout(patched_get_generator, timeout_spinner)