# WattAMeter Examples

This directory contains example scripts and notebooks demonstrating various uses of the WattAMeter library.

## Files

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
python script_name.py
```

For benchmarking examples, see the [`benchmark/`](../benchmark/) directory.

For Jupyter notebooks, start Jupyter and open the `.ipynb` files:

```bash
jupyter notebook
# or
jupyter lab
```
