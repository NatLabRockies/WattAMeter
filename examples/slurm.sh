#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
#
# SLURM script example for running WattAMeter alongside the main job
#
#SBATCH --time=00:02:00
#SBATCH --job-name=wattameter
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --signal=USR1@0

# Conda environment path
CONDAENV=/scratch/$USER/.conda-envs/wattameter

# Load Python environment
ml conda
conda activate $CONDAENV

# Get the path of the wattameter script
WATTAPATH=$(python -c 'import wattameter; import os; print(os.path.dirname(wattameter.__file__))')
WATTASCRIPT="${WATTAPATH}/utils/wattameter.sh"
WATTAWAIT="${WATTAPATH}/utils/wattawait.sh"

# Run wattameter on all nodes
srun --overlap --wait=0 --nodes=$SLURM_JOB_NUM_NODES --ntasks-per-node=1 "${WATTAWAIT}" $SLURM_JOB_ID &
WAIT_PID=$!
srun --overlap --wait=0 --output=slurm-$SLURM_JOB_ID-wattameter.txt --nodes=$SLURM_JOB_NUM_NODES --ntasks-per-node=1 "${WATTASCRIPT}" -i $SLURM_JOB_ID -t 0.1 -l info &
wait $WAIT_PID

# Run your script here, e.g.,
MAINTIME=1
# MAINTIME=120
srun --nodes=$SLURM_JOB_NUM_NODES --ntasks-per-node=$SLURM_NTASKS_PER_NODE python -c "import time; print('Hello from Wattameter!'); time.sleep($MAINTIME); print('Bye from Wattameter!')"

# Cancel the job after the main script completes
echo "Main script completed. Canceling the job."
scancel $SLURM_JOB_ID