import contextlib
import logging
import os

with contextlib.redirect_stdout(open(os.devnull, "w")):
    from ipystream.voila import patched_generator, auth_wall_limit, patch_voila
from ipystream.voila.utils import create_ipynb, is_sagemaker
import json
import site
import sys
from pathlib import Path


def run(
    disable_logging=True,
    POOL_SIZE=1,
    MAX_KERNELS=8,
    timeout_spinner=20,
    notebook: str | None = None,
    use_xpython: bool | None = None,
    enforce_PARAM_KEY_TOKEN=False,
    log_user_fun=None,
    token_to_user_fun=None,
    extra_args_override=None,
    port=8866,
):
    verify_local_call()
    if use_xpython is None:
        use_xpython = is_sagemaker()

    if use_xpython:
        register_local_xpython()
        patch_solara_comm()

    patched_generator.patch_voila_get_generator(enforce_PARAM_KEY_TOKEN, timeout_spinner)
    auth_wall_limit.patch(log_user_fun, token_to_user_fun, MAX_KERNELS)

    NOTEBOOK = "jupyter.ipynb"

    os.environ["VOILA_APP"] = "1"
    extra_args = [
        f"--port={port}",
        "--no-browser",
        "--Voila.ip=0.0.0.0",
        "--base_url=/",
        "--ServerApp.log_level=ERROR",
        "--show_tracebacks=True",
        "--preheat_kernel=True",
        f"--pool_size={POOL_SIZE}",
    ]

    if not extra_args_override and is_sagemaker():
        extra_args_override = [
            f"--port={port}",
            "--no-browser",
            "--Voila.ip=0.0.0.0",
            "--ServerApp.log_level=ERROR",
            "--show_tracebacks=True",
            "--preheat_kernel=True",
            f"--pool_size={POOL_SIZE}",
            f"--base_url=/jupyterlab/default/proxy/{port}/",
            "--server_url=/",
        ]

    if extra_args_override:
        extra_args = extra_args_override

    create_ipynb(NOTEBOOK, use_xpython, notebook)
    sys.argv = ["voila", NOTEBOOK] + extra_args

    # start Voila
    voila_app = patch_voila.patch()
    voila_app.initialize()
    print(f"APP: http://localhost:{port}")

    if disable_logging:
        logging.disable(logging.CRITICAL)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)

    voila_app.start()


def verify_local_call():
    # 1. Get the literal string of what was run (e.g., "foo.py" or "/a/b/c/foo.py")
    command_input = sys.argv[0]

    # 2. Get the folder where the command was called from (CWD)
    cwd = Path.cwd()

    # 3. Extract ONLY the filename from that input (e.g., "foo.py")
    executed_script_path = Path(command_input)
    filename = executed_script_path.name

    # 4. Combine CWD with just the filename to target the local folder
    local_file_path = cwd / filename

    # 5. Check if that file actually exists in the CWD
    if not local_file_path.exists():
        correct_dir = executed_script_path.parent

        raise Exception(
            f"You must run this script from its own folder.\n\n"
            f"You ran: python {command_input}\n"
            f"Please run:\n"
            f"   cd {correct_dir}\n"
            f"   python {filename}"
        )


def register_local_xpython():
    # 1. Discover the current Python path
    current_python = Path(sys.executable)
    venv_bin_dir = current_python.parent

    # 2. Try to find the correct executable
    # Check for 'xpython' binary first, then fallback to the python launcher
    xpython_bin = venv_bin_dir / "xpython"

    if xpython_bin.exists():
        executable_path = [str(xpython_bin)]
    else:
        # Fallback: Use the python interpreter with the launcher module
        # This is exactly what your successful 'ps aux' showed earlier
        executable_path = [str(current_python), "-m", "xpython_launcher"]

    # 3. Define destination
    kernel_dir = Path("/tmp/xpython")
    kernel_dir.mkdir(parents=True, exist_ok=True)

    # 4. Create the kernel.json
    # We use the discovered executable_path in the 'argv' list
    kernel_data = {
        "argv": executable_path + ["-f", "{connection_file}"],
        "display_name": "xpython (venv)",
        "language": "python",
        "metadata": {"debugger": True},
    }

    # 5. Write the file
    kernel_json_path = kernel_dir / "kernel.json"
    with open(kernel_json_path, "w") as f:
        json.dump(kernel_data, f, indent=2)


def patch_solara_comm():
    try:
        # 1. Find the site-packages directory for the current venv
        # getsitepackages() returns a list; usually index 0 is the primary one
        site_packages = site.getsitepackages()[0]
        comm_file = Path(site_packages) / "solara" / "comm.py"

        if not comm_file.exists():
            return

        # 2. Read the file content
        content = comm_file.read_text()

        # 3. Perform the equivalent of the 'sed' replacement
        target_str = "if comm is not None and comm.create_comm is comm._create_comm:"
        replacement_str = "if False:"

        if target_str in content:
            new_content = content.replace(target_str, replacement_str)
            comm_file.write_text(new_content)

    except Exception:
        pass
