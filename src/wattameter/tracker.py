# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from .readers import BaseReader
from .readers.utils import Second

from contextlib import AbstractContextManager
import logging
import time
import threading
from collections import deque
from datetime import datetime
from abc import abstractmethod
from itertools import zip_longest

logger = logging.getLogger(__name__)


class BaseTracker(AbstractContextManager):
    """Base class for trackers that read data at a specified frequency.

    :param dt_read: Time interval (in seconds) between consecutive readings.
    """

    def __init__(self, dt_read: float = 1.0) -> None:
        super().__init__()
        self.dt_read = dt_read

        # Read scheduler for asynchronous reading
        self._async_thread = None  #: Asynchronous thread for reading data.

    @abstractmethod
    def read(self) -> float:
        """Read data.

        :return: Time taken for the reading (in seconds).
        """
        pass

    @abstractmethod
    def write_header(self) -> None:
        """Write header."""
        pass

    @abstractmethod
    def write(self) -> None:
        """Write data."""
        pass

    def _read_and_sleep(self):
        """Read data and sleep to maintain the desired frequency."""
        # Read data from the reader
        elapsed_s = self.read()

        # Sleep for the remaining time if needed
        if elapsed_s < self.dt_read:
            time.sleep(self.dt_read - elapsed_s)
        else:
            logger.warning(f"Time taken for reading: {elapsed_s:.3e} seconds.")

    def _update_series(self, event, freq_write: int = 0):
        """Asynchronous task that reads data and writes it at specified intervals.

        :param event: threading.Event to signal when to stop the task.
        :param freq_write: Frequency (in number of reads) to write the collected data.
            If set to 0, data is never written.
        """
        if freq_write == 0:
            while not event.is_set():
                self._read_and_sleep()
        else:
            read_count = 0
            while not event.is_set():
                self._read_and_sleep()
                read_count += 1
                if read_count >= freq_write:
                    self.write()
                    read_count = 0

    def start(self, freq_write: int = 0):
        """Start asynchronous task :meth:`_update_series`.

        :param freq_write: Frequency (in number of reads) to write the collected data.
            If set to 0, data is never written.
        """
        if freq_write > 0:
            self.write_header()  # Write header at the beginning
        if self._async_thread is None:
            # Define the async task to update the time series
            self._stop_event = threading.Event()
            self._async_thread = threading.Thread(
                target=self._update_series,
                args=(self._stop_event, freq_write),
                daemon=True,
            )

            # Start the async task
            self._async_thread.start()
        else:
            logger.warning("Tracker is already running. Use stop() to stop it first.")

    def stop(self, freq_write: int = 0):
        """Stop async task :meth:`_update_series` and reads data one last time.

        On exit, perform a final read and write of the collected data.

        :param freq_write: Frequency (in number of reads) to write the collected data.
            If set to 0, data is never written.
        """
        if self._async_thread is not None:
            # Wait for the async task to finish
            self._stop_event.set()
            self._async_thread.join()

            # Mark the async thread as stopped
            self._async_thread = None

            # Final read/write to capture end of the series
            self.read()
            if freq_write > 0:
                self.write()
        else:
            logger.warning("Tracker is not running. Nothing to stop.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        if exc_type is not None:
            logger.error(
                "Exception in context:", exc_info=(exc_type, exc_value, traceback)
            )
        return None

    def track_until_forced_exit(self, freq_write: int = 0, *args, **kwargs):
        """Track data as the main task of the program until a forced exit.

        On exit, perform a final read and write of the collected data.

        .. note::

            This is the preferred way to track data of programs that are being
            executed in the machine. This method will block the main thread
            until a forced exit is detected (e.g., SIGINT or SIGTERM).

        :param freq_write: Frequency (in number of reads) to write the collected data.
            If set to 0, data is never written.
        """
        try:
            if freq_write == 0:
                while True:
                    self._read_and_sleep()
            else:
                read_count = 0
                while True:
                    self._read_and_sleep()
                    read_count += 1
                    if read_count >= freq_write:
                        self.write()
                        read_count = 0
        except KeyboardInterrupt:
            logger.info("Forced exit detected. Stopping tracker...")
        finally:
            # Final read/write to capture end of the series
            self.read()
            if freq_write > 0:
                self.write()


class Tracker(BaseTracker):
    """Generic tracker that reads data from a BaseReader at a specified frequency.

    :param reader: An instance of BaseReader to read data from.
    :param dt_read: Time interval (in seconds) between consecutive readings.
    :param freq_write: Frequency (in number of reads) to write the collected data.
        If set to 0, data is never written.
    :param output: Optional output stream to write the collected data. If not provided,
        the output stream is as defined in :meth:`output`.

    .. attribute:: reader

        An instance of BaseReader that provides the data to be tracked.

    .. attribute:: time_series

        A deque that stores the timestamps of the readings.

    .. attribute:: reading_time

        A deque that stores the time taken for each reading (in nanoseconds).
        This information can be useful for adjusting the reading frequency.
        Usually, the time taken for reading should be much smaller than
        :attr:`dt_read`.

    .. attribute:: data

        A deque that stores the data read from the reader.

    .. attribute:: freq_write

        Frequency (in number of reads) to write the collected data.
        If set to 0, data is never written.
    """

    def __init__(
        self,
        reader: BaseReader,
        dt_read: float = 1.0,
        freq_write: int = 3600,
        output=None,
    ) -> None:
        super().__init__(dt_read)

        # For reading data
        self.reader = reader
        if len(self.reader.tags) == 0:
            raise ValueError("Reader must have at least one tag.")

        # Time series and data storage
        self.time_series = deque([])
        self.reading_time = deque([])
        self.data = deque([])
        self._lock = threading.Lock()  #: Lock for thread-safe operations.

        # Output options
        self.freq_write = freq_write
        self._timestamp_fmt = "%Y-%m-%d_%H:%M:%S.%f"
        self._output = output

    def read(self) -> float:
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

    def write(self):
        self.write_data(*self.flush_data())

    def __enter__(self):
        super().start(self.freq_write)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        super().stop(self.freq_write)
        if exc_type is not None:
            logger.error(
                "Exception in context:", exc_info=(exc_type, exc_value, traceback)
            )
        return None

    def track_until_forced_exit(self):
        self.write_header()  # Write header at the beginning
        super().track_until_forced_exit(self.freq_write)

    def flush_data(self):
        """Flush all collected data from the tracker.

        :return: A tuple containing three lists:

            - time_series: List of timestamps (in nanoseconds).
            - reading_time: List of time taken for each reading (in nanoseconds).
            - data: 2D array of the collected data. Each row corresponds to a reading,
              and each column corresponds to a quantity read by the reader.
        """
        with self._lock:
            # Copy data to lists and clear the deques
            time_series = list(self.time_series)
            reading_time = list(self.reading_time)
            data = list(self.data)
            # Clear the deques
            self.time_series.clear()
            self.reading_time.clear()
            self.data.clear()

        return time_series, reading_time, data

    @property
    def output(self):
        """Output file to write the collected data."""
        if self._output is None:
            return f"{self.reader.__class__.__name__.lower()}_series.log"
        else:
            return self._output

    def format_timestamp(self, timestamp_ns: int) -> str:
        """Format a timestamp in nanoseconds to a human-readable string.

        :param timestamp_ns: Timestamp in nanoseconds.
        """
        return datetime.fromtimestamp(timestamp_ns / 1e9).strftime(self._timestamp_fmt)

    def write_header(self):
        """Write the header to the output stream."""
        timestamp_str = self.format_timestamp(time.time_ns())
        with open(self.output, "a", encoding="utf-8") as f:
            f.write("# timestamp" + " " * (len(timestamp_str) - 9))
            f.write(" reading-time[ns]")
            for tag in self.reader.tags:
                f.write(f" {tag}")
            for tag in self.reader.derived_tags:
                f.write(f" {tag}")
            f.write("\n")

    def write_data(self, time_series, reading_time, data):
        """Write the collected data to the output stream.

        :param time_series: Array of timestamps (in nanoseconds).
        :param reading_time: Array of time taken for each reading (in nanoseconds).
        :param data: 2D array of the collected data. Each row corresponds to a reading,
            and each column corresponds to a quantity read by the reader.
        """

        # Get derived quantities if available
        derived_data = self.reader.compute_derived(
            time_series, data, time_unit=Second("n")
        )

        buffer = ""
        for t, rtime, stream0, stream1 in zip_longest(
            time_series, reading_time, data, derived_data, fillvalue=[]
        ):
            buffer += "  " + self.format_timestamp(t)
            buffer += f" {rtime}"
            for v in stream0:
                buffer += f" {v}"
            for v in stream1:
                buffer += f" {v}"
            buffer += "\n"

        with open(self.output, "a", encoding="utf-8") as f:
            f.write(buffer)


class TrackerArray(BaseTracker):
    """Tracker that manages multiple :class:`Tracker` instances.

    :param readers: List of :class:`BaseReader` instances to read data from.
    :param dt_read: Time interval (in seconds) between consecutive readings.
    :param freq_write: Frequency (in number of reads) to write the collected data.
        If set to 0, data is never written.
    :param outputs: List of output streams for each tracker. If not provided,
        the output streams are as defined in each tracker's :meth:`output`.

    .. attribute:: trackers

        List of :class:`Tracker` instances managed by this tracker.

    .. attribute:: freq_write

        Frequency (in number of reads) to write the collected data.
        If set to 0, data is never written.
    """

    def __init__(
        self,
        readers: list[BaseReader],
        dt_read: float = 1.0,
        freq_write: int = 3600,
        outputs: list = [],
    ) -> None:
        super().__init__(dt_read)

        if len(outputs) == 0:
            outputs = [None] * len(readers)
        if len(outputs) != len(readers):
            raise ValueError(
                "Length of outputs must be equal to length of readers or zero."
            )

        self.trackers = [
            Tracker(reader, output=o) for reader, o in zip(readers, outputs)
        ]

        self.freq_write = freq_write

    def read(self) -> float:
        elapsed_s = 0.0
        for tracker in self.trackers:
            elapsed_s += tracker.read()
        return elapsed_s

    def write_header(self) -> None:
        for tracker in self.trackers:
            tracker.write_header()

    def write(self):
        for tracker in self.trackers:
            tracker.write()

    def __enter__(self):
        super().start(self.freq_write)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        super().stop(self.freq_write)
        if exc_type is not None:
            logger.error(
                "Exception in context:", exc_info=(exc_type, exc_value, traceback)
            )
        return None

    def track_until_forced_exit(self):
        self.write_header()
        super().track_until_forced_exit(self.freq_write)
