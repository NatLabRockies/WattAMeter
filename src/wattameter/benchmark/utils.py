#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC
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
import multiprocessing
import pynvml


logger = logging.getLogger(__name__)


def print_benchmark_banner(title: str):
    """Print a standardized benchmark section banner."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_benchmark_footer():
    """Print a standardized benchmark completion footer."""
    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print("Note: These measurements are indicative and will vary based on:")
    print("- Hardware specifications")
    print("- System load")
    print("- Available power monitoring interfaces")
    print("- Background processes")


def start_gpu_burn(gpu_burn_path, warmup_s: float = 0.0):
    """Optionally compile and start gpu_burn, returning the spawned process or None.

    :param gpu_burn_path: Path to gpu_burn executable, or None to skip starting gpu_burn
    :param warmup_s: Time in seconds to wait after starting gpu_burn before returning
    :return: The subprocess.Popen object for the gpu_burn process, or None if not started
    """
    if gpu_burn_path is None:
        return None

    try:
        print("🔥 Starting gpu_burn to stress GPUs...")
        gpu_burn_process = subprocess.Popen(
            [gpu_burn_path, "3600"],
            cwd=os.path.dirname(gpu_burn_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(warmup_s)
        print("✅ gpu_burn started successfully")
        return gpu_burn_process
    except Exception as e:
        print(f"⚠️  Could not start gpu_burn: {e}. Continuing with idle GPUs.")
        return None


def stop_gpu_burn(gpu_burn_process):
    """Terminate gpu_burn if it was started.

    :param gpu_burn_process: The subprocess.Popen object for the gpu_burn process, or None if not started
    """
    if gpu_burn_process is None:
        return

    if gpu_burn_process.poll() is None:  # Check if the process is still running
        print("\n🛑 Terminating gpu_burn...")
        gpu_burn_process.terminate()
        gpu_burn_process.wait()
        print("✅ gpu_burn terminated")
    else:
        print("⚠️  gpu_burn process was not alive at termination time")


def start_cpu_stress(warmup_s: float = 5.0, n: int = 0):
    """Start the CPU stress process and return it, or None if startup fails.

    :param warmup_s: Time in seconds to wait after starting the CPU stress before returning
    :param n: Size of the square matrices to multiply.
    :return: The multiprocessing.Process object for the CPU stress process, or None if not started
    """
    try:
        stress_cpu_args = []
        if n > 0:
            stress_cpu_args.append(n)

        print("🔥 Starting CPU stress process...")
        cpu_stress_process = multiprocessing.Process(
            target=stress_cpu, args=tuple(stress_cpu_args)
        )
        cpu_stress_process.start()
        time.sleep(warmup_s)
        print("✅ CPU stress process started successfully")
        return cpu_stress_process
    except Exception as e:
        print(f"⚠️  Could not start CPU stress process: {e}. Continuing with idle CPUs.")
        return None


def stop_cpu_stress(cpu_stress_process):
    """Terminate the CPU stress process if it was started.

    :param cpu_stress_process: The multiprocessing.Process object for the CPU stress process, or None if not started
    """
    if cpu_stress_process is None:
        return

    if cpu_stress_process.is_alive():
        print("\n🛑 Terminating CPU stress process...")
        cpu_stress_process.terminate()
        cpu_stress_process.join()
        print("✅ CPU stress process terminated")
    else:
        print("⚠️  CPU stress process was not alive at termination time")


def _get_numpy():
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover - error path
        raise ImportError(
            "WattAMeter optional dependency 'numpy' is required for benchmarks. "
            "Install it with `pip install wattameter[benchmark]` or `pip install numpy`. "
            f"Original error: {exc}"
        )
    return np


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
    f, n_trials: int = 10, sleep_dt: float = 0.0001, ntmax: int = 100000
) -> list[float]:
    """
    Estimates the average time interval between changes in the output of a given function.

    The function assumes that the value retrieved by `f` changes periodically
    and uses this change to estimate the time interval.

    :param f: A function that retrieves the current value to monitor for changes.
    :param n_trials: The number of trials to average the time interval over (default is 10).
    :param sleep_dt: The sleep duration between checks for value updates in seconds (default is 0.0001).
    :param ntmax: The maximum number of sleep iterations to wait for a value update (default is 100000).

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


