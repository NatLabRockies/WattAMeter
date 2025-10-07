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

from utils import print_system_info


if __name__ == "__main__":
    print("WattAMeter Benchmarks")
    print("Results are machine-dependent and should be used for reference only.\n")

    print_system_info()
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
