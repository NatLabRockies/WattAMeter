# WattAMeter Benchmarks

This directory contains benchmark scripts for measuring and analyzing the performance characteristics of the WattAMeter library.

## Files

### [overhead.py](overhead.py)

A benchmarking script that measures the overhead introduced by WattAMeter when tracking power. It evaluates both static overhead (initialization and termination times) and dynamic overhead (per-measurement time) with or without stress conditions on the system.

**Usage:**

```bash
python overhead.py [--cpu_stress_test CPU_STRESS_TEST] [--gpu_burn_dir GPU_BURN_DIR]
```

or, if WattAMeter is installed as a package:

```bash
wattameter_benchmark_overhead [--cpu_stress_test CPU_STRESS_TEST] [--gpu_burn_dir GPU_BURN_DIR]
```

The script benchmarks:

- **Static Overhead**: Time taken to initialize and terminate WattAMeter tracking
- **Dynamic Overhead**: Time taken for each power measurement under different system loads:
  - Idle system
  - Stressed GPUs (using `gpu_burn`)
  - Stressed CPUs (using a CPU stress function)

### [update_time.py](update_time.py)

A benchmarking script that measures the frequency of updates for various power and energy metrics. This script helps determine how often power readings are updated by the hardware.

**Usage:**

```bash
python update_time.py [--gpu_burn_dir GPU_BURN_DIR]
```

or, if WattAMeter is installed as a package:

```bash
wattameter_benchmark_dt [--gpu_burn_dir GPU_BURN_DIR]
```

The script benchmarks:

- **Power Usage**: Update frequency of `nvmlDeviceGetPowerUsage`
- **Energy Consumption**: Update frequency of `nvmlDeviceGetTotalEnergyConsumption`
- **GPU Utilization**: Update frequency of `nvmlDeviceGetUtilizationRates`
- **Temperature**: Update frequency of `nvmlDeviceGetTemperature`

Results include estimated update intervals and frequencies for each available GPU.

## Notes

- Benchmark results are machine-dependent and should be used for relative comparisons rather than absolute values
- Some benchmarks require NVIDIA GPUs
- Results may vary based on system load, hardware configuration, and driver versions
