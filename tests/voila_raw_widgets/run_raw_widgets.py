from ipystream.voila import run_raw
from tests.voila_raw_widgets.slow_connection import slow_connection

slow_connection()
run_raw.run()
