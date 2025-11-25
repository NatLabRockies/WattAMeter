#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from ..tracker import TrackerArray, Tracker
from ..readers import NVMLReader, RAPLReader, Power
from .utils import powerlog_filename, ForcedExit, handle_signal, default_cli_arguments

import signal
import time
import logging
import argparse
from datetime import datetime


def main(timestamp_fmt="%Y-%m-%d_%H:%M:%S.%f"):
    # Register the signals to handle forced exit
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, handle_signal)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="WattAMeter CLI")
    default_cli_arguments(parser)
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=args.log_level.upper())

    # Initialize base output filename
    base_output_filename = powerlog_filename(args.suffix)
    all_outputs = [base_output_filename]

    # Use default tracker configuration if user provides none
    tracker_specs = (
        args.tracker if args.tracker else [(0.1, [NVMLReader((Power,)), RAPLReader()])]
    )

    # Create trackers based on specifications
    trackers = []
    for idx, (dt_read, r_list) in enumerate(tracker_specs):
        # Filter out readers with no tags
        readers = [r for r in r_list if len(r.tags) > 0]
        if not readers:
            logging.warning(
                f"Tracker specification {idx} has no valid readers. Skipping."
            )
            continue

        # Generate unique output filenames for each reader
        output_tags = [
            f"{reader.__class__.__name__.lower()[0:4]}_{str(dt_read).replace('.', '')}"
            for reader in readers
        ]
        for i, tag in enumerate(output_tags):
            # Count occurrences using substring match
            count = sum(1 for existing_tag in all_outputs if tag in existing_tag)
            if count > 0:
                output_tags[i] = f"{tag}_{count}"
        outputs = [f"{tag}_{base_output_filename}" for tag in output_tags]
        all_outputs.extend(outputs)

        if len(readers) == 1:
            tracker = Tracker(
                reader=readers[0],
                dt_read=dt_read,
                freq_write=args.freq_write,
                output=outputs[0],
            )
        else:
            tracker = TrackerArray(
                readers,
                dt_read=dt_read,
                freq_write=args.freq_write,
                outputs=outputs,
            )
        trackers.append(tracker)

    if not trackers:
        logging.error("No valid readers available. Exiting.")
        return

    # Signal wattameter is starting
    t0 = time.time_ns()
    timestamp0 = datetime.fromtimestamp(t0 / 1e9).strftime(timestamp_fmt)
    for file in all_outputs:
        with open(file, "a") as f:
            f.write(f"# {timestamp0} - WattAMeter run {args.id}\n")

    # Repeat until interrupted
    try:
        logging.info("Tracking with WattAMeter...")
        for t in trackers[:-1]:
            t.start(freq_write=args.freq_write)
        trackers[-1].track_until_forced_exit()
    except ForcedExit:
        logging.info("Forced exit detected. Stopping tracker...")

        # Ignore further signals during cleanup
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
    finally:
        for t in trackers[:-1]:
            t.stop(freq_write=args.freq_write)
        trackers[-1].write()
        t1 = time.time_ns()
        elapsed_s = (t1 - t0) * 1e-9
        logging.info(f"Tracker stopped. Elapsed time: {elapsed_s:.2f} seconds.")


if __name__ == "__main__":
    main()  # Call the main function to start the tracker
