# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import subprocess
from pathlib import Path
import tempfile
import pytest


@pytest.fixture
def temp_dir():
    """Creates a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_slurm_start_parses_output_dir_and_preserves_passthrough_args(temp_dir):
    """Tests that start_wattameter consumes output-dir and forwards remaining args."""
    project_root = Path(__file__).resolve().parent.parent.parent
    script_path = project_root / "src/wattameter/utils/slurm.sh"

    srun_args_file = temp_dir / "srun_args.txt"

    bash_snippet = f"""
source \"{script_path}\"
export SLURM_JOB_ID=12345
export SLURM_JOB_NUM_NODES=1
export SRUN_ARGS_FILE=\"{srun_args_file}\"
export FAKE_WATTAPATH=\"{temp_dir}\"

srun() {{
    echo __CALL__ >> \"$SRUN_ARGS_FILE\"
    printf '%s\\n' \"$@\" >> \"$SRUN_ARGS_FILE\"
}}

squeue() {{
    echo \"11111 wattameter.sh\"
}}

python() {{
    echo \"$FAKE_WATTAPATH\"
}}

start_wattameter -o logs -- --tracker 0.1,rapl --log-level debug
"""

    proc = subprocess.run(
        ["bash", "-c", bash_snippet],
        cwd=temp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert srun_args_file.exists()

    captured = srun_args_file.read_text()
    assert captured.count("--chdir=logs") == 2
    assert "--tracker" in captured
    assert "0.1,rapl" in captured
    assert "--log-level" in captured
    assert "debug" in captured


def test_slurm_start_supports_equals_output_dir_form(temp_dir):
    """Tests that --output-dir=... is accepted by start_wattameter."""
    project_root = Path(__file__).resolve().parent.parent.parent
    script_path = project_root / "src/wattameter/utils/slurm.sh"

    srun_args_file = temp_dir / "srun_args_equals.txt"

    bash_snippet = f"""
source \"{script_path}\"
export SLURM_JOB_ID=54321
export SLURM_JOB_NUM_NODES=1
export SRUN_ARGS_FILE=\"{srun_args_file}\"
export FAKE_WATTAPATH=\"{temp_dir}\"

srun() {{
    printf '%s\\n' \"$@\" >> \"$SRUN_ARGS_FILE\"
}}

squeue() {{
    echo \"22222 wattameter.sh\"
}}

python() {{
    echo \"$FAKE_WATTAPATH\"
}}

start_wattameter --output-dir=logs-eq
"""

    proc = subprocess.run(
        ["bash", "-c", bash_snippet],
        cwd=temp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert srun_args_file.exists()

    captured = srun_args_file.read_text()
    assert "--chdir=logs-eq" in captured
