#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
#
# This script is used to run the WattAMeter CLI tool for power tracking.
# It captures the output and PID of the process, allowing for graceful termination on timeout.

get_log_file_name() {
    NODE=$(hostname)
    if [ -z "${RUN_ID}" ]; then
        echo "wattameter-${NODE}.txt"
    else
        echo "wattameter-${RUN_ID}-${NODE}.txt"
    fi
}

main() {
    # Default values
    RUN_ID=""
    DT_READ=1
    FREQ_WRITE=3600
    LOG_LEVEL="warning"

    # Find the WattAMeter CLI tool
    if ! command -v wattameter 2>&1 >/dev/null; then
        SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
        if [ -f "${SCRIPTPATH}/../cli/main.py" ]; then
            WATTAMETER="python ${SCRIPTPATH}/../cli/main.py"
        else
            echo "WattAMeter CLI not found. Please ensure it is installed and available in the path."
            exit 1
        fi
    else
        WATTAMETER=$(command -v wattameter)
    fi

    # Usage function to display help
    usage() {
        echo "Usage: $0 [-i run_id] [-t dt_read] [-f freq_write] [-l log_level]"
        exit 1
    }

    # Parse command line options
    while getopts ":i:t:f:l:" opt; do
        case $opt in
            i) RUN_ID="$OPTARG" ;;
            t) DT_READ="$OPTARG" ;;
            f) FREQ_WRITE="$OPTARG" ;;
            l) LOG_LEVEL="$OPTARG" ;;
            \?) echo "Invalid option: -$OPTARG" >&2; usage ;;
            :) echo "Option -$OPTARG requires an argument." >&2; usage ;;
        esac
    done

    # Get the hostname of the current node
    NODE=$(hostname)

    # Use the log identifier name if provided
    log_file=$(get_log_file_name)
    echo "Logging execution on ${NODE} to ${log_file}"

    # Start the power series tracking and log the output
    ${WATTAMETER} \
        --suffix "${NODE}" \
        --id "${RUN_ID}" \
        --dt-read "${DT_READ}" \
        --freq-write "${FREQ_WRITE}" \
        --log-level "${LOG_LEVEL}" > "${log_file}" 2>&1 &
    WATTAMETER_PID=$!

    # Gracefully terminates the tracking process on exit.
    SIGNAL=""
    on_exit() {
        echo "WattAMeter interrupted on ${NODE} by signal ${SIGNAL}. Terminating..."
        if [ -n "$EXITING" ]; then
            return
        fi
        EXITING=1
        kill -TERM "$WATTAMETER_PID" 2>/dev/null
        wait "$WATTAMETER_PID" 2>/dev/null
        while kill -0 "$WATTAMETER_PID" 2>/dev/null; do
            sleep 1
        done
        echo "WattAMeter has been terminated on node ${NODE}."
    }
    trap 'SIGNAL=INT; on_exit' INT
    trap 'SIGNAL=TERM; on_exit' TERM
    trap 'SIGNAL=HUP; on_exit' HUP
    trap 'SIGNAL=USR1; on_exit' USR1
    trap 'echo "WattAMeter exiting on ${NODE}..."' EXIT

    # Wait for the WattAMeter process to finish
    wait "$WATTAMETER_PID"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi