import argparse
import threading
import signal
import uuid


signal_handled = threading.Event()


class ForcedExit(BaseException):
    """Exception raised for forced exit signals."""

    pass


def handle_signal(signum, frame):
    """Handle termination signals."""
    if signal_handled.is_set():  # Thread-safe read
        return  # Ignore further signals
    signal_handled.set()  # Thread-safe write
    signame = signal.Signals(signum).name
    raise ForcedExit(f"Signal handler called with signal {signame} ({signum})")


def _suffix():
    """Generate a suffix based on the ID."""
    parser = argparse.ArgumentParser(exit_on_error=False)
    parser.add_argument(
        "--suffix",
        "-s",
        type=str,
        default=None,
        help="Suffix for the output files (default: None).",
    )
    suffix = parser.parse_known_args()[0].suffix

    return "" if suffix is None else f"_{suffix}"


def powerlog_filename(suffix=None):
    """Generate a log filename based on the ID."""
    suffix = f"_{suffix}" if suffix is not None else _suffix()
    return f"wattameter{suffix}.log"


def print_powerlog_filename(id=None):
    """Print the power log filename based on the ID."""
    print(powerlog_filename(id))


def emissions_filename(suffix=None):
    """Generate an emissions filename based on the ID."""
    suffix = f"_{suffix}" if suffix is not None else _suffix()
    return f"wattameter_emmisions{suffix}.csv"


def print_emissions_filename(id=None):
    """Print the emissions filename based on the ID."""
    print(emissions_filename(id))


def default_cli_arguments(parser: argparse.ArgumentParser):
    """Add common command line arguments to the parser."""
    parser.add_argument(
        "--suffix",
        "-s",
        type=str,
        default=None,
        help="Suffix for the output files (default: None).",
    )
    parser.add_argument(
        "--id",
        "-i",
        type=str,
        default=str(uuid.uuid4()),
        help="Identifier for the experiment.",
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
