#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC
#
# This script contains utility functions for SLURM job management.

start_wattameter () {
    # Error out if not running inside a SLURM job
    if [ -z "$SLURM_JOB_ID" ]; then
        echo "Error: start_wattameter must be run inside a SLURM job allocation."
        return 1
    fi

    # Set default value for SLURM_JOB_NUM_NODES if not defined
    if [ -z "$SLURM_JOB_NUM_NODES" ]; then
        local SLURM_JOB_NUM_NODES=1
    fi

    # Initialize global variables for wattameter steps
    if [ -z "$WATTAMETER_N_STARTED_STEPS" ]; then
        WATTAMETER_N_STARTED_STEPS=0
    fi
    if [ -z "$WATTAMETER_SLURM_STEP_IDS" ]; then
        WATTAMETER_SLURM_STEP_IDS=()
    fi

    # Use a suffix to differentiate multiple wattameter runs
    if [[ "$WATTAMETER_N_STARTED_STEPS" -gt 0 ]]; then
        local ID="$SLURM_JOB_ID-$WATTAMETER_N_STARTED_STEPS"
    else
        local ID="$SLURM_JOB_ID"
    fi
    WATTAMETER_N_STARTED_STEPS=$((WATTAMETER_N_STARTED_STEPS + 1))

    # Get the path of the wattameter script
    local WATTAPATH=$(python -c 'import wattameter; import os; print(os.path.dirname(wattameter.__file__))')
    local WATTASCRIPT="${WATTAPATH}/utils/wattameter.sh"
    local WATTAWAIT="${WATTAPATH}/utils/wattawait.sh"

    # Get output directory from arguments if provided, otherwise use current directory
    local OUTPUT_DIR="."
    local EXTRA_ARGS=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -o|--output-dir)
                if [[ $# -lt 2 || "$2" == -* ]]; then
                    echo "Error: $1 requires a value."
                    return 1
                fi
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --output-dir=*)
                OUTPUT_DIR="${1#--output-dir=}"
                shift
                ;;
            -h|--help) 
                echo "Usage: start_wattameter [-o|--output-dir output_dir] [wattameter-options]"
                echo "-o, --output-dir output_dir : Specify a directory to save output files if different from CWD"
                echo "wattameter-options  : Additional options to pass to the wattameter command"
                return 0
                ;;
            --)
                shift
                EXTRA_ARGS+=("$@")
                break
                ;;
            *) EXTRA_ARGS+=("$1"); shift ;;
        esac
    done
    set -- "${EXTRA_ARGS[@]}"  # Restore positional parameters

    # Create output directory if it doesn't exist
    mkdir -p -- "$OUTPUT_DIR" || {
        echo "Error: failed to create output directory '$OUTPUT_DIR'."
        return 1
    }

    # Create sentinel to track wattameter start
    srun --overlap --wait=0 --chdir="$OUTPUT_DIR" \
        --nodes="$SLURM_JOB_NUM_NODES" --ntasks-per-node=1 \
        "${WATTAWAIT}" -q "$ID" &
    local WAIT_PID=$!

    # Run wattameter on all nodes
    srun --overlap --wait=0 \
        --chdir="$OUTPUT_DIR" \
        --output="slurm-$ID-wattameter.txt" \
        --nodes="$SLURM_JOB_NUM_NODES" --ntasks-per-node=1 \
        "${WATTASCRIPT}" -i "$ID" "$@" 2>/dev/null &

    # Wait for wattameter to start
    wait "$WAIT_PID" 2>/dev/null

    # Get the step ID from the last wattameter srun command
    local SANITY_CHECK=0
    while true; do
        local STEP_ID=$(squeue -j "$SLURM_JOB_ID" -h -s --format="%i %.13j" | grep "wattameter.sh$" | tail -1 | awk '{print $1}')
        if [ -n "$STEP_ID" ]; then
            break
        fi
        sleep 0.1
        SANITY_CHECK=$((SANITY_CHECK + 1))
        if [ $SANITY_CHECK -gt 600 ]; then
            echo "Error: Unable to retrieve wattameter SLURM step ID."
            return 1
        fi
    done
    WATTAMETER_SLURM_STEP_IDS+=("$STEP_ID")

    local TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo "${TIMESTAMP}: Started WattAmeter job step $STEP_ID"
}

stop_wattameter () {    
    # Error out if not running inside a SLURM job
    if [ -z "$SLURM_JOB_ID" ]; then
        echo "Error: stop_wattameter must be run inside a SLURM job allocation."
        return 1
    fi

    # Cancel the last started wattameter step
    if [[ ${#WATTAMETER_SLURM_STEP_IDS[@]} -gt 0 ]]; then
        # Pop last wattameter STEP ID
        local STEP_ID="${WATTAMETER_SLURM_STEP_IDS[-1]}"
        unset 'WATTAMETER_SLURM_STEP_IDS[-1]'
        
        # Stop ID using scancel
        if [ -n "$STEP_ID" ]; then
            scancel --signal=INT "$STEP_ID" 2>/dev/null

            # Wait for the step to terminate
            local SANITY_CHECK=0
            while squeue -j "$SLURM_JOB_ID" -h -s --format "%i" | grep -q "^$STEP_ID$"; do
                sleep 0.1
                SANITY_CHECK=$((SANITY_CHECK + 1))
                if [ $SANITY_CHECK -gt 600 ]; then
                    echo "Warning: WattAMeter step $STEP_ID did not terminate in a timely manner."
                    break
                fi
            done

            local TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
            echo "${TIMESTAMP}: Stopped WattAmeter job step $STEP_ID"
        fi
    fi
}