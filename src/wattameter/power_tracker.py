# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from .readers import BaseReader

from contextlib import AbstractContextManager
import logging
import time
import threading
import numpy as np
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class Tracker(AbstractContextManager):
    """Tracker"""

    def __init__(self, reader: BaseReader, freq: float = 1.0, output=None) -> None:
        super().__init__()

        # For reading data
        self.freq = freq
        self.reader = reader

        # Time series and data storage
        self.time_series = deque([])
        self.reading_time = deque([])
        self.data = deque([])

        # Output options
        self.timestamp_fmt = "%Y-%m-%d_%H:%M:%S.%f"
        self._output = output

        # Read scheduler for asynchronous reading
        self._async_thread = None
        self._lock = threading.Lock()

    @property
    def power_data_is_added(self) -> bool:
        """Whether power data is added to the reading stream."""
        reader_q = self.reader.quantities
        return "energy" in reader_q and "power" not in reader_q

    @property
    def units(self):
        res = [self.reader.UNITS[q] for q in self.reader.quantities]
        if self.power_data_is_added:
            res = res + ["W"]
        return res

    def read(self) -> float:
        # Read data from the reader and measure the time taken
        timestamp0 = time.time_ns()
        data = self.reader.read()
        timestamp1 = time.time_ns()

        # Calculate the timestamp and elapsed time
        timestamp = int((timestamp0 + timestamp1) / 2.0)
        elapsed = timestamp1 - timestamp0

        # Store the data in the deques
        with self._lock:
            self.time_series.append(timestamp)
            self.reading_time.append(elapsed)
            self.data.append(data)

        return elapsed / 1e9  # Convert to seconds

    def _read_and_sleep(self):
        # Read data from all readers
        elapsed = self.read()
        logger.debug(f"Read completed in {elapsed:.3e} seconds.")

        # Sleep for the remaining time if needed
        if self.freq * elapsed < 1.0:
            time.sleep((1 / self.freq) - elapsed)
        else:
            logger.warning(
                f"Please increase `freq` value. "
                f"Current value: {self.freq:.3e} (read every {(1 / self.freq):.3e} seconds). "
                f"Time taken for reading: {elapsed:.3e} seconds."
            )

    def _update_series(self, event):
        while not event.is_set():
            self._read_and_sleep()

    def start(self):
        if self._async_thread is None:
            # Define the async task to update the power series
            self._stop_event = threading.Event()
            self._async_thread = threading.Thread(
                name="Tracker",
                target=self._update_series,
                args=(self._stop_event,),
                daemon=True,
            )

            # Start the async task
            self._async_thread.start()
        else:
            logger.warning("Tracker is already running. Use stop() to stop it first.")

    def stop(self):
        if self._async_thread is not None:
            # Wait for the async task to finish
            self._stop_event.set()
            self._async_thread.join()

            # Mark the async thread as stopped
            self._async_thread = None
        else:
            logger.warning("Tracker is not running. Nothing to stop.")

    def flush_data(self):
        """Flush all collected data from the tracker.

        Returns the collected time series, reading times, and data, then clears
        the internal buffers.
        """
        with self._lock:
            time_series = np.array(self.time_series)
            reading_time = np.array(self.reading_time)
            data = np.array(self.data)
            self.time_series.clear()
            self.reading_time.clear()
            self.data.clear()

        if self.power_data_is_added:
            power_data = self.reader.compute_power_series(
                time_series=time_series, energy_data=data
            )
            data = np.hstack((data, power_data))

        return time_series, reading_time, data

    @property
    def tags(self):
        """Return a list of tags for each device."""
        return self.reader.tags

    @property
    def output(self):
        if self._output is None:
            return f"{self.reader.__class__.__name__.lower()}_series.log"
        else:
            return self._output

    def write_header(self):
        """Write the header to the output file."""
        timestamp_str = datetime.fromtimestamp(time.time()).strftime(self.timestamp_fmt)
        with open(self.output, "a", encoding="utf-8") as f:
            f.write("# timestamp" + " " * (len(timestamp_str) - 9))
            f.write(" reading-time[ns]")
            for unit in self.units:
                for tag in self.tags:
                    f.write(f" {tag}[{unit}]")
            f.write("\n")

    def write(self, time_series, reading_time, data):
        """Write the collected data to the output file."""

        buffer = ""
        for t, rtime, stream in zip(time_series, reading_time, data):
            buffer += "  " + datetime.fromtimestamp(t / 1e9).strftime(
                self.timestamp_fmt
            )
            buffer += f" {rtime}"
            for v in stream:
                buffer += f" {v}"
            buffer += "\n"

        with open(self.output, "a", encoding="utf-8") as f:
            f.write(buffer)

    def __enter__(self):
        """Enter the context manager."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        self.stop()
        self.write_header()
        self.write(*self.flush_data())
        return None

    def track_until_forced_exit(self):
        """Track power and energy consumption until a forced exit."""
        try:
            while True:
                self._read_and_sleep()
        except KeyboardInterrupt:
            logger.info("Forced exit detected. Stopping tracker...")
        except Exception as e:
            self.write_header()
            self.write(*self.flush_data())
            logger.error(f"An error occurred: {e}")
        finally:
            self.write_header()
            self.write(*self.flush_data())
