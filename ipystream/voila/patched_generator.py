import os
import asyncio
import psutil
from tornado.httputil import split_host_and_port
from voila.notebook_renderer import NotebookRenderer
from voila.utils import ENV_VARIABLE, get_page_config
from nbclient.util import ensure_async
from voila.handler import VoilaHandler
from tornado.web import HTTPError

from ipystream.voila.kernel import get_kernel_manager
from ipystream.voila.patch_voila import _schedule_kernel_shutdown
from ipystream.voila.utils import get_token_from_headers, PARAM_KEY_TOKEN

VOILA_SPINNER_TIMEOUT = 20

injection = (
    "<style>"
    "body.jp-Notebook, .jp-Notebook { background-color: white !important; color: black !important; }"
    ".jp-Cell { background-color: white !important; color: black !important; }"
    "label, div, span, p, li, th, td, pre { color: black !important; }"
    "select { background-color: white !important; color: black !important; }"
    ".leaflet-control-legend { background-color: white !important; color: black !important; }"
    "</style>"
)

timeout_html = """
<script>
    window.stop();
    document.body.innerHTML = '<div style="padding:50px;text-align:center;font-family:sans-serif;"><h2>Resource Limit Reached</h2><p>The kernel was unresponsive and has been reaped.</p><button onclick="location.reload()">Reload</button></div>';
</script>
"""

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

        if self.notebook_path and path:
            self.redirect_to_file(path)
            return

        # State for the watchdog
        self.kernel_terminated = False

        async def watchdog_task(k_id, pid, handler):
            """Voila spinner timeout"""
            await asyncio.sleep(VOILA_SPINNER_TIMEOUT)
            if not self.kernel_terminated:
                self.kernel_terminated = True
                try:
                    handler.write(timeout_html)
                    await handler.flush()
                    # Surgical OS kill
                    p = psutil.Process(pid)
                    for child in p.children(recursive=True): child.kill()
                    p.kill()
                except: pass
                finally:
                    global_kernel_manager = get_kernel_manager()
                    _schedule_kernel_shutdown(global_kernel_manager, k_id)

        # ... (Original request_info and header setup remains exactly the same) ...
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
        # ... (Cache-Control headers) ...

        template_arg = self.get_argument("template", None)
        theme_arg = self.get_argument("theme", None)
        extra_kernel_env_variables = {ENV_VARIABLE.VOILA_REQUEST_URL: self.request.full_url()}

        if self.should_use_rendered_notebook(getattr(self.kernel_manager, 'notebook_data', {}).get(notebook_path, {}),
                                             getattr(self.kernel_manager, 'get_pool_size', lambda x: 0)(notebook_path),
                                             template_arg, theme_arg, self.request.arguments):

            render_task, rendered_cache, kernel_id = await self.kernel_manager.get_rendered_notebook(
                notebook_name=notebook_path, extra_kernel_env_variables=extra_kernel_env_variables
            )

            # Start Watchdog for Pool Kernel
            km = self.kernel_manager.get_kernel(kernel_id)
            pid = km.provisioner.process.pid if hasattr(km, 'provisioner') else km.process.pid
            reaper = asyncio.create_task(watchdog_task(kernel_id, pid, self))

            if len(rendered_cache) > 0: yield "".join(rendered_cache)
            rendered, rendering = await render_task
            async for html_snippet, _ in rendering:
                if self.kernel_terminated: return
                yield html_snippet

            self.kernel_terminated = True
            reaper.cancel()

        else:
            # Fresh Kernel Path
            gen = NotebookRenderer(request_handler=self, notebook_path=notebook_path,
                                   voila_configuration=self.voila_configuration, traitlet_config=self.traitlet_config,
                                   template_paths=self.template_paths, config_manager=self.config_manager,
                                   contents_manager=self.contents_manager, base_url=self.base_url,
                                   kernel_spec_manager=self.kernel_spec_manager, page_config=get_page_config(base_url=self.base_url, settings=self.settings, log=self.log, voila_configuration=self.voila_configuration))
            await gen.initialize(template=template_arg, theme=theme_arg)

            kernel_id = await ensure_async(self.kernel_manager.start_kernel(kernel_name=gen.notebook.metadata.kernelspec.name, path=cwd, env={**os.environ, **request_info}))

            # Start Watchdog for Fresh Kernel
            km = self.kernel_manager.get_kernel(kernel_id)
            pid = km.provisioner.process.pid if hasattr(km, 'provisioner') else km.process.pid
            reaper = asyncio.create_task(watchdog_task(kernel_id, pid, self))

            queue = asyncio.Queue()
            async def put_html():
                async for snippet, _ in gen.generate_content_generator(kernel_id, self.kernel_manager.get_kernel(kernel_id)):
                    await queue.put(snippet)
                await queue.put(None)
            asyncio.ensure_future(put_html())

            while True:
                try:
                    html_snippet = await asyncio.wait_for(queue.get(), VOILA_SPINNER_TIMEOUT)
                    if html_snippet is None or self.kernel_terminated: break
                    yield injection + html_snippet
                except asyncio.TimeoutError:
                    if not self.kernel_terminated:
                        self.kernel_terminated = True
                        global_kernel_manager = get_kernel_manager()
                        _schedule_kernel_shutdown(global_kernel_manager, kernel_id)
                        yield timeout_html
                    break

            self.kernel_terminated = True
            reaper.cancel()

    VoilaHandler.get_generator = patched_get_generator