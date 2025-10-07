# WattAMeter Benchmarks

This directory contains benchmark scripts for measuring and analyzing the performance characteristics of the WattAMeter library.

## Files

### [update_time.py](update_time.py)

A benchmarking script that measures the frequency of updates for various NVML power and energy metrics. This script helps determine how often power readings are updated by the hardware.

**Usage:**

```bash
python update_time.py
```

The script benchmarks:

- **Power Usage**: Update frequency of `nvmlDeviceGetPowerUsage`
- **Energy Consumption**: Update frequency of `nvmlDeviceGetTotalEnergyConsumption`

Results include estimated update intervals and frequencies for each available GPU.

### [main.py](main.py)

Main benchmark runner that can execute multiple benchmark scripts.

### [utils.py](utils.py)

Utility functions shared across benchmark scripts.

## Running Benchmarks

Run any of the benchmark scripts directly:

```bash
cd benchmark
python overhead.py
python update_time.py
```

Or use the main runner:

```bash
python main.py
```

## Notes

- Benchmark results are machine-dependent and should be used for relative comparisons rather than absolute values
- Some benchmarks require NVIDIA GPUs
- Results may vary based on system load, hardware configuration, and driver versions