def stress_cpu(n: int = 8192):
    """Function to stress the CPU by performing large matrix multiplications.

    https://www.reddit.com/r/overclocking/comments/1ckvr0w/comment/l2psl0j/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button

    :param n: Size of the square matrices to multiply.
    """
    np = _get_numpy()

    m1 = np.random.randn(n, n)
    m2 = np.random.randn(n, n)

    i = 0
    while True:
        np.linalg.norm(np.dot(m1, m2))
        i += 1


def compile_gpu_burn(gpu_burn_dir):
    """Compiles the gpu_burn benchmark and returns the path to the executable.

    :param gpu_burn_dir: Path to the gpu_burn benchmark directory.
    :return: Path to the compiled gpu_burn executable.
    """

    # Get CUDA path
    cuda_home = os.environ.get("CUDA_HOME") or os.environ.get("CUDA_PATH")
    if not cuda_home or cuda_home == "":
        logger.warning("CUDA_HOME or CUDA_PATH environment variable not set.")
        make_args = []
    else:
        make_args = ["CUDAPATH=" + cuda_home]

    # Get CUDA version if nvcc is available
    try:
        cuda_version_output = subprocess.check_output(
            ["nvcc", "--version"], text=True
        ).strip()
        cuda_version_match = re.search(r"release (\d+\.\d+)", cuda_version_output)
        if cuda_version_match:
            cuda_version = cuda_version_match.group(1)
            make_args.append("CUDA_VERSION=" + cuda_version)
        else:
            logger.warning("Could not parse CUDA version from nvcc output.")
    except Exception as e:
        logger.warning(f"Could not determine CUDA version: {e}")

    # Get NVIDIA compute capability
    nvidia_caps = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
        text=True,  # Decodes output as text
    ).splitlines()
    unique_caps = sorted(set(c.strip() for c in nvidia_caps if c.strip()))
    if len(unique_caps) > 0:
        nvidia_cap = unique_caps[0]
        make_args.append("COMPUTE=" + nvidia_cap)
    else:
        nvidia_cap = None

    # Compile gpu_burn
    logger.info(f"Compiling gpu_burn in {gpu_burn_dir} benchmark...")
    subprocess.run(["make", "clean"], cwd=gpu_burn_dir, check=True, capture_output=True)
    subprocess.run(
        ["make"] + make_args, cwd=gpu_burn_dir, check=True, capture_output=True
    )
    gpu_burn_path = os.path.join(gpu_burn_dir, "gpu_burn")

    # Test gpu_burn executable
    result = subprocess.run(
        [gpu_burn_path, "1"], cwd=gpu_burn_dir, capture_output=True, text=True
    )
    if (
        result.returncode != 0
        and "the provided PTX was compiled with an unsupported toolchain"
        in result.stderr
        and nvidia_cap is not None
    ):
        # Build a SASS cubin for this GPU and place it at compare.ptx.
        # The loader inspects the binary contents, so keeping the legacy filename
        # preserves default runtime behavior (`./gpu_burn`) while avoiding PTX JIT issues.
        nvidia_cap_plain = nvidia_cap.replace(".", "")
        subprocess.run(
            [
                "nvcc",
                "-gencode",
                f"arch=compute_{nvidia_cap_plain},code=sm_{nvidia_cap_plain}",
                "-cubin",
                "compare.cu",
                "-o",
                "compare.ptx",
            ],
            cwd=gpu_burn_dir,
            check=True,
            capture_output=True,
        )
        # Retry gpu_burn with the new cubin in place
        subprocess.run(
            [gpu_burn_path, "1"], cwd=gpu_burn_dir, check=True, capture_output=True
        )

    logger.info("gpu_burn compiled successfully.")
    return gpu_burn_path
