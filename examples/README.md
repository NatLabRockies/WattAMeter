# WattAMeter Examples

This directory contains example scripts and notebooks demonstrating various uses of the WattAMeter library.

## Files

### [slurm.sh](slurm.sh)

An SBATCH script for running `wattameter` jobs on a SLURM-managed cluster. This script works on single- or multi-node jobs.

**Usage:**

```bash
sbatch slurm.sh
```

### [sleep.ipynb](sleep.ipynb)

A Jupyter notebook that measures the error between requested sleep times and actual sleep durations. This helps understand the precision of sleep functions in Python.
