#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
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

from wattameter.cli.main import main
from wattameter.utils.postprocessing import file_to_df


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


def benchmark_dynamic_overhead():
    """Call main() and let it run for a short time to measure dynamic overhead

    - Use a frequency of 10 Hz for writing data to disk
    - Use a temporary directory to avoid writing files to the current directory
    - Let it run for 10 seconds, then send a SIGINT to terminate
    - Mock the cli arguments to set dt_read to 0.1 seconds
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
        try:
            print("Starting dynamic overhead measurement...")
            print("Running for 60 seconds", end="")

            # Start the main function in a separate process
            main_process = multiprocessing.Process(target=main)
            main_process.start()

            # Let it run for 60 seconds
            sys.stdout.flush()  # Ensures each dot is printed immediately
            for _ in range(60):
                print(".", end="")
                sys.stdout.flush()  # Ensures each dot is printed immediately
                time.sleep(1)  # Pause for 1 seconds between dots
            print(" Done!")

            print("Terminating process...")
            # Send SIGINT to terminate the child process
            if main_process.pid:
                os.kill(main_process.pid, signal.SIGINT)

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
            # Restore the original working directory
            os.chdir(original_cwd)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("WattAMeter Overhead Benchmark Suite")

    benchmark_static_overhead()
    benchmark_dynamic_overhead()

    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print()
    print("Note: These measurements are indicative and will vary based on:")
    print("  - Hardware specifications")
    print("  - Available power monitoring interfaces")
    print("  - Background processes")
