# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import subprocess
import os
import time
import signal
from pathlib import Path
import tempfile
import pytest


@pytest.fixture
def temp_dir():
    """Creates a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_wattameter_sh_execution_and_termination(temp_dir):
    """
    Tests the basic execution of the wattameter.sh script and its graceful termination.
    """

    # Determine the project root based on the current file's location
    # and construct the path to the script. This makes the test independent
    # of the current working directory.
    # Assumes the test file is in <project_root>/tests/utils/
    project_root = Path(__file__).resolve().parent.parent.parent
    script_path = project_root / "src/wattameter/utils/wattameter.sh"

    run_id = "pytest_shell_test"

    # With the new script, when -i is provided, the log file will be:
    # wattameter-{run_id}-{hostname}.txt
    import socket

    hostname = socket.gethostname()
    log_file_name = f"wattameter-{run_id}-{hostname}.txt"
    log_file_path = temp_dir / log_file_name

    # Start the script as a background process
    process = subprocess.Popen(
        [script_path, "-i", run_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # Create a new process group
        cwd=temp_dir,
    )

    # Allow some time for the script to initialize
    time.sleep(10)

    # If the process has already terminated, check the log file and exit
    if process.poll() is not None:
        assert log_file_path.exists(), f"Log file '{log_file_path}' was not created."
        with open(log_file_path, "r") as f:
            assert "No valid readers available" in f.read()

        return

    # Send a SIGTERM signal to the entire process group
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    # Wait for the process to complete
    stdout, stderr = process.communicate(timeout=5)

    # Check that the log file was created
    assert log_file_path.exists(), f"Log file '{log_file_path}' was not created."

    # Check the log file content (basic check)
    with open(log_file_path, "r") as _:
        pass  # Just ensure we can open it without error

    # Check stderr for unexpected errors
    stderr_str = stderr.decode()
    assert "No such file or directory" not in stderr_str
    assert "command not found" not in stderr_str

    # The "interrupted" message is expected from the script's trap
    stdout_str = stdout.decode()
    assert "WattAMeter interrupted" in stdout_str
    assert "WattAMeter has been terminated" in stdout_str
