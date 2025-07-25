#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC
#
# This script is used to wait for the WattAMeter timer to start before proceeding.

# Record the timestamp of the script start
START_TIME=$(date +%s)

# Get the hostname of the current node
NODE=$(hostname)

# Check if an input filename was given
if [ $# -ge 1 ]; then
    WATTAMETER_FILENAME="$1"
else
    # Get the WattAMeter powerlog filename for the current node
    WATTAMETER_FILENAME=$(wattameter_powerlog_filename --machine-id "${NODE}")
fi

# Wait for the WattAMeter powerlog file to be created or updated
if [ -f "${WATTAMETER_FILENAME}" ]; then
    # Check if the file was created after $START_TIME
    FILE_CREATION_TIME=$(stat -c %W "${WATTAMETER_FILENAME}")
    if [ "${FILE_CREATION_TIME}" -ge "${START_TIME}" ]; then
        echo "${WATTAMETER_FILENAME} file created."
    else
        # Wait until the WattAMeter powerlog file is updated
        LAST_MODIFIED="${START_TIME}"
        while [ "${LAST_MODIFIED}" -le "${START_TIME}" ]; do
            # Read the timestamp of the last modification
            LAST_MODIFIED=$(stat -c %Y "${WATTAMETER_FILENAME}")
            sleep 1  # Wait for 1 second before checking again
        done
        echo "${WATTAMETER_FILENAME} file updated."
    fi
else
    # Wait for the WattAMeter-PowerLog-Filename CLI tool to create the file
    until [ -f "${WATTAMETER_FILENAME}" ]; do
        sleep 1
    done
    echo "${WATTAMETER_FILENAME} file created."
fi