#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
"""
Benchmarks for WattAMeter

This script runs various benchmarks with WattAMeter, including:
- Overhead of initializing and destroying the CodeCarbonTracker
- Overhead of measurement operations
- Frequency of power updates

Usage:
    python main.py
"""

from update_time import benchmark_pynvml_update_time, benchmark_rapl_update_time
from overhead import benchmark_static_overhead, benchmark_dynamic_overhead

from utils import print_system_info


if __name__ == "__main__":
    import argparse

    print("WattAMeter Benchmarks")
    print("Results are machine-dependent and should be used for reference only.\n")

    parser = argparse.ArgumentParser(
        description="Run WattAMeter benchmarks to evaluate performance overheads."
    )
    parser.add_argument(
        "--stress-test",
        choices=[None, "gpu_burn", "cpu_stress"],
        default=None,
        help="Type of stress test to run during the dynamic overhead benchmark",
    )
    args = parser.parse_args()

    print_system_info()
    benchmark_pynvml_update_time()
    benchmark_rapl_update_time()
    benchmark_static_overhead()
    benchmark_dynamic_overhead(stress_test=args.stress_test)

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print("Note: These measurements are indicative and will vary based on:")
    print("- Hardware specifications")
    print("- System load")
    print("- Available power monitoring interfaces")
    print("- Background processes")
