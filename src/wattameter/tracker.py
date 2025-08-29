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
from abc import abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseTracker(AbstractContextManager):
    def __init__(self, dt_read: float = 1.0) -> None:
        super().__init__()
        self.dt_read = dt_read

        # Read scheduler for asynchronous reading
        self._async_thread = None
        self._lock = threading.Lock()

    @abstractmethod
    def read(self) -> float:
        """Read data.

        :return: Time taken for the reading (in seconds).
        """
        pass

    @abstractmethod
    def write(self, **kwargs) -> None:
        """Write data."""
        pass

    def _read_and_sleep(self):
        """Read data from the reader and sleep to maintain the desired frequency."""
        # Read data from the reader
        elapsed_s = self.read()

        # Sleep for the remaining time if needed
        if elapsed_s < self.dt_read:
            time.sleep(self.dt_read - elapsed_s)
        else:
            logger.warning(f"Time taken for reading: {elapsed_s:.3e} seconds.")

    def _update_series(self, event, dt_write: Optional[float] = None, **kwargs):
        """Asynchronous task to update the power series at the specified frequency.

        :param event: threading.Event to signal when to stop the task.
        :param dt_write: Optional time interval (in seconds) to write the collected data.
        """
        if dt_write is None:
            while not event.is_set():
                self._read_and_sleep()
        else:
            next_write_time = time.time() + dt_write
            while not event.is_set():
                self._read_and_sleep()
                current_time = time.time()
                if current_time >= next_write_time:
                    self.write(**kwargs)
                    next_write_time = current_time + dt_write

    def start(self, dt_write: Optional[float] = None, **kwargs):
        """Start the asynchronous task to update the power series."""
        if self._async_thread is None:
            # Define the async task to update the power series
            self._stop_event = threading.Event()
            self._async_thread = threading.Thread(
                target=self._update_series,
                args=(self._stop_event, dt_write),
                kwargs=kwargs,
                daemon=True,
            )

            # Start the async task
            self._async_thread.start()
        else:
            logger.warning("Tracker is already running. Use stop() to stop it first.")

    def stop(self):
        """Stop the asynchronous task that updates the power series."""
        if self._async_thread is not None:
            # Wait for the async task to finish
            self._stop_event.set()
            self._async_thread.join()

            # Mark the async thread as stopped
            self._async_thread = None
        else:
            logger.warning("Tracker is not running. Nothing to stop.")

    def __enter__(self):
        """Enter the context manager."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        self.stop()
        return None

    def track_until_forced_exit(self, dt_write: Optional[float] = None, **kwargs):
        """Track power and energy consumption until a forced exit.

        :param dt_write: Optional time interval (in seconds) to write the collected data."""
        try:
            if dt_write is None:
                while True:
                    self._read_and_sleep()
            else:
                next_write_time = time.time() + dt_write
                while True:
                    self._read_and_sleep()
                    current_time = time.time()
                    if current_time >= next_write_time:
                        self.write(**kwargs)
                        next_write_time = current_time + dt_write
        except KeyboardInterrupt:
            logger.info("Forced exit detected. Stopping tracker...")


class Tracker(BaseTracker):
    """Generic tracker that reads data from a BaseReader at a specified frequency.

    :param reader: An instance of BaseReader to read data from.
    :param freq: Frequency at which to read data (in Hz). Default is 1.0 Hz
        (one reading per second).
    :param output: Optional output file to write the collected data. If not provided,
        the output file is as defined in :meth:`output`.

    .. attribute:: freq

        Frequency at which to read data (in Hz).

    .. attribute:: reader

        An instance of BaseReader that provides the data to be tracked.

    .. attribute:: time_series

        A deque that stores the timestamps of the readings.

    .. attribute:: reading_time

        A deque that stores the time taken for each reading (in nanoseconds).
        This information can be useful for adjusting the reading frequency.
        Usually, the time taken for reading should be much smaller than
        the interval between readings (1/freq).

    .. attribute:: data

        A deque that stores the data read from the reader.
    """

    def __init__(
        self,
        reader: BaseReader,
        dt_read: float = 1.0,
        dt_write: float = 3600.0,
        output=None,
    ) -> None:
        super().__init__(dt_read)

        # For reading data
        self.reader = reader

        # Time series and data storage
        self.time_series = deque([])
        self.reading_time = deque([])
        self.data = deque([])

        # Output options
        self.dt_write = dt_write
        self._timestamp_fmt = "%Y-%m-%d_%H:%M:%S.%f"
        self._output = output

    def read(self) -> float:
        """Read data from the reader and store it in the internal buffers.

        :return: Time taken for the reading (in seconds).
        """
        # Read data from the reader and measure the time taken
        timestamp0 = time.time_ns()
        data = self.reader.read()
        timestamp1 = time.time_ns()

        # Calculate the timestamp and elapsed time
        timestamp = int((timestamp0 + timestamp1) / 2.0)
        elapsed = timestamp1 - timestamp0
        logger.debug(f"Read completed in {elapsed / 1e9:.3e} seconds.")

        # Store the data in the deques
        with self._lock:
            self.time_series.append(timestamp)
            self.reading_time.append(elapsed)
            self.data.append(data)

        # Compute the total elapsed time including reading and storing
        timestamp2 = time.time_ns()
        elapsed_s = (timestamp2 - timestamp0) / 1e9  # Convert to seconds

        return elapsed_s

    def write(self, *, write_header=True, **kwargs):
        """Write header and data to the output file."""
        if write_header:
            self.write_header()
        self.write_data(*self.flush_data())

    def __enter__(self):
        """Enter the context manager.

        Start the asynchronous task to update and store the power series.
        """
        self.write_header()  # Write header at the beginning
        super().start(self.dt_write, write_header=False)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        super().stop()
        self.write(write_header=False)
        return None

    def track_until_forced_exit(self, dt_write: Optional[float] = None, **kwargs):
        self.write_header()  # Write header at the beginning
        try:
            super().track_until_forced_exit(dt_write, write_header=False, **kwargs)
            self.write(write_header=False)
        except Exception:
            # Propagate other exceptions
            self.write(write_header=False)
            raise

    def flush_data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Flush all collected data from the tracker.

        Aditionally, if the reader provides energy data but not power data,
        compute the power data from the energy data.

        :return: A tuple containing three numpy arrays:

            - time_series: Array of timestamps (in nanoseconds).
            - reading_time: Array of time taken for each reading (in nanoseconds).
            - data: 2D array of the collected data. Each row corresponds to a reading,
              and each column corresponds to a quantity read by the reader. If power data
              is computed, it is appended as the last column.
        """
        with self._lock:
            time_series = np.array(self.time_series)
            reading_time = np.array(self.reading_time)
            data = np.array(self.data)
            self.time_series.clear()
            self.reading_time.clear()
            self.data.clear()

        if self.reader.energy_without_power:
            power_data = self.reader.compute_power_series(time_series * 1e-9, data)
            data = np.hstack((data, power_data))

        return time_series, reading_time, data

    @property
    def tags(self) -> list[str]:
        """List of tags for the data streams with units."""
        tags = self.reader.tags
        units = [self.reader.get_unit(q) for q in self.reader.quantities]
        if self.reader.energy_without_power:
            units += ["W"]
        return [f"{tag}[{unit}]" for unit in units for tag in tags]

    @property
    def output(self):
        """Output file to write the collected data."""
        if self._output is None:
            return f"{self.reader.__class__.__name__.lower()}_series.log"
        else:
            return self._output

    def write_header(self):
        """Write the header to the output file."""
        timestamp_str = datetime.fromtimestamp(time.time()).strftime(
            self._timestamp_fmt
        )
        with open(self.output, "a", encoding="utf-8") as f:
            f.write("# timestamp" + " " * (len(timestamp_str) - 9))
            f.write(" reading-time[ns]")
            for tag in self.tags:
                f.write(f" {tag}")
            f.write("\n")

    def write_data(self, time_series, reading_time, data):
        """Write the collected data to the output file.

        :param time_series: Array of timestamps (in nanoseconds).
        :param reading_time: Array of time taken for each reading (in nanoseconds).
        :param data: 2D array of the collected data. Each row corresponds to a reading,
            and each column corresponds to a quantity read by the reader.
        """

        buffer = ""
        for t, rtime, stream in zip(time_series, reading_time, data):
            buffer += "  " + datetime.fromtimestamp(t / 1e9).strftime(
                self._timestamp_fmt
            )
            buffer += f" {rtime}"
            for v in stream:
                buffer += f" {v}"
            buffer += "\n"

        with open(self.output, "a", encoding="utf-8") as f:
            f.write(buffer)


