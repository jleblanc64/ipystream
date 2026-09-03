"""
Instrumentation of every step that happens while the voila spinner (#loading) is displayed.

Usage, in Ipystream.run(), BEFORE patch_voila.patch():

    patched_generator.patch_voila_get_generator(enforce_PARAM_KEY_TOKEN, timeout_spinner, show_logo)
    auth_wall_limit.patch(...)
    log_steps.patch_log_steps()

    voila_app = patch_voila.patch()
    voila_app.initialize()

Call it EXACTLY ONCE (the _PATCHED guard enforces this): the class-level patches wrap
whatever is currently installed, so a second call makes every line appear twice.

Ordering constraints:
  - must run AFTER patch_voila_get_generator / auth_wall_limit.patch, since it wraps their versions
  - must run BEFORE voila.app is imported: app.py binds `voila_kernel_manager_factory` by name
    at import time, so the factory has to be swapped first
  - Voila.init_handlers is patched to register the browser log endpoint, because Voila only
    creates self.app inside start(), which then immediately enters the IOLoop

Everything is written with utils_log.log() -> <project root>/logs.txt
"""

import itertools
import time

from ipystream.voila.utils_log import log

_PATCHED = False
_req_counter = itertools.count(1)

BROWSER_LOG_PATH = "ipystream-log"


def _elapsed(t0):
    return f"{(time.perf_counter() - t0) * 1000:.0f}ms"


def patch_log_steps(log_browser_steps=True, log_static_files=True):
    """
    log_static_files: logs every static asset served (voila.js, labextensions, ...).
    Noisy, but this is what tells you whether a slow SageMaker load is the proxy hop
    or the instance itself. Turn it on only while debugging.
    """
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    # keep this one first: it must happen before `voila.app` is imported anywhere
    _patch_kernel_manager()

    _patch_handler()
    _patch_renderer()
    _patch_executor()
    _patch_kernel_websocket()

    if log_static_files:
        _patch_static_handlers()

    if log_browser_steps:
        _patch_browser_log_handler()


# ---------------------------------------------------------------- 1. HTTP request
# voila/handler.py :: VoilaHandler.prepare / get_generator
# get_generator is the async generator whose chunks are streamed to the browser
# while the spinner is up.
def _patch_handler():
    from voila.handler import VoilaHandler

    _orig_prepare = VoilaHandler.prepare
    _orig_get_generator = VoilaHandler.get_generator

    async def prepare(self, *a, **kw):
        self._ipy_id = next(_req_counter)
        self._ipy_t0 = time.perf_counter()
        log(f"[{self._ipy_id}] REQUEST {self.request.path} from {self.request.remote_ip}")
        return await _orig_prepare(self, *a, **kw)

    async def get_generator(self, *a, **kw):
        rid = getattr(self, "_ipy_id", 0)
        t0 = getattr(self, "_ipy_t0", time.perf_counter())
        log(f"[{rid}] GENERATOR start")
        n = 0
        try:
            async for chunk in _orig_get_generator(self, *a, **kw):
                n += 1
                log(f"[{rid}] CHUNK #{n} ({len(chunk)} chars) t={_elapsed(t0)}")
                yield chunk
        finally:
            log(f"[{rid}] GENERATOR done, {n} chunks, total={_elapsed(t0)}")

    VoilaHandler.prepare = prepare
    VoilaHandler.get_generator = get_generator


# ---------------------------------------------------------------- 2. kernel pool
# voila/voila_kernel_manager.py :: get_rendered_notebook / _initialize / fill_if_needed
# With --preheat_kernel=True this is where most of the spinner time is spent:
# either waiting for a kernel of the pool, or refilling it.
def _patch_kernel_manager():
    from voila import voila_kernel_manager

    _orig_factory = voila_kernel_manager.voila_kernel_manager_factory

    def factory(*args, **kwargs):
        cls = _orig_factory(*args, **kwargs)

        _orig_get_rendered = cls.get_rendered_notebook
        _orig_initialize = cls._initialize
        _orig_fill = cls.fill_if_needed

        async def get_rendered_notebook(self, notebook_name, *a, **kw):
            t0 = time.perf_counter()
            pool = self._pools.get(notebook_name, [])
            log(f"POOL take: size={len(pool)} ready={len([t for t in pool if t.done()])}")
            try:
                render_task, rendered_cache, kernel_id = await _orig_get_rendered(self, notebook_name, *a, **kw)
            except Exception as e:
                log(f"POOL error after {_elapsed(t0)}: {type(e).__name__}: {e}")
                raise

            log(f"POOL took kernel {kernel_id} cached_cells={len(rendered_cache)} in {_elapsed(t0)}")
            return render_task, rendered_cache, kernel_id

        async def _initialize(self, notebook_path, kernel_id=None, **kw):
            t0 = time.perf_counter()
            log(f"PREHEAT start ({notebook_path})")
            res = await _orig_initialize(self, notebook_path, kernel_id, **kw)
            log(f"PREHEAT ready kernel={res['kernel_id']} in {_elapsed(t0)}")
            return res

        def fill_if_needed(self, *a, **kw):
            log("POOL refill requested")
            return _orig_fill(self, *a, **kw)

        cls.get_rendered_notebook = get_rendered_notebook
        cls._initialize = _initialize
        cls.fill_if_needed = fill_if_needed
        return cls

    voila_kernel_manager.voila_kernel_manager_factory = factory


# ---------------------------------------------------------------- 3. rendering
# voila/notebook_renderer.py :: initialize / _jinja_kernel_start /
# _jinja_cell_generator / _jinja_notebook_execute / _cleanup_resources
def _patch_renderer():
    from voila.notebook_renderer import NotebookRenderer

    _orig_initialize = NotebookRenderer.initialize
    _orig_kernel_start = NotebookRenderer._jinja_kernel_start
    _orig_cell_gen = NotebookRenderer._jinja_cell_generator
    _orig_cell_gen_noexec = NotebookRenderer._jinja_cell_generator_without_execution
    _orig_nb_execute = NotebookRenderer._jinja_notebook_execute
    _orig_cleanup = NotebookRenderer._cleanup_resources

    async def initialize(self, **kw):
        t0 = time.perf_counter()
        log("RENDERER initialize start")
        res = await _orig_initialize(self, **kw)
        log(f"RENDERER initialize done (template={self.template_name}) in {_elapsed(t0)}")
        return res

    async def _jinja_kernel_start(self, nb, kernel_id, kernel_future):
        t0 = time.perf_counter()
        log(f"KERNEL start/connect kernel_id={kernel_id}")
        res = await _orig_kernel_start(self, nb, kernel_id, kernel_future)
        log(f"KERNEL client ready kernel_id={kernel_id} in {_elapsed(t0)}")
        return res

    def _wrap_cell_gen(orig, label):
        async def gen(self, nb, kernel_id):
            t0 = time.perf_counter()
            total = len(nb.cells)
            log(f"{label} start, {total} cells (kernel={kernel_id})")
            i = 0
            async for cell in orig(self, nb, kernel_id):
                i += 1
                log(f"{label} cell {i}/{total} rendered t={_elapsed(t0)}")
                yield cell
            log(f"{label} finished in {_elapsed(t0)}")

        return gen

    async def _jinja_notebook_execute(self, nb, kernel_id):
        t0 = time.perf_counter()
        log(f"NOTEBOOK execute start (kernel={kernel_id})")
        res = await _orig_nb_execute(self, nb, kernel_id)
        log(f"NOTEBOOK execute done in {_elapsed(t0)}")
        return res

    async def _cleanup_resources(self):
        log("RENDERER cleanup (stop kernel client channels)")
        return await _orig_cleanup(self)

    NotebookRenderer.initialize = initialize
    NotebookRenderer._jinja_kernel_start = _jinja_kernel_start
    NotebookRenderer._jinja_cell_generator = _wrap_cell_gen(_orig_cell_gen, "CELLS")
    NotebookRenderer._jinja_cell_generator_without_execution = _wrap_cell_gen(
        _orig_cell_gen_noexec, "CELLS(progressive)"
    )
    NotebookRenderer._jinja_notebook_execute = _jinja_notebook_execute
    NotebookRenderer._cleanup_resources = _cleanup_resources


# ---------------------------------------------------------------- 4. cell execution
# voila/execute.py :: VoilaExecutor.execute_cell (already patched by patched_generator2)
def _patch_executor():
    from voila.execute import VoilaExecutor

    _orig_execute_cell = VoilaExecutor.execute_cell

    async def execute_cell(self, cell, resources, cell_index, *a, **kw):
        t0 = time.perf_counter()
        source = (getattr(cell, "source", "") or "").strip().splitlines()
        first_line = source[0][:80] if source else ""
        log(f"EXEC cell {cell_index} start: {first_line}")
        try:
            return await _orig_execute_cell(self, cell, resources, cell_index, *a, **kw)
        finally:
            log(f"EXEC cell {cell_index} end in {_elapsed(t0)}")

    VoilaExecutor.execute_cell = execute_cell


# ---------------------------------------------------------------- 5. browser websocket
# jupyter_server :: KernelWebsocketHandler.open -> the browser now talks to the kernel
def _patch_kernel_websocket():
    try:
        from jupyter_server.services.kernels.websocket.handler import KernelWebsocketHandler
    except ImportError:  # jupyter_server < 2
        from jupyter_server.services.kernels.handlers import KernelWebsocketHandler

    _orig_open = KernelWebsocketHandler.open
    _orig_close = KernelWebsocketHandler.on_close

    async def open(self, kernel_id, *a, **kw):
        log(f"WS browser connected to kernel {kernel_id}")
        return await _orig_open(self, kernel_id, *a, **kw)

    def on_close(self, *a, **kw):
        log(f"WS browser disconnected from kernel {getattr(self, 'kernel_id', '?')}")
        return _orig_close(self, *a, **kw)

    KernelWebsocketHandler.open = open
    KernelWebsocketHandler.on_close = on_close


# ---------------------------------------------------------------- 6. static assets
# On SageMaker everything goes through /jupyterlab/default/proxy/<port>/, so the JS
# bundles are often what the spinner is really waiting on. StaticFileHandler is the
# base class of voila's AllowListFileHandler and of FileFindHandler, so this covers
# all asset routes at once.
def _patch_static_handlers():
    import tornado.web

    _orig_on_finish = tornado.web.StaticFileHandler.on_finish

    def on_finish(self):
        t0 = getattr(self.request, "_start_time", None)
        ms = f"{(time.time() - t0) * 1000:.0f}ms" if t0 else "?"
        size = self._headers.get("Content-Length", "?")
        log(f"STATIC {self.request.path} {self.get_status()} {size}b in {ms}")
        return _orig_on_finish(self)

    tornado.web.StaticFileHandler.on_finish = on_finish


# ---------------------------------------------------------------- 7. browser side
# The last steps of the spinner happen in JS: voila_process(i, n) updates the
# "Executing i of n" text, and voila_finish() -> display_cells() removes #loading.
# We wrap both and POST to <base_url>/ipystream-log so they land in the same file.
#
# Add BROWSER_LOG_JS to the string returned by patched_generator.build_injection().
BROWSER_LOG_JS = (
    "<script>"
    "(function() {"
    "  var t0 = Date.now();"
    "  function send(msg) {"
    f"    try {{ fetch('{BROWSER_LOG_PATH}', {{method: 'POST', body: msg + ' (+' + (Date.now() - t0) + 'ms)', keepalive: true}}); }} catch (e) {{}}"
    "  }"
    "  send('page received, spinner visible');"
    "  window.addEventListener('DOMContentLoaded', function() { send('DOMContentLoaded'); });"
    "  window.addEventListener('load', function() { send('window load (assets done)'); });"
    "  var iv = setInterval(function() {"
    "    if (!window.voila_process || !window.voila_finish) return;"
    "    clearInterval(iv);"
    "    var p = window.voila_process, f = window.voila_finish;"
    "    window.voila_process = function(i, n) { send('voila_process ' + i + '/' + n); return p.apply(this, arguments); };"
    "    window.voila_finish = function() { send('voila_finish -> spinner removed'); return f.apply(this, arguments); };"
    "  }, 50);"
    "})();"
    "</script>"
)


def _patch_browser_log_handler():
    import tornado.web
    from voila.app import Voila

    class _LogHandler(tornado.web.RequestHandler):
        def check_xsrf_cookie(self):
            pass

        def post(self):
            log(f"BROWSER {self.request.body.decode('utf-8', 'replace')[:300]}")
            self.finish("")

    _orig_init_handlers = Voila.init_handlers

    def init_handlers(self):
        handlers = _orig_init_handlers(self)
        handlers.insert(0, (rf".*/{BROWSER_LOG_PATH}$", _LogHandler))
        return handlers

    Voila.init_handlers = init_handlers