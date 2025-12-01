#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
"""
Overhead of using WattAMeter
"""

import logging
import time
import multiprocessing
import subprocess
import signal
import tempfile
import os
import sys
from unittest import mock

from ..cli.main import main
from ..utils import file_to_df
from .utils import compile_gpu_burn, stress_cpu


def benchmark_static_overhead():
    """Call main() and exit as soon as BaseTracker::track_until_forced_exit is reached

    - Use mock to replace BaseTracker::track_until_forced_exit with a function that just returns
    - Use a temporary directory to avoid writing files to the current directory

    :return: static overhead in seconds
    """

    print()
    print("=" * 60)
    print("STATIC WATTAMETER CLI OVERHEAD BENCHMARK")
    print("=" * 60)

    with (
        tempfile.TemporaryDirectory() as temp_dir,
        mock.patch(
            "argparse.ArgumentParser.parse_args",
            return_value=mock.MagicMock(
                suffix=None,
                id="benchmark_run",
                dt_read=0.1,
                freq_write=3600,
                log_level="INFO",
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


def benchmark_dynamic_overhead(cpu_stress_test=False, gpu_burn_dir=None):
    """Call main() and let it run for a short time to measure dynamic overhead

    - Use a frequency of 10 Hz for writing data to disk
    - Use a temporary directory to avoid writing files to the current directory
    - Let it run for 10 seconds, then send a SIGINT to terminate
    - Mock the cli arguments to set dt_read to 0.1 seconds

    :param cpu_stress_test: If True, stress the CPU during the benchmark
    :param gpu_burn_dir: If not None, path to the gpu_burn benchmark
    """

    print()
    print("=" * 60)
    print("DYNAMIC WATTAMETER CLI OVERHEAD BENCHMARK")
    print("=" * 60)

    with (
        tempfile.TemporaryDirectory() as temp_dir,
        mock.patch(
            "argparse.ArgumentParser.parse_args",
            return_value=mock.MagicMock(
                suffix=None,
                id="benchmark_run",
                dt_read=0.1,
                freq_write=3600,
                log_level="INFO",
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
            if gpu_burn_dir is not None:
                try:
                    gpu_burn_path = compile_gpu_burn(gpu_burn_dir)
                    print("\n🔥 Starting gpu_burn to stress GPUs...")
                    gpu_burn_process = subprocess.Popen(
                        [gpu_burn_path, "3600"],
                        cwd=gpu_burn_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(10)  # Give it some time to start
                    print("✅ gpu_burn started successfully")
                except Exception as e:
                    print(
                        f"\n⚠️  Could not start gpu_burn: {e}. Continuing with idle GPUs."
                    )

            # Stress CPUs if requested
            if cpu_stress_test:
                try:
                    print("\n🔥 Starting stressing CPUs...")
                    cpu_stress_process = multiprocessing.Process(target=stress_cpu)
                    cpu_stress_process.start()
                    time.sleep(5)  # Give it some time to start
                    print("✅ cpu_stress_process started successfully")
                except Exception as e:
                    print(
                        f"\n⚠️  Could not start CPU stress process: {e}. Continuing with idle CPUs."
                    )

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
                        dt = (
                            df.index[1:-1]  # avoid edge effects
                            .to_series()
                            .diff()
                            .dropna()
                            .mean()
                            .total_seconds()
                        )
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
            if gpu_burn_process is not None:
                print("\n🛑 Terminating gpu_burn...")
                gpu_burn_process.terminate()
                gpu_burn_process.wait()
                print("✅ gpu_burn terminated")

            # Terminate CPU stress process
            if cpu_stress_process is not None:
                print("\n🛑 Terminating CPU stress process...")
                cpu_stress_process.terminate()
                cpu_stress_process.join()
                print("✅ CPU stress process terminated")

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
        type=bool,
        default=False,
        help="If True, stress the CPU during the dynamic overhead benchmark",
    )
    parser.add_argument(
        "--gpu-burn-dir",
        type=str,
        default=None,
        help="If provided, path to the gpu_burn benchmark to stress GPUs during the dynamic overhead benchmark",
    )
    args = parser.parse_args()

    benchmark_static_overhead()
    benchmark_dynamic_overhead(args.cpu_stress_test, args.gpu_burn_dir)

    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print()
    print("Note: These measurements are indicative and will vary based on:")
    print("  - Hardware specifications")
    print("  - Available power monitoring interfaces")
    print("  - Background processes")


if __name__ == "__main__":
    run_benchmark()  # Call the benchmark runner