class TrackerArray(BaseTracker):
    def __init__(
        self,
        readers: list[BaseReader],
        dt_read: float = 1.0,
        dt_write: float = 3600.0,
        outputs: list = [],
        **kwargs,
    ) -> None:
        super().__init__(dt_read)

        if len(outputs) == 0:
            outputs = [None] * len(readers)
        if len(outputs) != len(readers):
            raise ValueError(
                "Length of outputs must be equal to length of readers or zero."
            )

        self.trackers = [
            Tracker(reader, output=o, **kwargs) for reader, o in zip(readers, outputs)
        ]

        self.dt_write = dt_write

    def read(self) -> float:
        """Read data from all readers and store it in the internal buffers.

        :return: Time taken for the reading (in seconds).
        """
        elapsed_s = 0.0
        for tracker in self.trackers:
            elapsed_s += tracker.read()
        return elapsed_s

    def write(self, *, write_header=True, **kwargs):
        """Write header and data to the output file."""
        for tracker in self.trackers:
            if write_header:
                tracker.write_header()
            tracker.write(write_header=False, **kwargs)

    def __enter__(self):
        """Enter the context manager.

        Start the asynchronous task to update and store the power series.
        """
        for tracker in self.trackers:
            tracker.write_header()
        super().start(self.dt_write, write_header=False)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        super().stop()
        self.write(write_header=False)
        return None

    def track_until_forced_exit(self, dt_write: Optional[float] = None, **kwargs):
        for tracker in self.trackers:
            tracker.write_header()
        try:
            super().track_until_forced_exit(dt_write, write_header=False, **kwargs)
            self.write(write_header=False)
        except Exception:
            # Propagate other exceptions
            self.write(write_header=False)
            raise
