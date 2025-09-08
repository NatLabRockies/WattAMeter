#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from ..tracker import TrackerArray
from ..readers import NVMLReader, RAPLReader
from ..readers import Power, Temperature
from .utils import powerlog_filename, ForcedExit, handle_signal, default_cli_arguments

import signal
import time
import logging
import argparse


def main():
    # Register the signals to handle forced exit
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGHUP):
        signal.signal(sig, handle_signal)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Track power over time.")
    default_cli_arguments(parser)
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=args.log_level.upper())

    # Initialize readers and outputs
    base_output_filename = powerlog_filename(args.suffix)
    readers = [NVMLReader((Power, Temperature)), RAPLReader()]
    outputs = [f"nvml_{base_output_filename}", f"rapl_{base_output_filename}"]

    # Filter out readers with no tags and their corresponding outputs
    filtered_data = [
        (reader, output)
        for reader, output in zip(readers, outputs)
        if len(reader.tags) > 0
    ]
    readers = [reader for reader, output in filtered_data]
    outputs = [output for reader, output in filtered_data]

    if not readers:
        logging.error("No valid readers available. Exiting.")
        return

    # Initialize the tracker
    tracker = TrackerArray(
        readers, dt_read=args.dt_read, freq_write=args.freq_write, outputs=outputs
    )

    # Record the start time
    t0 = time.time_ns()

    # Signal that the tracker is starting
    with open(base_output_filename, "a") as f:
        timestamp = tracker.trackers[0].format_timestamp(t0)
        f.write(f"# {timestamp} - Power data for run {args.id}\n")
        f.write(f"# {timestamp} - Tracking started\n")

    # Write initial headers to all output files
    for i in range(len(outputs)):
        timestamp = tracker.trackers[i].format_timestamp(t0)
        with open(outputs[i], "a") as f:
            f.write(f"# {timestamp} - Power data for run {args.id}\n")
            f.write(f"# {timestamp} - Tracking started\n")

    # Repeat until interrupted
    try:
        logging.info("Tracking power...")
        tracker.track_until_forced_exit()
    except ForcedExit:
        logging.info("Forced exit detected. Stopping tracker...")
    finally:
        tracker.write()
        t1 = time.time_ns()
        elapsed_s = (t1 - t0) * 1e-9
        logging.info(f"Tracker stopped. Elapsed time: {elapsed_s:.2f} seconds.")


if __name__ == "__main__":
    main()  # Call the main function to start the tracker
