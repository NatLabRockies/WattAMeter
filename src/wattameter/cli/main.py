#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from ..power_tracker import PowerTracker

import signal
import time
import logging
import argparse
import threading


class ForcedExit(BaseException):
    """Exception raised for forced exit signals."""

    pass


signal_handled = threading.Event()


def handle_signal(signum, frame):
    """Handle termination signals."""
    if signal_handled.is_set():  # Thread-safe read
        return  # Ignore further signals
    signal_handled.set()  # Thread-safe write
    signame = signal.Signals(signum).name
    raise ForcedExit(f"Signal handler called with signal {signame} ({signum})")


def _suffix(machine_id=None):
    """Generate a suffix based on the machine ID."""
    if machine_id is not None:
        return f"_{machine_id}"

    # If no machine ID is provided, try to parse it from command line arguments
    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument(
        "--machine-id",
        "-i",
        type=str,
        default=None,
        help="Unique identifier for the machine used as suffix in the output files.",
    )
    machine_id = parser.parse_known_args()[0].machine_id

    return "" if machine_id is None else f"_{machine_id}"


def powerlog_filename(machine_id=None):
    """Generate a log filename based on the machine ID."""
    suffix = _suffix(machine_id)
    return f"wattameter{suffix}.log"


def print_powerlog_filename(machine_id=None):
    """Print the power log filename based on the machine ID."""
    print(powerlog_filename(machine_id))


def emissions_filename(machine_id=None):
    """Generate an emissions filename based on the machine ID."""
    suffix = _suffix(machine_id)
    return f"wattameter_emmisions{suffix}.csv"


def print_emissions_filename(machine_id=None):
    """Print the emissions filename based on the machine ID."""
    print(emissions_filename(machine_id))


def main():
    # Register the signals to handle forced exit
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGHUP):
        signal.signal(sig, handle_signal)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Track power over time, energy and CO2 emissions from your computer."
    )
    parser.add_argument(
        "--machine-id",
        "-i",
        type=str,
        default=None,
        help="Unique identifier for the machine used as suffix in the output files.",
    )
    parser.add_argument(
        "--dt-read",
        "-t",
        type=float,
        default=1,
        help="Time interval in seconds for reading power data (default: 1 second).",
    )
    parser.add_argument(
        "--freq-write",
        "-f",
        type=float,
        default=3600,
        help="Frequence for writing power data to file (default: every 3600 reads).",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        choices=["debug", "info", "warning", "error", "critical"],
        default="warning",
        help="Set the logging level (default: warning).",
    )
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
    tracker = PowerTracker(
        # For CO2 emissions tracking
        country_iso_code=args.country,
        region=args.region,
        # For power tracking
        measure_power_secs=args.dt_read,
        # For recording data
        log_level=args.log_level.upper(),
        # For saving power and energy data to file
        api_call_interval=int(args.freq_write / args.dt_read),
        output_dir=".",
        output_file=emissions_filename(args.machine_id),
        output_power_file=powerlog_filename(args.machine_id),
    )

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
