#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
#
# SLURM script example for running WattAMeter alongside the main job
#
#SBATCH --time=00:01:00
#SBATCH --job-name=wattameter
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1

# Load Python environment
ml conda
conda activate /scratch/$USER/.conda-envs/wattameter

# Load wattameter slurm utilities
WATTAPATH=$(python -c 'import wattameter; import os; print(os.path.dirname(wattameter.__file__))')
source "${WATTAPATH}/utils/slurm.sh"

# Run wattameter on all nodes
start_wattameter -t 0.1 -l info

# Run your script here, e.g.,
if [ $# -gt 0 ]; then
    MAINTIME=$1
else
    MAINTIME=1
fi
srun --nodes=$SLURM_JOB_NUM_NODES --ntasks-per-node=$SLURM_NTASKS_PER_NODE python -c "
from datetime import datetime
import time

now = datetime.now()
print(now.strftime('%Y-%m-%d %H:%M:%S'), 'Hello from Wattameter!', flush=True)

time.sleep($MAINTIME)

now = datetime.now()
print(now.strftime('%Y-%m-%d %H:%M:%S'), 'Bye from Wattameter!')
"

# Stop wattameter after the main job completes
stop_wattameter