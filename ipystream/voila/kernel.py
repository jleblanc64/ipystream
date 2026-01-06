import json
import os
import re
from pathlib import Path
from IPython import get_ipython
from jupyter_server.services.kernels.kernelmanager import MappingKernelManager

global_kernel_manager = None


def get_kernel_manager():
    global global_kernel_manager
    return global_kernel_manager


# --- CATCH global_kernel_manager
_original_start_kernel = MappingKernelManager.start_kernel


def limited_start_kernel(self, **kwargs):
    global global_kernel_manager
    if global_kernel_manager is None:
        global_kernel_manager = self

    return _original_start_kernel(self, **kwargs)


MappingKernelManager.start_kernel = limited_start_kernel

_original_shutdown_kernel = MappingKernelManager.shutdown_kernel


def get_original_shutdown_kernel():
    global _original_shutdown_kernel
    return _original_shutdown_kernel


def get_user():
    kernel_to_user = _load_kernel_to_user()
    return kernel_to_user.get(get_kernel_id())


def get_token(cache: dict = {}):
    if "TEST" in cache:
        return cache["jwt"]

    kernel_to_token = _load_kernel_to_user(KERNEL_TO_TOKEN_FILE)
    return kernel_to_token.get(get_kernel_id())

def get_kernel_id():
    ipython = get_ipython()
    if not ipython:
        return "0"

    env_id = os.environ.get("VOILA_KERNEL_ID")
    return env_id if env_id else re.search(r"kernel-(.*)\.json", ipython.config.get("IPKernelApp", {}).get("connection_file", "")).group(1)


def pair_mappings(unpaired_mappings):
    return [[a, b] for a, b in zip(*unpaired_mappings)]


def unpair_mappings(paired_mappings):
    return [list(t) for t in zip(*paired_mappings)]


# --- Helper functions ---
KERNEL_TO_USER_FILE = "kernel_to_user.json"
KERNEL_TO_TOKEN_FILE = "kernel_to_token.json"


def _save_kernel_to_user(data, file=KERNEL_TO_USER_FILE):
    path = find_project_root() / file
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _load_kernel_to_user(file=KERNEL_TO_USER_FILE):
    path = find_project_root() / file
    with open(path, "r") as f:
        return json.load(f)


root_files = [".git", "requirements.txt"]


def find_project_root() -> Path | None:
    start_path = Path.cwd().resolve()
    # Check the start path and all its parents
    for folder in [start_path, *start_path.parents]:
        if any((folder / f).exists() for f in root_files):
            return folder
    return None
