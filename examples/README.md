# WattAMeter Examples

This directory contains example scripts and notebooks demonstrating various uses of the WattAMeter library.

## Files

### [overhead_benchmark.py](overhead_benchmark.py)

A comprehensive benchmarking script that measures the performance overhead introduced by PowerTracker. This script is particularly useful for:

- **Performance evaluation**: Understanding how much overhead PowerTracker adds to your application
- **System comparison**: Comparing overhead across different machines or configurations
- **Optimization validation**: Verifying that code changes don't introduce excessive overhead

**Usage:**

```bash
python overhead_benchmark.py
```

The script measures two types of overhead:

- **Initialization overhead**: Time taken to create, start, and stop a PowerTracker instance
- **Measurement overhead**: Time taken for individual power measurements

Results are machine-dependent and should be used for reference only.

### [slurm.sh](slurm.sh)

An SBATCH script for running `wattameter` jobs on a SLURM-managed cluster. The script makes also adds the CPU "Intel Xeon Platinum 8470QL" to the database to exhibit such functionality. This script works on single- or multi-node jobs.

**Usage:**

```bash
sbatch slurm.sh
```

## Running Examples

Make sure you have WattAMeter installed in your environment:

```bash
# If using pip
pip install -e .

# If using pdm
pdm install
```

Then run any of the Python scripts directly:

```bash
cd examples
python overhead_benchmark.py
```

For Jupyter notebooks, start Jupyter and open the `.ipynb` files:

```bash
jupyter notebook
# or
jupyter lab
```
