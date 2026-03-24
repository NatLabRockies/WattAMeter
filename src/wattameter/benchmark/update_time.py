#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC
"""
Frequency of Update Benchmark Script for WattAMeter

This script measures the frequency of updates for different metrics.
Since update frequency measurements are machine-dependent, this script is provided
as an example rather than as a test.

Usage:
    python update_time.py
"""

import statistics
import logging
import time
from functools import partial

from .utils import (
    estimate_dt,
    print_benchmark_banner,
    print_benchmark_footer,
    compile_gpu_burn,
    start_gpu_burn,
    stop_gpu_burn,
    start_cpu_stress,
    stop_cpu_stress,
)
from ..readers import RAPLReader, NVMLReader


def _benchmark_metric(metric_name, get_metric_func, unit, n_trials=100):
    """
    Helper function to benchmark a specific NVML metric.

    :param metric_name: Name of the metric being benchmarked
    :param get_metric_func: Function that returns the metric value
    :param unit: Unit of the metric (e.g., "mW", "mJ")
    :param n_trials: Number of trials to perform for estimating update time
    :raises RuntimeError: If the metric cannot be read or does not update
    """
    try:
        # Test initial reading
        initial_value = get_metric_func()
        print(f"   Initial {metric_name.lower()} reading: {initial_value} {unit}")

        # Estimate update frequency
        print(f"   🕐 Estimating {metric_name.lower()} update interval...")
        t0 = time.perf_counter()
        estimated_dt = estimate_dt(get_metric_func, n_trials=n_trials)
        t1 = time.perf_counter()

        freq = [1.0 / dt for dt in estimated_dt]
        min_freq = min(freq)
        max_freq = max(freq)
        median_freq = statistics.median(freq)
        mean_freq = len(estimated_dt) / (t1 - t0)

        print(f"   📈 Mean update frequency: {mean_freq:.6f} Hz")
        print(f"                     Median: {median_freq:.6f} Hz")
        print(f"                        Min: {min_freq:.6f} Hz")
        print(f"                        Max: {max_freq:.6f} Hz")

        # Provide context on update frequency
        if mean_freq > 100:  # < 10ms (> 100Hz)
            print("   💚 Very fast updates (< 10ms)")
        elif mean_freq > 10:  # < 100ms (> 10Hz)
            print("   ✅ Fast updates (< 100ms)")
        elif mean_freq > 1:  # < 1s (> 1Hz)
            print("   ⚠️  Moderate updates (< 1s)")
        else:  # >= 1s (<= 1Hz)
            print("   ⚠️  Slow updates (>= 1s)")

    except RuntimeError as e:
        print(f"   ❌ Failed to estimate {metric_name.lower()} update time: {e}")
        print(
            f"   💡 This might mean {metric_name.lower()} readings don't change or update very slowly"
        )


def benchmark_pynvml_update_time(gpu_burn_path=None, n_trials=100):
    """Benchmarks the update time of pynvml nvmlDeviceGetPowerUsage function using estimate_dt().

    :param gpu_burn_path: If not None, path to the gpu_burn executable
    :param n_trials: Number of trials to perform for estimating update time
    """
    print_benchmark_banner("PYNVML POWER USAGE UPDATE TIME BENCHMARK")

    nvml = NVMLReader()
    if len(nvml.tags) == 0:
        print("❌ No NVML devices found. Skipping benchmark.")
        return

    # Stress GPUs if gpu_burn is available
    gpu_burn_process = start_gpu_burn(gpu_burn_path, warmup_s=0.0)

    # Benchmark each GPU
    for gpu_id, _handle in enumerate(nvml.devices):
        print(f"\n🔍 Benchmarking GPU id: {gpu_id}")

        try:
            _benchmark_metric(
                "Energy Consumption",
                partial(nvml.read_energy_on_device, i=gpu_id),
                "mJ",
                n_trials=n_trials,
            )
        except RuntimeError as e:
            print(f"   ❌ Cannot get energy readings: {e}")

        try:
            _benchmark_metric(
                "Power Usage",
                partial(nvml.read_power_on_device, i=gpu_id),
                "mW",
                n_trials=n_trials,
            )
        except RuntimeError as e:
            print(f"   ❌ Cannot get power readings: {e}")

    # Terminate gpu_burn if it was started
    stop_gpu_burn(gpu_burn_process)


def benchmark_rapl_update_time(cpu_stress_test=False, n_trials=100, n: int = 0):
    """Benchmarks the update time of the RAPL files using estimate_dt().

    :param cpu_stress_test: If True, stress the CPU during the benchmark
    :param n_trials: Number of trials to perform for estimating update time
    :param n: Size of the square matrices to multiply for CPU stress test
        (ignored if cpu_stress_test is False). Set to 0 to use the default size.
    """
    print_benchmark_banner("RAPL POWER USAGE UPDATE TIME BENCHMARK")

    rapl = RAPLReader()
    if len(rapl.tags) == 0:
        print("❌ No RAPL devices found. Skipping benchmark.")
        return

    # Stress CPUs
    cpu_stress_process = None
    if cpu_stress_test:
        cpu_stress_process = start_cpu_stress(warmup_s=5.0, n=n)

    # Benchmark each RAPL file
    for rapl_file in rapl.devices:
        print(f"\n🔍 Benchmarking RAPL file: {rapl_file.path}")

        try:
            _benchmark_metric(
                "Energy Consumption",
                rapl_file.read_energy,
                "uJ",
                n_trials=n_trials,
            )
        except RuntimeError as e:
            print(f"   ❌ Cannot get energy readings: {e}")

    # Terminate CPU stress process
    stop_cpu_stress(cpu_stress_process)


def run_benchmark():
    import argparse
    import os

    logging.basicConfig(level=logging.INFO)

    print("WattAMeter Frequency of Update Benchmark")
    print("This script measures the frequency of update in different devices.")
    print("Results are machine-dependent and should be used for reference only.\n")

    parser = argparse.ArgumentParser(
        description="Benchmark the frequency of update of various WattAMeter components"
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=100,
        help="Number of trials to perform for estimating update times (default: 100)",
    )
    parser.add_argument(
        "--cpu-stress-test",
        action="store_true",
        help="Stress the CPUs to see how that affects update times",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=0,
        help="Size of the square matrices to multiply for CPU stress test (ignored if --cpu-stress-test is not set). Set to 0 to use the default size.",
    )
    parser.add_argument(
        "--gpu-burn-dir",
        type=str,
        default=None,
        help="Path to the gpu_burn benchmark to stress GPUs and see how that affects update times",
    )
    parser.add_argument(
        "--recompile-gpu-burn",
        action="store_true",
        help="Recompile gpu_burn before running the benchmark (requires CUDA toolkit)",
    )
    args = parser.parse_args()

    # Try compiling gpu_burn if needed
    gpu_burn_path = None
    if args.gpu_burn_dir is not None:
        gpu_burn_path = os.path.join(args.gpu_burn_dir, "gpu_burn")
        if args.recompile_gpu_burn or not os.path.isfile(gpu_burn_path):
            try:
                compile_gpu_burn(args.gpu_burn_dir)
            except Exception as e:
                print(f"❌ Failed to compile gpu_burn: {e}. Continuing with idle GPUs.")

    benchmark_pynvml_update_time(gpu_burn_path=gpu_burn_path, n_trials=args.n_trials)
    benchmark_rapl_update_time(
        cpu_stress_test=args.cpu_stress_test, n_trials=args.n_trials, n=args.n
    )

    print_benchmark_footer()


if __name__ == "__main__":
    run_benchmark()  # Call the benchmark runner
