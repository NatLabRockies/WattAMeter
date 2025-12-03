#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
"""
Utility functions for the benchmarks
"""

import time
import logging
import platform
import os
import subprocess
import re
import sys
import pynvml


logger = logging.getLogger(__name__)


def get_cpu_info():
    """Get basic CPU information.

    Source - https://stackoverflow.com/a/13078519
    Posted by dbn, modified by community. See post 'Timeline' for change history
    Retrieved 2025-12-03, License - CC BY-SA 4.0
    """

    if platform.system() == "Windows":
        return platform.processor()
    elif platform.system() == "Darwin":
        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + "/usr/sbin"
        command = "sysctl -n machdep.cpu.brand_string"
        return subprocess.check_output(command, shell=True).decode().strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).decode().strip()
        for line in all_info.split("\n"):
            if "model name" in line:
                return re.sub(".*model name.*:", "", line, 1)
    return ""


def print_system_info():
    """Print basic system information that might affect overhead."""
    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    print(f"Platform: {platform.platform()}")
    print(f"Python version: {sys.version}")
    print(f"Architecture: {platform.architecture()}")
    print(f"Processor: {get_cpu_info()}")

    try:
        pynvml.nvmlInit()
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            if hasattr(name, "decode"):
                name = name.decode("utf-8")
            print(f"GPU: {name}")
        except pynvml.NVMLError as e:
            print(f"GPU: Error retrieving GPU info - {e}")
        finally:
            pynvml.nvmlShutdown()
    except pynvml.NVMLError:
        pass  # NVML not available, skip GPU info


def estimate_dt(
    f, n_trials: int = 10, sleep_dt: float = 0.0001, ntmax: int = 1000
) -> list[float]:
    """
    Estimates the average time interval between changes in the output of a given function.

    The function assumes that the value retrieved by `f` changes periodically
    and uses this change to estimate the time interval.

    :param f: A function that retrieves the current value to monitor for changes.
    :param n_trials: The number of trials to average the time interval over (default is 10).
    :param sleep_dt: The sleep duration between checks for value updates in seconds (default is 0.0001).
    :param ntmax: The maximum number of sleep iterations to wait for a value update (default is 1000).

    :return: The estimated average time interval in seconds.

    :raises RuntimeError: If the value does not change within the maximum wait time.
    """
    # Value and time counters
    v1 = f()
    logger.debug(f"Initial value: {v1}")
    t1 = time.perf_counter_ns()

    # Estimate the time interval
    res = [0.0] * n_trials
    n_computed_dt = 0
    for count in range(n_trials + 1):
        logger.debug(f"Trial {count + 1}/{n_trials}")

        # Initialize the value and time counters
        v0 = v1
        t0 = t1

        # Wait for the value to change
        sanity_check = 0
        while sanity_check < ntmax and v1 == v0:
            time.sleep(sleep_dt)

            v1 = f()
            logger.debug(f"Polled value: {v1}")
            t1 = time.perf_counter_ns()

            sanity_check += 1

        if sanity_check == ntmax:
            raise RuntimeError(
                "The value did not change after the maximum wait time. Please check the function."
            )

        # Update estimated time interval
        if count > 0:  # Skip the first trial to avoid initialization bias
            res[n_computed_dt] = (t1 - t0) * 1e-9  # Convert ns to seconds
            n_computed_dt += 1
            logger.debug(f"Computed dt: {res[n_computed_dt - 1]} seconds")

    return res[:n_computed_dt]


def stress_cpu(n: int = 9999):
    """Function to stress the CPU by performing large matrix multiplications.

    https://www.reddit.com/r/overclocking/comments/1ckvr0w/comment/l2psl0j/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button

    :param n: Number of matrix multiplications to perform.
    """
    try:
        import numpy as np

        m1 = np.random.randn(8192, 8192)
        m2 = np.random.randn(8192, 8192)
        for i in range(n):
            np.linalg.norm(np.dot(m1, m2))
    except ImportError:
        logger.warning("numpy not available. Skipping CPU stress test.")
        return


def compile_gpu_burn(gpu_burn_dir):
    """Compiles the gpu_burn benchmark and returns the path to the executable.

    :param gpu_burn_dir: Path to the gpu_burn benchmark directory.
    :return: Path to the compiled gpu_burn executable.
    """

    # Check CUDA_HOME
    cuda_home = os.environ.get("CUDA_HOME") or os.environ.get("CUDA_PATH")
    if not cuda_home or cuda_home == "":
        logger.warning("CUDA_HOME or CUDA_PATH environment variable not set.")
        cuda_home = ""
    else:
        cuda_home = "CUDAPATH=" + cuda_home

    # Get NVIDIA compute capability
    nvidia_cap = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
        cwd=gpu_burn_dir,
        text=True,  # Decodes output as text
    ).strip()

    # Compile gpu_burn
    logger.info(f"Compiling gpu_burn in {gpu_burn_dir} benchmark...")
    subprocess.run(
        ["make", "-j4", "clean"],
        cwd=gpu_burn_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["make", "-j4", cuda_home, "COMPUTE=" + nvidia_cap],
        cwd=gpu_burn_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    logger.info("gpu_burn compiled successfully.")
    return os.path.join(gpu_burn_dir, "gpu_burn")
