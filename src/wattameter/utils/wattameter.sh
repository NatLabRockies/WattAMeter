#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
#
# This script is used to run the WattAMeter CLI tool.
# It captures the output and PID of the process, allowing for graceful termination on timeout.

# Usage function to display help
usage() {
    echo "Usage: $0 [-i|--index run_id] [-s|--suffix suffix] [-q|--quiet] [wattameter-options]"
    echo "-i, --id    run_id  : Specify a run identifier for this WattAMeter instance"
    echo "-s, --suffix suffix : Specify a custom suffix for log file naming"
    echo "-q, --quiet         : Quiet mode; suppress startup messages"
    echo "-h, --help          : Display this help message"
    echo "wattameter-options  : Additional options to pass to the wattameter command"
    echo ""
    echo "Note: Default suffix is hostname."
    echo "      If --id is provided, default suffix becomes run_id-hostname."
    exit 0
}

main() {
    # Get the hostname of the current node
    local NODE=$(hostname)

    # Parse arguments manually
    local RUN_ID=""
    local SUFFIX=${NODE}
    local CUSTOM_SUFFIX=false
    local QUIET=false
    local EXTRA_ARGS=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -i|--id) RUN_ID="$2"; shift 2 ;;
            -s|--suffix) SUFFIX="$2"; CUSTOM_SUFFIX=true; shift 2 ;;
            -q|--quiet) QUIET=true; shift ;;
            -h|--help) usage ;;
            *) EXTRA_ARGS+=("$1"); shift ;;
        esac
    done
    set -- "${EXTRA_ARGS[@]}"  # Restore positional parameters

    # Determine suffix based on flags
    if [[ "$CUSTOM_SUFFIX" = false && -n "${RUN_ID}" ]]; then
        SUFFIX="${RUN_ID}-${NODE}"
    fi

    # Set log file name
    local log_file="wattameter-${SUFFIX}.txt"
    if [[ "${QUIET}" = false ]]; then
        echo "Logging execution on ${NODE} to ${log_file}"
    fi

    # Build wattameter command arguments
    local WATTAMETER_ARGS="--suffix ${SUFFIX}"
    if [ -n "${RUN_ID}" ]; then
        WATTAMETER_ARGS="${WATTAMETER_ARGS} --id ${RUN_ID}"
    fi

    # Start the tracking and log the output
    wattameter ${WATTAMETER_ARGS} "$@" > "${log_file}" 2>&1 &
    local WATTAMETER_PID=$!

    # Gracefully terminates the tracking process on exit.
    local SIGNAL=""
    on_exit() {
        local TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
        echo "${TIMESTAMP}: WattAMeter interrupted on ${NODE} by signal ${SIGNAL}. Terminating..."

        # Interrupt the WattAMeter process
        kill -INT "$WATTAMETER_PID" 2>/dev/null
        wait "$WATTAMETER_PID" 2>/dev/null
        while kill -0 "$WATTAMETER_PID" 2>/dev/null; do
            sleep 0.1
        done

        local TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
        echo "${TIMESTAMP}: WattAMeter has been terminated on node ${NODE}."
    }
    trap 'SIGNAL=INT; on_exit' INT
    trap 'SIGNAL=TERM; on_exit' TERM
    trap 'SIGNAL=HUP; on_exit' HUP

    # Wait for the WattAMeter process to finish
    wait "$WATTAMETER_PID"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi