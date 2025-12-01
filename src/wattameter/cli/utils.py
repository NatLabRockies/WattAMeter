# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import argparse
import threading
import signal
import uuid

from ..readers import RAPLReader, NVMLReader
from ..readers import Energy, DataThroughput, Utilization, Power, Temperature

signal_handled = threading.Event()


def parse_tracker_spec(spec_string):
    """
    Parse a tracker specification string like 'dt,metric1,metric2,...'
    Returns a tuple of (dt_read, [reader1, reader2, ...])
    where each reader is initialized with the requested metrics.
    """
    parts = spec_string.split(",")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError(
            f"Tracker spec must have at least dt and one metric: {spec_string}"
        )

    try:
        dt_read = float(parts[0])
        assert dt_read > 0
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid dt_read value: {parts[0]}")
    except AssertionError:
        raise argparse.ArgumentTypeError(f"dt_read must be positive: {parts[0]}")

    # Map metric names to classes
    metric_map = {
        "rapl": (RAPLReader, Energy),
        "nvml-energy": (NVMLReader, Energy),
        "nvml-power": (NVMLReader, Power),
        "nvml-temp": (NVMLReader, Temperature),
        "nvml-util": (NVMLReader, Utilization),
        "nvml-nvlink": (NVMLReader, DataThroughput),
    }

    # Group metrics by reader type
    _metrics = {}
    for metric_name in parts[1:]:
        metric_name_lower = metric_name.strip().lower()
        if metric_name_lower not in metric_map:
            raise argparse.ArgumentTypeError(
                f"Unknown metric: {metric_name}. Valid metrics: {', '.join(metric_map.keys())}"
            )
        _reader_class = metric_map[metric_name_lower][0]
        _metric_class = metric_map[metric_name_lower][1]
        if _reader_class not in _metrics:
            _metrics[_reader_class] = [_metric_class]
        else:
            if _metric_class not in _metrics[_reader_class]:
                _metrics[_reader_class].append(_metric_class)

    readers = []
    for reader_class, metric_classes in _metrics.items():
        if reader_class == RAPLReader:
            readers.append(RAPLReader())
        else:
            readers.append(reader_class(quantities=tuple(metric_classes)))

    return dt_read, readers


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
        "--tracker",
        action="append",
        type=parse_tracker_spec,
        default=[],
        help=(
            "Tracker specification: dt_read,metric1,metric2,... (can be specified multiple times). "
            "dt_read is the time interval in seconds between readings. "
            "Available metrics: rapl (CPU energy), nvml-energy (GPU energy), nvml-power (GPU power), "
            "nvml-temp (GPU temperature), nvml-util (GPU utilization), nvml-nvlink (GPU NVLink throughput). "
            "Example: --tracker 0.1,nvml-power,rapl --tracker 1.0,nvml-util"
        ),
    )
    parser.add_argument(
        "--freq-write",
        "-f",
        type=float,
        default=3600,
        help="Frequence for writing data to file (default: every 3600 reads).",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        choices=["debug", "info", "warning", "error", "critical"],
        default="warning",
        help="Set the logging level (default: warning).",
    )
