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

from .utils import (
    estimate_dt,
    print_benchmark_banner,
    print_benchmark_footer,
    start_gpu_burn,
    stop_gpu_burn,
    start_cpu_stress,
    stop_cpu_stress,
)
from ..readers import RAPLReader


def _benchmark_metric(metric_name, get_metric_func, unit):
    """
    Helper function to benchmark a specific NVML metric.

    :param metric_name: Name of the metric being benchmarked
    :param get_metric_func: Function that returns the metric value
    :param unit: Unit of the metric (e.g., "mW", "mJ")
    :raises RuntimeError: If the metric cannot be read or does not update
    """
    try:
        # Test initial reading
        initial_value = get_metric_func()
        print(f"   Initial {metric_name.lower()} reading: {initial_value} {unit}")

        # Estimate update frequency
        print(f"   🕐 Estimating {metric_name.lower()} update interval...")
        t0 = time.perf_counter()
        estimated_dt = estimate_dt(
            get_metric_func,
            n_trials=1000,
            ntmax=2000,
        )
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


def benchmark_pynvml_update_time(gpu_burn_dir=None):
    """Benchmarks the update time of pynvml nvmlDeviceGetPowerUsage function using estimate_dt()."""
    print_benchmark_banner("PYNVML POWER USAGE UPDATE TIME BENCHMARK")

    try:
        import pynvml
    except ImportError:
        print("❌ pynvml not available. Skipping benchmark.")
        return

    gpu_burn_process = None
    try:
        pynvml.nvmlInit()
        print("✅ NVML initialized successfully")

        # Check if any GPUs are available
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count == 0:
                print("❌ No NVIDIA GPUs found. Skipping benchmark.")
                pynvml.nvmlShutdown()
                return
            print(f"📊 Found {device_count} NVIDIA GPU(s)")

        except pynvml.NVMLError as e:
            print(f"❌ Error getting device count: {e}")
            pynvml.nvmlShutdown()
            return

        # Stress GPUs if gpu_burn is available
        gpu_burn_process = start_gpu_burn(gpu_burn_dir, warmup_s=10.0)

        # Benchmark each GPU
        for gpu_id in range(device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                name = pynvml.nvmlDeviceGetName(handle)
                if hasattr(name, "decode"):
                    name = name.decode("utf-8")

                print(f"\n🔍 Benchmarking GPU {gpu_id}: {name}")

                # Benchmark energy consumption
                print("\n🔋 Energy Consumption Benchmark")

                def get_energy_consumption():
                    try:
                        energy_mJ = pynvml.nvmlDeviceGetTotalEnergyConsumption(handle)
                        return energy_mJ  # Returns energy in millijoules
                    except pynvml.NVMLError as e:
                        raise RuntimeError(f"Failed to get energy consumption: {e}")

                try:
                    _benchmark_metric(
                        "Energy Consumption", get_energy_consumption, "mJ"
                    )
                except RuntimeError as e:
                    print(f"   ❌ Cannot get energy readings: {e}")

                # Benchmark power usage
                print("\n⚡ Power Usage Benchmark")

                def get_power_usage():
                    try:
                        power_mW = pynvml.nvmlDeviceGetPowerUsage(handle)
                        return power_mW  # Returns power in milliwatts
                    except pynvml.NVMLError as e:
                        raise RuntimeError(f"Failed to get power usage: {e}")

                try:
                    _benchmark_metric("Power Usage", get_power_usage, "mW")
                except RuntimeError as e:
                    print(f"   ❌ Cannot get power readings: {e}")

                # Benchmark utilization rates
                print("\n📊 Utilization Rates Benchmark")

                def get_memory_utilization():
                    try:
                        utilization = pynvml.nvmlDeviceGetUtilizationRates(
                            handle
                        ).memory
                        return utilization  # Returns utilization
                    except pynvml.NVMLError as e:
                        raise RuntimeError(f"Failed to get utilization rates: {e}")

                try:
                    _benchmark_metric(
                        "Memory utilization Rate", get_memory_utilization, "%"
                    )
                except RuntimeError as e:
                    print(f"   ❌ Cannot get utilization readings: {e}")

                # Benchmark temperature
                print("\n🌡️  Temperature Benchmark")

                def get_temperature():
                    try:
                        temp_c = pynvml.nvmlDeviceGetTemperature(
                            handle, pynvml.NVML_TEMPERATURE_GPU
                        )
                        return temp_c  # Returns temperature in Celsius
                    except pynvml.NVMLError as e:
                        raise RuntimeError(f"Failed to get temperature: {e}")

                try:
                    _benchmark_metric("Temperature", get_temperature, "°C")
                except RuntimeError as e:
                    print(f"   ❌ Cannot get temperature readings: {e}")

            except pynvml.NVMLError as e:
                print(f"   ❌ Error accessing GPU {gpu_id}: {e}")
                continue

    except pynvml.NVMLError as e:
        print(f"❌ Failed to initialize NVML: {e}")
        return
    finally:
        # Terminate gpu_burn if it was started
        stop_gpu_burn(gpu_burn_process)

        # Shutdown NVML
        try:
            pynvml.nvmlShutdown()
            print("\n✅ NVML shutdown completed")
        except Exception:
            pass


def benchmark_rapl_update_time(cpu_stress_test=False):
    """Benchmarks the update time of the RAPL files using estimate_dt()."""
    print_benchmark_banner("RAPL POWER USAGE UPDATE TIME BENCHMARK")

    rapl = RAPLReader()
    if len(rapl.tags) == 0:
        print("❌ No RAPL devices found. Skipping benchmark.")
        return

    # Stress CPUs
    cpu_stress_process = None
    if cpu_stress_test:
        cpu_stress_process = start_cpu_stress(warmup_s=5.0)

    # Benchmark each RAPL file
    for rapl_file in rapl.devices:
        print(f"\n🔍 Benchmarking RAPL file: {rapl_file.path}")

        try:
            _benchmark_metric("Energy Consumption", rapl_file.read_energy, "uJ")
        except RuntimeError as e:
            print(f"   ❌ Cannot get energy readings: {e}")

    # Terminate CPU stress process
    stop_cpu_stress(cpu_stress_process)


def run_benchmark():
    import argparse

    logging.basicConfig(level=logging.INFO)

    print("WattAMeter Frequency of Update Benchmark")
    print("This script measures the frequency of update in different devices.")
    print("Results are machine-dependent and should be used for reference only.\n")

    parser = argparse.ArgumentParser(
        description="Benchmark the frequency of update of various WattAMeter components"
    )
    parser.add_argument(
        "--cpu-stress-test",
        action="store_true",
        help="Stress the CPUs to see how that affects update times",
    )
    parser.add_argument(
        "--gpu-burn-dir",
        type=str,
        default=None,
        help="Path to the gpu_burn benchmark to stress GPUs and see how that affects update times",
    )
    args = parser.parse_args()

    benchmark_pynvml_update_time(gpu_burn_dir=args.gpu_burn_dir)
    benchmark_rapl_update_time(cpu_stress_test=args.cpu_stress_test)

    print_benchmark_footer()


if __name__ == "__main__":
    run_benchmark()  # Call the benchmark runner
