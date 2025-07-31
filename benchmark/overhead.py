#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
"""
Overhead Benchmark Script for WattAMeter

This script measures the performance overhead introduced by the PowerTracker.
Since overhead measurements are machine-dependent, this script is provided
as an example rather than as a test.

Usage:
    python overhead.py
"""

import time
from wattameter.power_tracker import PowerTracker
import tempfile
from pathlib import Path


def create_default_tracker(temp_dir, measure_power_secs: float = 1):
    """Creates a default PowerTracker instance for benchmarking."""
    tracker = PowerTracker(
        # For CO2 emissions tracking
        country_iso_code="USA",
        region="colorado",
        # For power tracking
        measure_power_secs=measure_power_secs,
        # For recording data
        log_level="warning",
        # For saving power and energy data to file
        api_call_interval=3600,  # 1 hour in seconds
        output_dir=str(temp_dir),
        output_file="emissions.csv",
        output_power_file="power.log",
    )
    return tracker


def benchmark_initialization_overhead(iterations: int = 5):
    """Measures the overhead of initializing and destroying the PowerTracker."""
    print("=" * 60)
    print("POWERTRACKER INITIALIZATION OVERHEAD BENCHMARK")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)

        # Measure multiple iterations for better accuracy
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


def benchmark_measurement_overhead(num_measurements: int = 50):
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


def _get_rapl_files() -> list[str]:
    """Returns a list of RAPL files (if any) in the system."""
    try:
        from codecarbon.core.cpu import IntelRAPL

        rapl = IntelRAPL()
        return [rapl_file.path for rapl_file in rapl._rapl_files]
    except (FileNotFoundError, ImportError, SystemError, PermissionError) as e:
        print(f"❌ IntelRAPL not available. Skipping benchmark. Error: {e}")
        return []


def _read_rapl_energy(files: list, dt: float) -> list[float]:
    """Reads a RAPL file and returns the energy in uJ."""
    dE = []
    for f in files:
        f.seek(0)
        dE.append(float(f.read().strip()))
    time.sleep(dt)
    for i, f in enumerate(files):
        f.seek(0)
        dE[i] = float(f.read().strip()) - dE[i]
        if dE[i] < 0:
            return _read_rapl_energy(files, dt)
    return [x / 1e6 for x in dE]  # Convert to J


def benchmark_measurement_cpu_energy_overhead(T: float = 10):
    """Measures the CPU energy added by the PowerTracker's measurement function."""
    print("\n" + "=" * 60)
    print("POWERTRACKER MEASUREMENT CPU ENERGY OVERHEAD BENCHMARK")
    print("=" * 60)

    # Get RAPL files
    rapl_files = _get_rapl_files()
    print(f"Found {len(rapl_files)} RAPL files: {rapl_files}")

    # Open RAPL files to read energy consumption
    rapl_f = [open(f, "r") for f in rapl_files]

    # Measure idle energy consumption
    print("Measuring idle energy consumption...")
    idle_energy = _read_rapl_energy(rapl_f, dt=T)
    print(f"Idle energy consumption: {idle_energy} J in {T} seconds")

    for dt in [0.1, 0.5, 1.0]:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            print(f"Measuring energy consumed by PowerTracker (freq={int(1 / dt)}Hz)")

            tracker = create_default_tracker(temp_dir, measure_power_secs=dt)
            tracker.start()

            # Measure energy consumption during PowerTracker operation
            overhead_energy = _read_rapl_energy(rapl_f, dt=T)

            tracker.stop()

            print(
                f"PowerTracker+Idle energy consumption: {overhead_energy} J in {T} seconds"
            )

            overhead_energy = [
                max(e - i, 0) for e, i in zip(overhead_energy, idle_energy)
            ]
            overhead_power = [e / T for e in overhead_energy]

            print(
                f"Energy consumed by PowerTracker: {overhead_energy} J in {T} seconds"
            )

            rel_overhead_energy = [e / i for e, i in zip(overhead_energy, idle_energy)]
            print(
                f"Energy consumed relative to idle: {rel_overhead_energy} J in {T} seconds"
            )
            print(f"Average power overhead: {overhead_power} W")

    # Close RAPL files
    for f in rapl_f:
        f.close()


if __name__ == "__main__":
    print("WattAMeter Overhead Benchmark")
    print("This script measures the performance overhead of PowerTracker.")
    print("Results are machine-dependent and should be used for reference only.\n")

    benchmark_initialization_overhead()
    benchmark_measurement_overhead()
    benchmark_measurement_cpu_energy_overhead()

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print("Note: These measurements are indicative and will vary based on:")
    print("- Hardware specifications")
    print("- System load")
    print("- Available power monitoring interfaces")
    print("- Background processes")
