from ipystream.voila.utils import PARAM_KEY_TOKEN
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def add_v_cookie(Voila):
    def v_cookie_wrapper(handler_class):
        class VCookieHandler(handler_class):
            async def prepare(self):
                # Get the token from URL query parameters
                v = self.get_argument(PARAM_KEY_TOKEN, None)
                if v:
                    # Set the cookie
                    self.set_cookie(PARAM_KEY_TOKEN, v, path="/", httponly=True)

                    # Remove token from URL and redirect
                    parsed_url = urlparse(self.request.uri)
                    query_params = parse_qs(parsed_url.query)

                    # Remove the token parameter
                    if PARAM_KEY_TOKEN in query_params:
                        del query_params[PARAM_KEY_TOKEN]

                    # Rebuild URL without the token
                    new_query = urlencode(query_params, doseq=True)
                    clean_url = urlunparse(
                        (
                            parsed_url.scheme,
                            parsed_url.netloc,
                            parsed_url.path,
                            parsed_url.params,
                            new_query,
                            parsed_url.fragment,
                        )
                    )

                    # Redirect to clean URL
                    self.redirect(clean_url)
                    return  # Stop further processing

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
