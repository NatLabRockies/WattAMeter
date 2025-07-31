#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
"""
Utility functions for the benchmarks
"""

import time


def print_system_info():
    """Print basic system information that might affect overhead."""
    import platform
    import cpuinfo
    import sys
    import pynvml

    print("=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    print(f"Platform: {platform.platform()}")
    print(f"Python version: {sys.version}")
    print(f"Architecture: {platform.architecture()}")
    print(f"Processor: {cpuinfo.get_cpu_info()['brand_raw']}")

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
    f, n_trials: int = 10, sleep_dt: float = 0.013, ntmax: int = 1000
) -> list[float]:
    """
    Estimates the average time interval between changes in the output of a given function.

    The function assumes that the value retrieved by `f` changes periodically
    and uses this change to estimate the time interval.

    :param f: A function that retrieves the current value to monitor for changes.
    :param n_trials: The number of trials to average the time interval over (default is 10).
    :param sleep_dt: The sleep duration between checks for value updates in seconds (default is 0.013).
    :param ntmax: The maximum number of sleep iterations to wait for a value update (default is 1000).

    :return: The estimated average time interval in seconds.

    :raises RuntimeError: If the value does not change within the maximum wait time.
    """
    # Value and time counters
    v1 = f()
    t1 = time.perf_counter()

    # Estimate the time interval
    res = [0.0] * n_trials
    n_computed_dt = 0
    for count in range(n_trials + 1):
        # Initialize the value and time counters
        v0 = v1
        t0 = t1

        # Wait for the value to change
        sanity_check = 0
        while sanity_check < ntmax and v1 == v0:
            time.sleep(sleep_dt)
            v1 = f()
            t1 = time.perf_counter()
            sanity_check += 1

        if sanity_check == ntmax:
            raise RuntimeError(
                "The value did not change after the maximum wait time. Please check the function."
            )

        # Update estimated time interval
        if count > 0:  # Skip the first trial to avoid initialization bias
            n_computed_dt += 1
            res[count - 1] = t1 - t0

    return res
