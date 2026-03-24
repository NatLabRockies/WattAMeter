#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC
"""
Overhead of using WattAMeter
"""

import logging
import time
import multiprocessing
import signal
import tempfile
import os
import sys
from unittest import mock

from ..cli.main import main
from ..utils import file_to_df
from .utils import (
    print_benchmark_banner,
    print_benchmark_footer,
    compile_gpu_burn,
    start_gpu_burn,
    stop_gpu_burn,
    start_cpu_stress,
    stop_cpu_stress,
)


def benchmark_static_overhead():
    """Call main() and exit as soon as BaseTracker::track_until_forced_exit is reached

    - Use mock to replace BaseTracker::track_until_forced_exit with a function that just returns
    - Use a temporary directory to avoid writing files to the current directory

    :return: static overhead in seconds
    """

    print_benchmark_banner("STATIC WATTAMETER CLI OVERHEAD BENCHMARK")

    with (
        tempfile.TemporaryDirectory() as temp_dir,
        mock.patch(
            "argparse.ArgumentParser.parse_args",
            return_value=mock.MagicMock(
                suffix=None,
                id="benchmark_run",
                tracker=None,
                freq_write=3600,
                log_level="INFO",
                output_dir=temp_dir,
                mqtt_broker=None,
            ),
        ),
        mock.patch(
            "wattameter.tracker.BaseTracker.track_until_forced_exit",
            return_value=None,
        ),
    ):
        # Change the current working directory to the temporary one
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            print("Starting static overhead measurement...")
            t0 = time.perf_counter_ns()
            main()
            t1 = time.perf_counter_ns()
            static_overhead = (t1 - t0) / 1e9  # Convert to seconds
            print(f"\nStatic overhead: {static_overhead:.6f} seconds")
        finally:
            # Restore the original working directory
            os.chdir(original_cwd)

    return static_overhead


def benchmark_dynamic_overhead(cpu_stress_test=False, gpu_burn_path=None, n: int = 0):
    """Call main() and let it run for a short time to measure dynamic overhead

    - Use a frequency of 10 Hz for writing data to disk
    - Use a temporary directory to avoid writing files to the current directory
    - Let it run for 10 seconds, then send a SIGINT to terminate
    - Mock the cli arguments to set dt_read to 0.1 seconds

    :param cpu_stress_test: If True, stress the CPU during the benchmark
    :param gpu_burn_path: If not None, path to the gpu_burn executable
    :param n: Size of the square matrices to multiply for CPU stress test
        (ignored if cpu_stress_test is False). Set to 0 to use the default size.
    """

    print_benchmark_banner("DYNAMIC WATTAMETER CLI OVERHEAD BENCHMARK")

    with (
        tempfile.TemporaryDirectory() as temp_dir,
        mock.patch(
            "argparse.ArgumentParser.parse_args",
            return_value=mock.MagicMock(
                suffix=None,
                id="benchmark_run",
                tracker=None,
                freq_write=3600,
                log_level="INFO",
                output_dir=temp_dir,
                mqtt_broker=None,
            ),
        ),
    ):
        # Change the current working directory to the temporary one
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        gpu_burn_process = None
        cpu_stress_process = None
        try:
            print("Starting dynamic overhead measurement...")
            print("Running for 60 seconds", end="")

            # Stress GPUs if gpu_burn is available
            gpu_burn_process = start_gpu_burn(gpu_burn_path, warmup_s=5.0)

            # Stress CPUs if requested
            if cpu_stress_test:
                cpu_stress_process = start_cpu_stress(warmup_s=5.0, n=n)

            # Start the main function in a separate process
            main_process = multiprocessing.Process(target=main)
            main_process.start()

            # Let it run for 60 seconds
            sys.stdout.flush()  # Ensures each dot is printed immediately
            for _ in range(60):
                print(".", end="")
                sys.stdout.flush()  # Ensures each dot is printed immediately
                time.sleep(1)  # Pause for 1 seconds between dots
                if not main_process.is_alive():
                    break
            print(" Done!")

            # Send SIGINT to terminate the child process
            print("Terminating process...")
            if main_process.is_alive() and main_process.pid:
                try:
                    os.kill(main_process.pid, signal.SIGINT)
                except OSError:
                    # process may have exited between checks
                    pass

            # Wait for the main process to finish
            main_process.join()
            print("Process terminated.")

            # Read output files
            print("Analyzing results...")
            for filename in os.listdir(temp_dir):
                if filename.endswith("_wattameter.log"):
                    print(f"\nReading output file: {filename}")
                    with open(os.path.join(temp_dir, filename), "r") as f:
                        df = file_to_df(f)
                        mean_delta = (
                            df.index[1:-1]  # avoid edge effects
                            .to_series()
                            .diff()
                            .dropna()
                            .mean()
                        )
                        try:
                            dt = mean_delta.total_seconds()  # type: ignore[attr-defined]
                        except AttributeError:
                            dt = float(mean_delta)
                        desc = df["reading-time[ns]"].describe()
                        print("Reading time statistics (nanoseconds):")
                        for stat, value in desc.items():
                            if stat in ["count", "min", "25%", "50%", "75%", "max"]:
                                print(f"  {stat:>8}: {int(value):,}")
                            else:
                                print(f"  {stat:>8}: {value:,.2f}")
                        print(
                            f"Average of {df['reading-time[ns]'].mean():,.2f} ns every {dt} s"
                        )
        finally:
            # Terminate gpu_burn if it was started
            stop_gpu_burn(gpu_burn_process)

            # Terminate CPU stress process
            stop_cpu_stress(cpu_stress_process)

            # Restore the original working directory
            os.chdir(original_cwd)


def run_benchmark():
    import argparse

    logging.basicConfig(level=logging.INFO)

    print("WattAMeter Overhead Benchmark Suite")

    parser = argparse.ArgumentParser(
        description="Benchmark the overhead of using WattAMeter"
    )
    parser.add_argument(
        "--cpu-stress-test",
        action="store_true",
        help="Stress the CPUs during the dynamic overhead benchmark",
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
        help="Path to the gpu_burn benchmark to stress GPUs during the dynamic overhead benchmark",
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

    benchmark_static_overhead()
    benchmark_dynamic_overhead(
        cpu_stress_test=args.cpu_stress_test, gpu_burn_path=gpu_burn_path, n=args.n
    )

    print_benchmark_footer()


if __name__ == "__main__":
    run_benchmark()  # Call the benchmark runner
