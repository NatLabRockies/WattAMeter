#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
"""
Frequency of Update Benchmark Script for WattAMeter

This script measures the frequency of updates for the PowerTracker.
Since update frequency measurements are machine-dependent, this script is provided
as an example rather than as a test.

Usage:
    python update_time.py
"""

from utils import estimate_dt


def _benchmark_metric(metric_name, get_metric_func, unit, conversion_factor=1):
    """
    Helper function to benchmark a specific NVML metric.

    Args:
        metric_name: Name of the metric being benchmarked
        get_metric_func: Function that returns the metric value
        unit: Unit of the metric (e.g., "mW", "mJ")
        conversion_factor: Factor to convert to human-readable units (e.g., 1000 for mW to W)
    """
    try:
        # Test initial reading
        initial_value = get_metric_func()
        if conversion_factor > 1:
            print(
                f"   Initial {metric_name.lower()} reading: {initial_value} {unit} ({initial_value / conversion_factor:.2f} {unit[1:]})"
            )
        else:
            print(f"   Initial {metric_name.lower()} reading: {initial_value} {unit}")

        # Estimate update frequency
        print(f"   🕐 Estimating {metric_name.lower()} update interval...")
        estimated_dt = estimate_dt(
            get_metric_func,
            n_trials=100,
            ntmax=2000,
        )

        print(f"   ✅ Estimated update interval: {estimated_dt:.6f} seconds")
        print(f"   📈 Estimated update frequency: {1.0 / estimated_dt:.2f} Hz")

        # Provide context on update frequency
        if estimated_dt < 0.01:  # < 10ms (> 100Hz)
            print("   💚 Very fast updates (< 10ms)")
        elif estimated_dt < 0.1:  # < 100ms (> 10Hz)
            print("   ✅ Fast updates (< 100ms)")
        elif estimated_dt < 1.0:  # < 1s (> 1Hz)
            print("   ⚠️  Moderate updates (< 1s)")
        else:  # >= 1s (<= 1Hz)
            print("   ⚠️  Slow updates (>= 1s)")

    except RuntimeError as e:
        print(f"   ❌ Failed to estimate {metric_name.lower()} update time: {e}")
        print(
            f"   💡 This might mean {metric_name.lower()} readings don't change or update very slowly"
        )


def benchmark_pynvml_update_time():
    """Benchmarks the update time of pynvml nvmlDeviceGetPowerUsage function using estimate_dt()."""
    print("\n" + "=" * 60)
    print("PYNVML POWER USAGE UPDATE TIME BENCHMARK")
    print("=" * 60)

    try:
        import pynvml
    except ImportError:
        print("❌ pynvml not available. Skipping benchmark.")
        return

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

        # Benchmark each GPU
        for gpu_id in range(device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
                name = pynvml.nvmlDeviceGetName(handle)
                if hasattr(name, "decode"):
                    name = name.decode("utf-8")

                print(f"\n🔍 Benchmarking GPU {gpu_id}: {name}")

                # Benchmark power usage
                print("\n⚡ Power Usage Benchmark")

                def get_power_usage():
                    try:
                        power_mW = pynvml.nvmlDeviceGetPowerUsage(handle)
                        return power_mW  # Returns power in milliwatts
                    except pynvml.NVMLError as e:
                        raise RuntimeError(f"Failed to get power usage: {e}")

                try:
                    _benchmark_metric("Power Usage", get_power_usage, "mW", 1000)
                except RuntimeError as e:
                    print(f"   ❌ Cannot get power readings: {e}")

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
                except pynvml.NVMLError as e:
                    print(
                        f"   ❌ Energy consumption not supported on GPU {gpu_id}: {e}"
                    )
                    print("   � This feature may require newer GPU models or drivers")
                except RuntimeError as e:
                    print(f"   ❌ Cannot get energy readings: {e}")

            except pynvml.NVMLError as e:
                print(f"   ❌ Error accessing GPU {gpu_id}: {e}")
                continue

    except pynvml.NVMLError as e:
        print(f"❌ Failed to initialize NVML: {e}")
        return
    finally:
        try:
            pynvml.nvmlShutdown()
            print("\n✅ NVML shutdown completed")
        except Exception:
            pass


def benchmark_rapl_update_time():
    """Benchmarks the update time of the RAPL files using estimate_dt()."""
    print("\n" + "=" * 60)
    print("RAPL POWER USAGE UPDATE TIME BENCHMARK")
    print("=" * 60)

    try:
        from codecarbon.core.cpu import IntelRAPL

        rapl = IntelRAPL()
    except (FileNotFoundError, ImportError, SystemError, PermissionError) as e:
        print(f"❌ IntelRAPL not available. Skipping benchmark. Error: {e}")
        return

    # Benchmark each RAPL file
    for rapl_file in rapl._rapl_files:
        print(f"\n🔍 Benchmarking RAPL file: {rapl_file.path}")

        with open(rapl_file.path, "r") as f:

            def get_energy_consumption():
                f.seek(0)
                energy_uj = int(f.readline())
                return energy_uj  # Returns energy in uJ

            try:
                _benchmark_metric(
                    "Energy Consumption", get_energy_consumption, "uJ", 1000000
                )
            except RuntimeError as e:
                print(f"   ❌ Cannot get energy readings: {e}")


if __name__ == "__main__":
    print("WattAMeter Frequency of Update Benchmark")
    print("This script measures the frequency of update in different devices.")
    print("Results are machine-dependent and should be used for reference only.\n")

    benchmark_pynvml_update_time()
    benchmark_rapl_update_time()

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print("Note: These measurements are indicative and will vary based on:")
    print("- Hardware specifications")
    print("- System load")
    print("- Available power monitoring interfaces")
    print("- Background processes")
