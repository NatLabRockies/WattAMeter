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


def _get_rapl_domain_name(rapl_file: str) -> str:
    """Extract a readable domain name from RAPL file path by reading the name file."""
    import os
    import re

    # Extract directory path from energy_uj file path
    # e.g., '/sys/class/powercap/intel-rapl/subsystem/intel-rapl:0/energy_uj' -> '/sys/class/powercap/intel-rapl/subsystem/intel-rapl:0'
    rapl_dir = os.path.dirname(rapl_file)

    # If the path ends in a pattern like :<number>:<number>
    if re.search(r":\d+:\d+$", rapl_dir):
        # Remove the last part after the last colon
        parent_rapl_component_dir = re.sub(r":\d+$", "", rapl_dir)
        domain_name = (
            _get_rapl_domain_name(os.path.join(parent_rapl_component_dir, "energy_uj"))
            + "-"
        )
    else:
        domain_name = ""

    try:
        # Read the actual domain name from the 'name' file
        with open(os.path.join(rapl_dir, "name"), "r") as f:
            domain_name += f.read().strip()

    except (FileNotFoundError, PermissionError, OSError):
        # Fallback to extracting from path if name file is not readable
        last_digit = re.search(r"\d+$", rapl_dir)
        if last_digit:
            domain_name += last_digit[0]
        else:
            domain_name += "unkknown"

    return domain_name


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


def benchmark_measurement_cpu_energy_overhead(T: float = 60):
    """Measures the CPU energy added by the PowerTracker's measurement function."""
    print("\n" + "=" * 60)
    print("POWERTRACKER MEASUREMENT CPU ENERGY OVERHEAD BENCHMARK")
    print("=" * 60)

    # Get RAPL files
    rapl_files = _get_rapl_files()
    if not rapl_files:
        return

    # Get RAPL domain names
    domain_names = []
    for i, rapl_file in enumerate(rapl_files):
        domain_name = _get_rapl_domain_name(rapl_file)
        domain_names.append(domain_name)

    # Reorder rapl_files and domain_names alphabetically by domain name
    rapl_files, domain_names = zip(
        *sorted(zip(rapl_files, domain_names), key=lambda x: x[1])
    )

    print(f"Found {len(rapl_files)} RAPL domains:")
    for i, rapl_file in enumerate(rapl_files):
        print(f"  {i + 1}. {domain_names[i]}")
    print()

    # Open RAPL files to read energy consumption
    rapl_f = [open(f, "r") for f in rapl_files]

    # Measure idle energy consumption
    print(f"📊 Measuring idle energy consumption for {T} seconds...")
    idle_energy = _read_rapl_energy(rapl_f, dt=T)

    print("Idle Energy Consumption:")
    total_idle_energy = 0
    for i, (domain, energy) in enumerate(zip(domain_names, idle_energy)):
        print(f"  {domain:15s}: {energy:8.3f} J")
        total_idle_energy += energy
    print(f"  {'Total':15s}: {total_idle_energy:8.3f} J")
    print()

    # Results summary
    results = []

    for dt in [0.1, 0.2, 0.5, 1.0]:
        freq = int(1 / dt)
        print(
            f"📊 Measuring PowerTracker overhead at {freq} Hz (measurement every {dt}s)"
        )
        print("-" * 50)

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)

            tracker = create_default_tracker(temp_dir, measure_power_secs=dt)
            tracker.start()

            # Measure energy consumption during PowerTracker operation
            overhead_energy_raw = _read_rapl_energy(rapl_f, dt=T)

            tracker.stop()

            # Calculate overhead
            overhead_energy = [
                max(e - i, 0) for e, i in zip(overhead_energy_raw, idle_energy)
            ]
            overhead_power = [e / T for e in overhead_energy]
            rel_overhead = [
                e / i * 100 if i > 0 else 0
                for e, i in zip(overhead_energy, idle_energy)
            ]

            # Display results for this frequency
            total_overhead_energy = sum(overhead_energy)
            total_overhead_power = sum(overhead_power)

            print("PowerTracker Energy Overhead:")
            for i, (domain, energy, power, rel) in enumerate(
                zip(domain_names, overhead_energy, overhead_power, rel_overhead)
            ):
                print(
                    f"  {domain:15s}: {energy:8.3f} J  ({power:7.4f} W)  [{rel:5.1f}% of idle]"
                )
            print(
                f"  {'Total':15s}: {total_overhead_energy:8.3f} J  ({total_overhead_power:7.4f} W)"
            )

            # Store results for summary
            results.append(
                {
                    "frequency": freq,
                    "dt": dt,
                    "total_energy": total_overhead_energy,
                    "total_power": total_overhead_power,
                    "domain_energies": overhead_energy,
                    "domain_powers": overhead_power,
                    "relative_overhead": rel_overhead,
                }
            )

            print()

    # Close RAPL files
    for f in rapl_f:
        f.close()

    # Print summary
    print("=" * 60)
    print("OVERHEAD SUMMARY")
    print("=" * 60)
    print(
        f"{'Frequency':>10s} {'Period':>8s} {'Total Energy':>13s} {'Total Power':>12s} {'Efficiency':>12s}"
    )
    print(
        f"{'(Hz)':>10s} {'(s)':>8s} {'(J)':>13s} {'(W)':>12s} {'(J/measurement)':>12s}"
    )
    print("-" * 60)

    for result in results:
        measurements_per_period = T / result["dt"]
        energy_per_measurement = (
            result["total_energy"] / measurements_per_period
            if measurements_per_period > 0
            else 0
        )
        print(
            f"{result['frequency']:>10d} {result['dt']:>8.1f} {result['total_energy']:>13.6f} {result['total_power']:>12.6f} {energy_per_measurement:>12.9f}"
        )

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    best_efficiency = min(
        results,
        key=lambda x: x["total_power"] if x["total_power"] > 0 else float("inf"),
    )
    lowest_overhead = min(results, key=lambda x: x["total_energy"])

    print(
        f"🏆 Most efficient frequency: {best_efficiency['frequency']} Hz ({best_efficiency['total_power']:.6f} W)"
    )
    print(
        f"🏆 Lowest total overhead: {lowest_overhead['frequency']} Hz ({lowest_overhead['total_energy']:.6f} J)"
    )

    # Check if overhead is reasonable
    avg_overhead_power = sum(r["total_power"] for r in results) / len(results)
    if avg_overhead_power < 0.1:
        print("✅ Average overhead is excellent (< 0.1 W)")
    elif avg_overhead_power < 1.0:
        print("✅ Average overhead is good (< 1.0 W)")
    elif avg_overhead_power < 5.0:
        print("⚠️  Average overhead is acceptable (< 5.0 W)")
    else:
        print("❌ Average overhead might be too high (> 5.0 W)")

    print(
        f"📊 Average measurement overhead across all frequencies: {avg_overhead_power:.6f} W"
    )


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
