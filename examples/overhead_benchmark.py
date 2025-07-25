#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
"""
Overhead Benchmark Script for WattAMeter

This script measures the performance overhead introduced by the PowerTracker.
Since overhead measurements are machine-dependent, this script is provided
as an example rather than as a test.

Usage:
    python overhead_benchmark.py
"""

import time
from wattameter.power_tracker import PowerTracker
import tempfile
from pathlib import Path


def create_default_tracker(temp_dir):
    """Creates a default PowerTracker instance for benchmarking."""
    tracker = PowerTracker(
        # For CO2 emissions tracking
        country_iso_code="USA",
        region="colorado",
        # For power tracking
        measure_power_secs=1,
        # For recording data
        log_level="warning",
        # For saving power and energy data to file
        api_call_interval=3600,  # 1 hour in seconds
        output_dir=str(temp_dir),
        output_file="emissions.csv",
        output_power_file="power.log",
    )
    return tracker


def benchmark_initialization_overhead():
    """Measures the overhead of initializing and destroying the PowerTracker."""
    print("=" * 60)
    print("POWERTRACKER INITIALIZATION OVERHEAD BENCHMARK")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)

        # Measure multiple iterations for better accuracy
        iterations = 5
        total_time = 0

        for i in range(iterations):
            start_time = time.perf_counter()

            tracker = create_default_tracker(temp_dir)
            tracker.start()
            tracker.stop()
            del tracker

            end_time = time.perf_counter()
            iteration_time = end_time - start_time
            total_time += iteration_time

            print(f"Iteration {i + 1}: {iteration_time:.6f} seconds")

        average_overhead = total_time / iterations
        print(f"\nAverage initialization overhead: {average_overhead:.6f} seconds")
        print(f"Total time for {iterations} iterations: {total_time:.6f} seconds")

        # Provide context on what constitutes reasonable overhead
        if average_overhead < 0.1:
            print("✅ Overhead is excellent (< 0.1s)")
        elif average_overhead < 1.0:
            print("✅ Overhead is good (< 1.0s)")
        elif average_overhead < 10.0:
            print("⚠️  Overhead is acceptable (< 10.0s)")
        else:
            print("❌ Overhead might be too high (> 10.0s)")


def benchmark_measurement_overhead():
    """Measures the overhead of the PowerTracker's measurement function."""
    print("\n" + "=" * 60)
    print("POWERTRACKER MEASUREMENT OVERHEAD BENCHMARK")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)

        tracker = create_default_tracker(temp_dir)
        tracker.start()

        # Stop schedulers to avoid interference with measurements
        if tracker._scheduler:
            tracker._scheduler.stop()
        if tracker._scheduler_monitor_power:
            tracker._scheduler_monitor_power.stop()

        # Measure multiple measurements for better accuracy
        num_measurements = 50

        print(f"Performing {num_measurements} power measurements...")

        start_time = time.perf_counter()
        for i in range(num_measurements):
            tracker._measure_power_and_energy()
        end_time = time.perf_counter()

        tracker.stop()

        total_time = end_time - start_time
        average_measurement_overhead = total_time / num_measurements

        print(
            f"Total time for {num_measurements} measurements: {total_time:.6f} seconds"
        )
        print(
            f"Average measurement overhead: {average_measurement_overhead:.6f} seconds"
        )

        # Provide context on what constitutes reasonable measurement overhead
        if average_measurement_overhead < 0.001:
            print("✅ Measurement overhead is excellent (< 1ms)")
        elif average_measurement_overhead < 0.01:
            print("✅ Measurement overhead is good (< 10ms)")
        elif average_measurement_overhead < 0.1:
            print("⚠️  Measurement overhead is acceptable (< 100ms)")
        else:
            print("❌ Measurement overhead might be too high (> 100ms)")


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


if __name__ == "__main__":
    print("WattAMeter Overhead Benchmark")
    print("This script measures the performance overhead of PowerTracker.")
    print("Results are machine-dependent and should be used for reference only.\n")

    print_system_info()
    benchmark_initialization_overhead()
    benchmark_measurement_overhead()

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print("Note: These measurements are indicative and will vary based on:")
    print("- Hardware specifications")
    print("- System load")
    print("- Available power monitoring interfaces")
    print("- Background processes")
