import logging
import os
from ipystream.voila import patched_generator, auth_wall_limit, patch_voila
from ipystream.voila.utils import create_ipynb
import json
import site
import sys
from pathlib import Path

def run(
    disable_logging=True,
    POOL_SIZE=1,
    MAX_KERNELS=8,
    use_xpython=True,
    enforce_PARAM_KEY_TOKEN=False,
    log_user_fun=None,
    token_to_user_fun=None,
    extra_args_override=None,
    port=8866,
):
    if use_xpython:
        register_local_xpython()
        patch_solara_comm()

    patched_generator.patch_voila_get_generator(enforce_PARAM_KEY_TOKEN)
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

    if extra_args_override:
        extra_args = extra_args_override

    create_ipynb(NOTEBOOK, use_xpython)
    sys.argv = ["voila", NOTEBOOK] + extra_args

    # start Voila
    voila_app = patch_voila.patch()
    voila_app.initialize()
    print(f"VOILA: http://localhost:{port}")

    if disable_logging:
        logging.disable(logging.CRITICAL)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)

    voila_app.start()

def register_local_xpython():
    # 1. Discover the current Python path
    current_python = Path(sys.executable)
    venv_bin_dir = current_python.parent

    print(f"Detected Python at: {current_python}")

    # 2. Try to find the correct executable
    # Check for 'xpython' binary first, then fallback to the python launcher
    xpython_bin = venv_bin_dir / "xpython"

    if xpython_bin.exists():
        executable_path = [str(xpython_bin)]
    else:
        # Fallback: Use the python interpreter with the launcher module
        # This is exactly what your successful 'ps aux' showed earlier
        print(
            "⚠️ 'xpython' binary not found. Falling back to 'python -m xpython_launcher'"
        )
        executable_path = [str(current_python), "-m", "xpython_launcher"]

    # 3. Define destination
    kernel_dir = Path.home() / ".local/share/jupyter/kernels/xpython"
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

    print(f"✅ Registered kernelspec at: {kernel_json_path}")
    print(f"🚀 Using command: {' '.join(executable_path)}")

def patch_solara_comm():
    try:
        # 1. Find the site-packages directory for the current venv
        # getsitepackages() returns a list; usually index 0 is the primary one
        site_packages = site.getsitepackages()[0]
        comm_file = Path(site_packages) / "solara" / "comm.py"

        if not comm_file.exists():
            print(f"⚠️ Solara comm.py not found at {comm_file}. Skipping patch.")
            return

        # 2. Read the file content
        content = comm_file.read_text()

        # 3. Perform the equivalent of the 'sed' replacement
        target_str = "if comm is not None and comm.create_comm is comm._create_comm:"
        replacement_str = "if False:"

        if target_str in content:
            new_content = content.replace(target_str, replacement_str)
            # 4. Write it back
            comm_file.write_text(new_content)
            print(f"✅ Successfully patched: {comm_file}")
        elif replacement_str in content:
            print(f"ℹ️ Solara comm.py is already patched.")
        else:
            print(
                "⚠️ Could not find the target string in comm.py. The version might have changed."
            )

    except Exception as e:
        print(f"❌ Failed to patch Solara: {e}")