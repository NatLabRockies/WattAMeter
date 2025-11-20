#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
#
# This script is used to wait until "run ID" can be read from the file path.
# If no file path is given, it will use the wattameter_powerlog_filename
# utility to get the file path for the current node.

# Usage function to display help
usage() {
    echo "Usage: $0 [-q] [-f filepath] ID"
    echo "  -q          Quiet mode (suppress output)"
    echo "  -f filepath Optional file path to monitor"
    echo "  ID          Run ID to wait for"
    exit "${1:-0}"
}

# Parse options
QUIET=false
FILEPATH=""
while getopts "qf:h" opt; do
    case "$opt" in
        q) QUIET=true ;;
        f) FILEPATH="$OPTARG" ;;
        h) usage 0 ;;
        *) usage 1 ;;
    esac
done
shift $((OPTIND - 1))

# Get the ID from the remaining arguments
if [ $# -ge 1 ]; then
    ID="$1"
else
    usage
fi

# If no filepath was provided via -f flag, generate it
if [ -z "$FILEPATH" ]; then
    # Get the WattAMeter powerlog file path for the current node
    NODE=$(hostname)
    FILEPATH=$(wattameter_powerlog_filename --suffix "${ID}-${NODE}")
fi

# Wait until ID can be read from the file
if [ "$QUIET" = false ]; then
    echo "Waiting for ${FILEPATH} to be ready for run ID ${ID}..."
fi
until grep -qs "run $ID" "${FILEPATH}"; do
    sleep 1  # Wait for 1 second before checking again
done

if [ "$QUIET" = false ]; then
    echo "${FILEPATH} is ready for run ID ${ID}."
fi
exit 0