from ipystream.voila.utils import PARAM_KEY_TOKEN, is_sagemaker


def add_v_cookie(Voila):
    def v_cookie_wrapper(handler_class):
        class VCookieHandler(handler_class):
            async def prepare(self):
                # Get the token from URL query parameters
                v = self.get_argument(PARAM_KEY_TOKEN, None)
                if v:
                    # Set the cookie
                    self.set_cookie(PARAM_KEY_TOKEN, v, path="/", httponly=True)
                    host_info = self.request.host  # e.g., "localhost:8867"

                    port = "8866"
                    if ":" in host_info:
                        port = host_info.split(":")[-1]

                    # Redirect to clean URL
                    self.redirect(clean_url(port))
                    return

                # Call parent prepare (sync or async)
                parent_prepare = super().prepare()
                if parent_prepare is not None:
                    await parent_prepare

        return VCookieHandler

    _original_init_handlers = Voila.init_handlers

    def _patched_init_handlers(self):
        handlers = _original_init_handlers(self)

        wrapped = []
        for h in handlers:
            pattern, handler_class, *rest = h
            wrapped.append((pattern, v_cookie_wrapper(handler_class), *rest))
        return wrapped

    Voila.init_handlers = _patched_init_handlers


def clean_url(port):
    return f"/jupyterlab/default/proxy/{port}/" if is_sagemaker() else "/"
