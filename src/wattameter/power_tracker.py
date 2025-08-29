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

logger = logging.getLogger(__name__)


class BaseTracker(AbstractContextManager):
    def __init__(self, freq: float = 1.0) -> None:
        super().__init__()
        self.freq = freq

        # Read scheduler for asynchronous reading
        self._async_thread = None
        self._lock = threading.Lock()

    @abstractmethod
    def read(self) -> float:
        """Read data.

        :return: Time taken for the reading (in seconds).
        """
        pass

    def _read_and_sleep(self):
        """Read data from the reader and sleep to maintain the desired frequency."""
        # Read data from the reader
        elapsed_s = self.read()

        # Sleep for the remaining time if needed
        if self.freq * elapsed_s < 1.0:
            time.sleep((1 / self.freq) - elapsed_s)
        else:
            logger.warning(
                f"Please decrease `freq` value. "
                f"Current value: {self.freq:.3e} (read every {(1 / self.freq):.3e} seconds). "
                f"Time taken for reading: {elapsed_s:.3e} seconds."
            )

    def _update_series(self, event):
        """Asynchronous task to update the power series at the specified frequency.

        :param event: threading.Event to signal when to stop the task.
        """
        while not event.is_set():
            self._read_and_sleep()

    def start(self):
        """Start the asynchronous task to update the power series."""
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

    def track_until_forced_exit(self):
        """Track power and energy consumption until a forced exit."""
        try:
            while True:
                self._read_and_sleep()
        except KeyboardInterrupt:
            logger.info("Forced exit detected. Stopping tracker...")
        except Exception as e:
            # Propagate other exceptions
            raise e
        finally:
            return None


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

    def __init__(self, reader: BaseReader, freq: float = 1.0, output=None) -> None:
        super().__init__(freq)

        # For reading data
        self.reader = reader

        # Time series and data storage
        self.time_series = deque([])
        self.reading_time = deque([])
        self.data = deque([])

        # Output options
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

        # Store the data in the deques
        with self._lock:
            self.time_series.append(timestamp)
            self.reading_time.append(elapsed)
            self.data.append(data)

        elapsed_s = elapsed / 1e9  # Convert to seconds
        logger.debug(f"Read completed in {elapsed_s:.3e} seconds.")

        return elapsed_s

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        super().__exit__(exc_type, exc_value, traceback)
        self.write(*self.flush_data())
        return None

    def track_until_forced_exit(self):
        """Track power and energy consumption until a forced exit."""
        try:
            super().track_until_forced_exit()
            self.write(*self.flush_data())
        except Exception as e:
            self.write(*self.flush_data())
            logger.error(f"An error occurred: {e}")
        finally:
            return None

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

    def write(self, time_series, reading_time, data):
        """Write header and data to the output file."""
        self.write_header()
        self.write_data(time_series, reading_time, data)


class TrackerArray(BaseTracker):
    def __init__(self, readers: list[BaseReader], freq: float = 1.0, **kwargs) -> None:
        super().__init__(freq)
        self.trackers = [Tracker(reader, output=None, **kwargs) for reader in readers]

    def read(self) -> float:
        """Read data from all readers and store it in the internal buffers.

        :return: Time taken for the reading (in seconds).
        """
        elapsed_s = 0.0
        for tracker in self.trackers:
            elapsed_s += tracker.read()
        return elapsed_s

    def write(self):
        """Write header and data to the output file for all trackers."""
        for tracker in self.trackers:
            tracker.write(*tracker.flush_data())

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        super().__exit__(exc_type, exc_value, traceback)
        self.write()
        return None

    def track_until_forced_exit(self):
        """Track power and energy consumption until a forced exit."""
        try:
            super().track_until_forced_exit()
            self.write()
        except Exception as e:
            self.write()
            logger.error(f"An error occurred: {e}")
        finally:
            return None
