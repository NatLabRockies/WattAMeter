# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import asyncio
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_dir():
    """Creates a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_wattawait_waits_for_file_creation(temp_dir):
    """
    Tests that wattawait.sh waits until a non-existent file is created.
    """

    # Determine the project root based on the current file's location
    # and construct the path to the script. This makes the test independent
    # of the current working directory.
    # Assumes the test file is in <project_root>/tests/utils/
    project_root = Path(__file__).resolve().parent.parent.parent
    script_path = str(project_root / "src/wattameter/utils/wattawait.sh")

    log_file_path = temp_dir / "test_creation.log"
    assert not log_file_path.exists()

    # Start wattawait.sh in the background
    # New syntax: wattawait.sh [-q] [-f filepath] ID
    proc = await asyncio.create_subprocess_exec(
        script_path,
        "-f",
        str(log_file_path),
        "42",  # Arbitrary ID to pass to the script
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Give it a moment to start waiting
    await asyncio.sleep(2)

    # Create the file and write 'run 42', which should unblock wattawait.sh
    log_file_path.touch()
    with open(log_file_path, "w") as f:
        f.write("run 42\n")

    try:
        # Wait for wattawait.sh to finish
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
    except asyncio.TimeoutError:
        proc.terminate()
        await proc.communicate()
        pytest.fail("wattawait.sh did not terminate after file creation.")

    # Check that the script output indicates successful creation
    assert f"{log_file_path} is ready for run ID 42." in stdout.decode()


@pytest.mark.asyncio
async def test_wattawait_waits_for_file_update(temp_dir):
    """
    Tests that wattawait.sh waits until an existing file is updated.
    """

    # Determine the project root based on the current file's location
    # and construct the path to the script. This makes the test independent
    # of the current working directory.
    # Assumes the test file is in <project_root>/tests/utils/
    project_root = Path(__file__).resolve().parent.parent.parent
    script_path = str(project_root / "src/wattameter/utils/wattawait.sh")

    log_file_path = temp_dir / "test_update.log"

    # Create the file *before* starting wattawait.sh
    log_file_path.touch()
    # Wait a moment so the modification time is clearly in the past
    await asyncio.sleep(2)

    # Start wattawait.sh in the background
    # New syntax: wattawait.sh [-q] [-f filepath] ID
    proc = await asyncio.create_subprocess_exec(
        script_path,
        "-f",
        str(log_file_path),
        "42",  # Arbitrary ID to pass to the script
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Give it a moment to start waiting
    await asyncio.sleep(2)

    # Update the file, which should unblock wattawait.sh
    with open(log_file_path, "a") as f:
        f.write("run 42\n")

    try:
        # Wait for wattawait.sh to finish
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
    except asyncio.TimeoutError:
        proc.terminate()
        await proc.communicate()
        pytest.fail("wattawait.sh did not terminate after file update.")

    # Check that the script output indicates successful update
    assert f"{log_file_path} is ready for run ID 42." in stdout.decode()
