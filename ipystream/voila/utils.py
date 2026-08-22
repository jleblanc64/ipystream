import json
import os
from http.cookies import SimpleCookie
from pathlib import Path

PARAM_KEY_TOKEN = "tok"


def get_token_from_headers(headers_dict):
    cookie = headers_dict.get("Cookie")
    if not cookie:
        return None

    return get_cookie_value(cookie, PARAM_KEY_TOKEN)


def get_cookie_value(cookie_str, key):
    cookie = SimpleCookie()
    cookie.load(cookie_str)
    if key in cookie:
        return cookie[key].value
    return None


def is_sagemaker():
    sm_vars = [
        "SAGEMAKER_SPACE_NAME",
        "SAGEMAKER_APP_TYPE",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
    ]
    return any(var in os.environ for var in sm_vars)


def create_ipynb(path: str, use_xpython: bool, notebook: str | None, lazy_run: bool) -> Path:
    if not notebook:
        folder = "python." if Path("python").is_dir() else ""
        notebook = f"{folder}notebook"

    code = [
        "from ipystream.voila.kernel_heartbeat import setup_heartbeat_checker\n",
        f"from {notebook} import run\n",
        "import warnings\n",
        "warnings.filterwarnings('ignore')\n",
        "setup_heartbeat_checker()\n",
        "run()",
    ]

    if lazy_run:
        code = [
            "from ipystream.voila.kernel_heartbeat import setup_heartbeat_checker\n",
            f"from {notebook} import run\n",
            "import warnings\n",
            "from ipywidgets import Output\n",
            "from IPython.core.display_functions import display\n",
            "from ipystream.voila.utils_browser_ready import on_browser_ready\n",
            "warnings.filterwarnings('ignore')\n",
            "setup_heartbeat_checker()\n",
            "out = Output()\n",
            "display(out)\n",
            "def run_out():\n",
            "    with out:\n",
            "        run()\n",
            "on_browser_ready(run_out)",
        ]

    notebook_data = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "run-cell",
                "metadata": {},
                "outputs": [],
                "source": code,
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    if use_xpython:
        notebook_data["metadata"]["kernelspec"] = {
            "display_name": "xpython",
            "language": "python",
            "name": "xpython",
        }

    content = json.dumps(notebook_data)

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path
