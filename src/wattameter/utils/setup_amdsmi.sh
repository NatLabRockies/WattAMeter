#!/bin/bash
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC
#
# This script sets up the AMD SMI Python environment by installing the amdsmi package

if [ -z "$ROCMPATH" ]; then
    echo "ROCMPATH is not set. Trying to find it through rocm-smi..."
    ROCMPATH=$(which rocm-smi | xargs readlink -f | xargs dirname | xargs dirname | xargs dirname)
    if [ -z "$ROCMPATH" ]; then
        echo "Could not find ROCMPATH. Please set it manually."
        exit 1
    fi
fi

# Install AMD SMI from the target ROCm instance.
# Copy to a writable temp dir first because pip's egg_info might not write
# into a read-only system path where amdsmi.egg-info already exists.
AMDSMI_TMP=$(mktemp -d)
cp -r "$ROCMPATH/share/amd_smi/." "$AMDSMI_TMP/"
python -m pip install "$AMDSMI_TMP"
rm -rf "$AMDSMI_TMP"
