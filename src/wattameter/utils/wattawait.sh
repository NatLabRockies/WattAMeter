#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
#
# This script is used to wait until "run ID" can be read from the file path.
# If no file path is given, it will use the wattameter_powerlog_filename
# utility to get the file path for the current node.

# Usage function to display help
usage() {
    echo "Usage: $0 (ID) [filepath]"
    exit 1
}

# Get the ID from the command line argument
if [ $# -ge 1 ]; then
    ID="$1"
else
    usage
fi

# Check if an input filename was given
if [ $# -ge 2 ]; then
    FILEPATH="$2"
else
    # Get the WattAMeter powerlog file path for the current node
    NODE=$(hostname)
    FILEPATH=$(wattameter_powerlog_filename --suffix "${NODE}")
    echo "Waiting for ${FILEPATH} to be ready for run ID ${ID}..."
fi

# Wait for the file to be created
until [ -f "${FILEPATH}" ]; do
    sleep 1  # Wait for 1 second before checking again
done

# Wait until ID can be read from the file
until grep -q "run $ID" "${FILEPATH}"; do
    sleep 1  # Wait for 1 second before checking again
done

echo "${FILEPATH} is ready for run ID ${ID}."
exit 0