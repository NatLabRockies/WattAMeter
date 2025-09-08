#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from ..codecarbon_tracker import CodeCarbonTracker
from .utils import (
    emissions_filename,
    ForcedExit,
    powerlog_filename,
    handle_signal,
    default_cli_arguments,
)

import signal
import time
import logging
import argparse


def main():
    # Register the signals to handle forced exit
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGHUP):
        signal.signal(sig, handle_signal)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Track power over time, energy and CO2 emissions from your computer."
    )
    default_cli_arguments(parser)
    parser.add_argument(
        "--country",
        "-c",
        type=str,
        default="USA",
        help="ISO code of the country for CO2 emissions tracking (default: USA).",
    )
    parser.add_argument(
        "--region",
        "-r",
        type=str,
        default="colorado",
        help="Region for CO2 emissions tracking (default: colorado).",
    )
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=args.log_level.upper())

    # Initialize the tracker
    tracker = CodeCarbonTracker(
        # For CO2 emissions tracking
        country_iso_code=args.country,
        region=args.region,
        # For power tracking
        measure_power_secs=args.dt_read,
        # For recording data
        log_level=args.log_level.upper(),
        # For saving power and energy data to file
        api_call_interval=args.freq_write,
        output_dir=".",
        output_file=emissions_filename(args.suffix),
        output_power_file=powerlog_filename(args.suffix),
    )
    tracker.run_id = args.id

    # Start tracking power and energy consumption
    t0 = time.time()
    tracker.start()

    # Repeat until interrupted
    try:
        logging.info("Tracking power...")
        while True:
            time.sleep(86400)  # Sleep for a long time to keep the tracker running
    except ForcedExit:
        logging.info("Forced exit detected. Stopping tracker...")
    finally:
        tracker.stop()
        t1 = time.time()
        logging.info(f"Tracker stopped. Elapsed time: {t1 - t0:.2f} seconds.")


if __name__ == "__main__":
    main()  # Call the main function to start the tracker
