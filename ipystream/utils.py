from IPython.core.display_functions import display, update_display
from ipywidgets import IntText

internal_counter_desc = "#{[34_9azerfcd"
quiet_display_key = "quiet_display"
logs_key = "logs"

def is_internal_counter(widget):
    if not isinstance(widget, IntText):
        return False

    return widget.description == internal_counter_desc

def remove_internal_counter(l):
    return [x for x in l if not is_internal_counter(x)]

def proxy_display(widg, display_id, cache):
    if quiet_display_key in cache:
        log(widg, display_id, cache)
    else:
        display(widg, display_id=display_id)

def proxy_update_display(widg, display_id, cache):
    if quiet_display_key in cache:
        log(widg, display_id, cache)
    else:
        update_display(widg, display_id=display_id)

def log(widg, display_id, cache):
    if logs_key not in cache:
        cache[logs_key] = {}

    cache[logs_key][display_id] = widg
