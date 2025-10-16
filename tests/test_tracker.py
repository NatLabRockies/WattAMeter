"""
Test suite for tracker.py module.

This module tests all tracker classes (BaseTracker, Tracker, TrackerArray) with
particular focus on the track_until_forced_exit method functionality, including:
- Header writing behavior
- Final operations in finally block
- Exception handling (KeyboardInterrupt vs others)
- Periodic write operations based on freq_write parameter
- Parameter passing between subclasses and base class
"""

import pytest
import logging
import tempfile
import os
import time
import threading
from unittest.mock import patch
import numpy as np
from collections import deque

# Add the src directory to the path so we can import our module
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wattameter.tracker import BaseTracker, Tracker, TrackerArray
from wattameter.readers import (
    BaseReader,
    Unit,
    Power,
    Energy,
    Watt,
    Joule,
    Temperature,
    Celsius,
)


class MockReader(BaseReader):
    """Mock reader for testing purposes."""

    def __init__(
        self,
        quantities=(Power,),
        read_return_value=None,
        read_delay=0.0,
    ):
        super().__init__(quantities)
        self.read_return_value = read_return_value or [100, 200]
        self.read_delay = read_delay
        self.read_count = 0

    @property
    def tags(self):
        return ["device0[W]", "device1[W]"]

    def get_unit(self, quantity) -> Unit:
        units = {Power: Watt(), Energy: Joule(), Temperature: Celsius()}
        return units.get(quantity, Unit())

    def read(self):
        self.read_count += 1
        if self.read_delay > 0:
            time.sleep(self.read_delay)
        return (
            self.read_return_value.copy()
            if isinstance(self.read_return_value, list)
            else self.read_return_value
        )


class ConcreteTracker(BaseTracker):
    """Concrete implementation of BaseTracker for testing."""

    def __init__(self, dt_read: float = 1.0):
        super().__init__(dt_read)
        self.read_calls = []
        self.write_calls = []
        self.write_header_calls = []

    def read(self) -> float:
        start_time = time.perf_counter()
        # Simulate some work
        time.sleep(0.001)
        elapsed = time.perf_counter() - start_time
        self.read_calls.append(elapsed)
        return elapsed

    def write(self) -> None:
        self.write_calls.append(time.time())

    def write_header(self) -> None:
        self.write_header_calls.append(time.time())


class TestBaseTracker:
    """Test cases for BaseTracker abstract class."""

    def test_init(self):
        """Test BaseTracker initialization."""
        tracker = ConcreteTracker(dt_read=2.0)
        assert tracker.dt_read == 2.0
        assert tracker._async_thread is None

    def test_read_and_sleep_normal_case(self):
        """Test _read_and_sleep when read time is less than dt_read."""
        tracker = ConcreteTracker(dt_read=0.1)

        start_time = time.perf_counter()
        tracker._read_and_sleep()
        total_time = time.perf_counter() - start_time

        # Should take approximately dt_read time
        assert 0.09 <= total_time <= 0.15  # Allow some tolerance
        assert len(tracker.read_calls) == 1

    def test_read_and_sleep_slow_read(self, caplog):
        """Test _read_and_sleep when read time exceeds dt_read."""
        # Mock read to take longer than dt_read
        tracker = ConcreteTracker(dt_read=0.001)

        with patch.object(tracker, "read", return_value=0.01):  # 10ms read time
            with caplog.at_level(logging.WARNING):
                tracker._read_and_sleep()

        assert "Time taken for reading" in caplog.text

    def test_start_success(self):
        """Test successful start of async thread."""
        tracker = ConcreteTracker(dt_read=0.1)

        tracker.start()

        assert tracker._async_thread is not None
        assert tracker._async_thread.is_alive()
        assert hasattr(tracker, "_stop_event")

        # Clean up
        tracker.stop()

    def test_start_already_running(self, caplog):
        """Test start when tracker is already running."""
        tracker = ConcreteTracker(dt_read=0.1)

        tracker.start()

        with caplog.at_level(logging.WARNING):
            tracker.start()  # Try to start again

        assert "Tracker is already running" in caplog.text

        # Clean up
        tracker.stop()

    def test_stop_success(self):
        """Test successful stop of async thread."""
        tracker = ConcreteTracker(dt_read=0.1)

        tracker.start()
        assert tracker._async_thread is not None

        tracker.stop()
        assert tracker._async_thread is None

    def test_stop_not_running(self, caplog):
        """Test stop when tracker is not running."""
        tracker = ConcreteTracker(dt_read=0.1)

        with caplog.at_level(logging.WARNING):
            tracker.stop()

        assert "Tracker is not running" in caplog.text

    def test_context_manager(self):
        """Test context manager functionality."""
        tracker = ConcreteTracker(dt_read=0.1)

        with tracker:
            assert tracker._async_thread is not None
            assert tracker._async_thread.is_alive()

        assert tracker._async_thread is None

    def test_update_series_no_write(self):
        """Test _update_series without write interval."""
        tracker = ConcreteTracker(dt_read=0.01)
        stop_event = threading.Event()

        # Start the update series in a thread
        thread = threading.Thread(target=tracker._update_series, args=(stop_event,))
        thread.start()

        # Let it run for a short time
        time.sleep(0.05)
        stop_event.set()
        thread.join(timeout=1.0)

        assert len(tracker.read_calls) > 0
        assert len(tracker.write_calls) == 0

    def test_update_series_with_write(self):
        """Test _update_series with write interval."""
        tracker = ConcreteTracker(dt_read=0.01)
        stop_event = threading.Event()

        # Start the update series with write interval
        thread = threading.Thread(
            target=tracker._update_series,
            args=(stop_event, 2),  # Write every 20ms
        )
        thread.start()

        # Let it run for a short time
        time.sleep(0.05)
        stop_event.set()
        thread.join(timeout=1.0)

        assert len(tracker.read_calls) > 0
        assert len(tracker.write_calls) > 0

    def test_track_until_forced_exit_keyboard_interrupt(self, caplog):
        """Test track_until_forced_exit with KeyboardInterrupt."""
        tracker = ConcreteTracker(dt_read=0.01)

        with patch.object(tracker, "_read_and_sleep", side_effect=KeyboardInterrupt()):
            with caplog.at_level(logging.INFO):
                result = tracker.track_until_forced_exit()

        assert "Forced exit detected" in caplog.text
        assert result is None

    def test_track_until_forced_exit_other_exception(self):
        """Test track_until_forced_exit with other exceptions."""
        tracker = ConcreteTracker(dt_read=0.01)

        with patch.object(
            tracker, "_read_and_sleep", side_effect=ValueError("Test error")
        ):
            with pytest.raises(ValueError, match="Test error"):
                tracker.track_until_forced_exit()

    def test_track_until_forced_exit_final_operations_freq_write_zero(self):
        """Test BaseTracker performs final read but no write when freq_write=0."""
        tracker = ConcreteTracker(dt_read=0.01)

        with patch.object(tracker, "_read_and_sleep", side_effect=KeyboardInterrupt()):
            tracker.track_until_forced_exit(freq_write=0)

        # Final read should occur
        assert len(tracker.read_calls) == 1
        # No writes when freq_write=0
        assert len(tracker.write_calls) == 0
        # BaseTracker doesn't call write_header itself
        assert len(tracker.write_header_calls) == 0

    def test_track_until_forced_exit_final_operations_freq_write_positive(self):
        """Test BaseTracker performs final read and write when freq_write > 0."""
        tracker = ConcreteTracker(dt_read=0.01)

        with patch.object(tracker, "_read_and_sleep", side_effect=KeyboardInterrupt()):
            tracker.track_until_forced_exit(freq_write=5)

        # Final read should occur
        assert len(tracker.read_calls) == 1
        # Final write should occur when freq_write > 0
        assert len(tracker.write_calls) == 1
        # BaseTracker doesn't call write_header itself
        assert len(tracker.write_header_calls) == 0

    def test_track_until_forced_exit_periodic_writes_based_on_freq_write(self):
        """Test BaseTracker performs periodic writes based on freq_write parameter."""
        tracker = ConcreteTracker(dt_read=0.01)

        call_count = 0

        def mock_read_and_sleep():
            nonlocal call_count
            call_count += 1
            if call_count >= 5:  # Stop after 5 calls
                raise KeyboardInterrupt()

        with patch.object(tracker, "_read_and_sleep", side_effect=mock_read_and_sleep):
            tracker.track_until_forced_exit(freq_write=2)

        # Should have periodic writes: at calls 2, 4 + final write = 3 total
        assert len(tracker.write_calls) == 3
        # Should have final read
        assert len(tracker.read_calls) == 1

    def test_track_until_forced_exit_final_operations_always_execute(self):
        """Test that final read/write operations always execute in finally block."""
        tracker = ConcreteTracker(dt_read=0.01)

        # Even with an exception in the loop, final operations should execute
        with patch.object(tracker, "_read_and_sleep", side_effect=KeyboardInterrupt()):
            tracker.track_until_forced_exit(freq_write=1)

        # Final read should always happen
        assert len(tracker.read_calls) == 1
        # Final write should happen when freq_write > 0
        assert len(tracker.write_calls) == 1


@pytest.fixture()
def temp_dir():
    """Fixture to create and clean up a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir)


class TestTracker:
    """Test cases for Tracker class."""

    @pytest.fixture()
    def output_file(self, temp_dir):
        """Fixture to create output file path."""
        return os.path.join(temp_dir, "test_output.log")

    def test_init(self, output_file):
        """Test Tracker initialization."""
        reader = MockReader()
        tracker = Tracker(reader, dt_read=2.0, freq_write=3600, output=output_file)

        assert tracker.reader == reader
        assert tracker.dt_read == 2.0
        assert tracker.freq_write == 3600.0
        assert tracker._output == output_file
        assert isinstance(tracker.time_series, deque)
        assert isinstance(tracker.reading_time, deque)
        assert isinstance(tracker.data, deque)
        assert hasattr(tracker, "_lock")

    def test_read(self, output_file):
        """Test read method stores data correctly."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=1.0, output=output_file)

        elapsed = tracker.read()

        assert isinstance(elapsed, float)
        assert elapsed > 0
        assert len(tracker.time_series) == 1
        assert len(tracker.reading_time) == 1
        assert len(tracker.data) == 1
        assert tracker.data[0] == [10, 20]

    def test_read_multiple_calls(self, output_file):
        """Test multiple read calls accumulate data."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=1.0, output=output_file)

        tracker.read()
        tracker.read()
        tracker.read()

        assert len(tracker.time_series) == 3
        assert len(tracker.reading_time) == 3
        assert len(tracker.data) == 3

    def test_flush_data(self, output_file):
        """Test flush_data returns and clears data."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=1.0, output=output_file)

        # Add some data
        tracker.read()
        tracker.read()

        time_series, reading_time, data = tracker.flush_data()

        # Check returned data
        assert len(time_series) == 2
        assert len(reading_time) == 2
        assert np.asarray(data).shape == (2, 2)  # 2 readings, 2 values each

        # Check data is cleared
        assert len(tracker.time_series) == 0
        assert len(tracker.reading_time) == 0
        assert len(tracker.data) == 0

    def test_output_property_default(self):
        """Test output property with default filename."""
        reader = MockReader()
        tracker = Tracker(reader, dt_read=1.0)

        assert tracker.output == "mockreader_series.log"

    def test_output_property_custom(self):
        """Test output property with custom filename."""
        reader = MockReader()
        tracker = Tracker(reader, dt_read=1.0, output="custom.log")

        assert tracker.output == "custom.log"

    def test_write_header(self, output_file):
        """Test write_header creates proper header."""
        reader = MockReader()
        tracker = Tracker(reader, dt_read=1.0, output=output_file)

        tracker.write_header()

        with open(output_file, "r") as f:
            content = f.read()

        assert "# timestamp" in content
        assert "reading-time[ns]" in content
        assert "device0[W]" in content
        assert "device1[W]" in content

    def test_write_data(self, output_file):
        """Test write_data writes data correctly."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=1.0, output=output_file)

        # Create test data
        time_series = np.array([1000000000, 2000000000])  # nanoseconds
        reading_time = np.array([1000000, 2000000])  # nanoseconds
        data = np.array([[10, 20], [15, 25]])

        tracker.write_data(time_series, reading_time, data)

        with open(output_file, "r") as f:
            content = f.read()

        assert "1000000" in content  # reading time
        assert "10" in content and "20" in content  # data values
        assert "15" in content and "25" in content  # data values

    def test_write_method(self, output_file):
        """Test write method coordinates data writing."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=1.0, output=output_file)

        # Add some data
        tracker.read()

        with (
            patch.object(tracker, "write_data") as mock_data,
            patch.object(
                tracker,
                "flush_data",
                return_value=(np.array([1]), np.array([2]), np.array([[3]])),
            ),
        ):
            tracker.write()

            mock_data.assert_called_once()

    def test_context_manager_writes_header_and_data(self, output_file):
        """Test context manager writes header and final data."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=0.01, output=output_file)

        with (
            patch.object(tracker, "write_header") as mock_header,
            patch.object(tracker, "write") as mock_write,
        ):
            with tracker:
                time.sleep(0.02)  # Let it run briefly

            mock_header.assert_called_once()
            mock_write.assert_called()

    def test_track_until_forced_exit_writes_header_and_data(self, output_file):
        """Test track_until_forced_exit writes header and final data."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=0.01, output=output_file)

        with (
            patch.object(tracker, "write_header") as mock_header,
            patch.object(tracker, "write") as mock_write,
            patch.object(tracker, "_read_and_sleep", side_effect=KeyboardInterrupt()),
        ):
            tracker.track_until_forced_exit()

            mock_header.assert_called_once()
            mock_write.assert_called()

    def test_track_until_forced_exit_writes_header_to_file(self, output_file):
        """Test track_until_forced_exit actually writes header to output file."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=0.01, output=output_file)

        with patch.object(tracker, "_read_and_sleep", side_effect=KeyboardInterrupt()):
            tracker.track_until_forced_exit()

        # Check that header was written to file
        assert os.path.exists(output_file)
        with open(output_file, "r") as f:
            content = f.read()
            assert "# timestamp" in content
            assert "reading-time[ns]" in content
            assert "device0[W]" in content
            assert "device1[W]" in content

    def test_track_until_forced_exit_uses_instance_freq_write(self, output_file):
        """Test Tracker passes its instance freq_write to base class method."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(reader, dt_read=0.01, freq_write=7, output=output_file)

        # Mock the base class method to verify correct parameter passing
        with patch.object(BaseTracker, "track_until_forced_exit") as mock_base:
            tracker.track_until_forced_exit()

        # Verify base method was called with instance's freq_write
        mock_base.assert_called_once_with(7)

    def test_track_until_forced_exit_final_operations_file_output(self, output_file):
        """Test final operations create actual file output."""
        reader = MockReader(read_return_value=[10, 20])
        tracker = Tracker(
            reader, dt_read=0.01, freq_write=100, output=output_file
        )  # High freq to avoid periodic writes

        with patch.object(tracker, "_read_and_sleep", side_effect=KeyboardInterrupt()):
            tracker.track_until_forced_exit()

        # File should exist and have both header and some data
        assert os.path.exists(output_file)
        with open(output_file, "r") as f:
            content = f.read()
            assert "# timestamp" in content  # Header
            # Should have at least one data line from final operations


class TestTrackerArray:
    """Test cases for TrackerArray class."""

    def test_init_no_outputs(self):
        """Test TrackerArray initialization without specified outputs."""
        readers = [MockReader(), MockReader()]
        # Use type: ignore to suppress the type checker warning for tests
        tracker_array = TrackerArray(readers, dt_read=1.0, freq_write=3600.0)  # type: ignore

        assert len(tracker_array.trackers) == 2
        assert tracker_array.dt_read == 1.0
        assert tracker_array.freq_write == 3600.0

    def test_init_with_outputs(self):
        """Test TrackerArray initialization with specified outputs."""
        readers = [MockReader(), MockReader()]
        outputs = ["output1.log", "output2.log"]
        tracker_array = TrackerArray(readers, dt_read=1.0, outputs=outputs)  # type: ignore

        assert len(tracker_array.trackers) == 2
        assert tracker_array.trackers[0]._output == "output1.log"
        assert tracker_array.trackers[1]._output == "output2.log"

    def test_init_mismatched_outputs(self):
        """Test TrackerArray initialization with mismatched outputs length."""
        readers = [MockReader(), MockReader()]
        outputs = ["output1.log"]  # Only one output for two readers

        with pytest.raises(ValueError, match="Length of outputs must be equal"):
            TrackerArray(readers, dt_read=1.0, outputs=outputs)  # type: ignore

    def test_read(self):
        """Test read method reads from all trackers."""
        readers = [MockReader(read_delay=0.001), MockReader(read_delay=0.001)]
        tracker_array = TrackerArray(readers, dt_read=1.0)  # type: ignore

        elapsed = tracker_array.read()

        assert isinstance(elapsed, float)
        assert elapsed > 0
        # Each tracker should have been read once
        for tracker in tracker_array.trackers:
            assert len(tracker.time_series) == 1

    def test_write(self, temp_dir):
        """Test write method writes from all trackers."""
        readers = [MockReader(), MockReader()]
        outputs = [os.path.join(temp_dir, f"output{i}.log") for i in range(2)]
        tracker_array = TrackerArray(readers, dt_read=1.0, outputs=outputs)  # type: ignore

        # Add some data to each tracker
        for tracker in tracker_array.trackers:
            tracker.read()

        tracker_array.write()

        # Check that files were created
        for output in outputs:
            assert os.path.exists(output)

    def test_context_manager(self, temp_dir):
        """Test TrackerArray context manager functionality."""
        readers = [MockReader(), MockReader()]
        outputs = [os.path.join(temp_dir, f"output{i}.log") for i in range(2)]
        tracker_array = TrackerArray(readers, dt_read=0.01, outputs=outputs)  # type: ignore

        with tracker_array:
            time.sleep(0.02)  # Let it run briefly

        # Check that files were created and have content
        for output in outputs:
            assert os.path.exists(output)
            with open(output, "r") as f:
                content = f.read()
                assert len(content) > 0
                assert "timestamp" in content

    def test_track_until_forced_exit(self, temp_dir):
        """Test TrackerArray track_until_forced_exit method."""
        readers = [MockReader(), MockReader()]
        outputs = [os.path.join(temp_dir, f"output{i}.log") for i in range(2)]
        tracker_array = TrackerArray(readers, dt_read=0.01, outputs=outputs)  # type: ignore

        with patch.object(
            tracker_array, "_read_and_sleep", side_effect=KeyboardInterrupt()
        ):
            tracker_array.track_until_forced_exit()

        # Check that files were created
        for output in outputs:
            assert os.path.exists(output)

    def test_track_until_forced_exit_writes_headers_for_all_trackers(self, temp_dir):
        """Test TrackerArray writes headers for all its child trackers."""
        readers = [MockReader(), MockReader()]
        outputs = [os.path.join(temp_dir, f"array_test_{i}.log") for i in range(2)]
        tracker_array = TrackerArray(
            readers, dt_read=0.01, freq_write=5, outputs=outputs
        )  # type: ignore

        with patch.object(
            tracker_array, "_read_and_sleep", side_effect=KeyboardInterrupt()
        ):
            tracker_array.track_until_forced_exit()

        # Both output files should exist with headers
        for output in outputs:
            assert os.path.exists(output)
            with open(output, "r") as f:
                content = f.read()
                assert content.startswith("# timestamp")
                assert "device0[W]" in content
                assert "device1[W]" in content

    def test_track_until_forced_exit_uses_instance_freq_write(self, temp_dir):
        """Test TrackerArray passes its instance freq_write to base class method."""
        readers = [MockReader(), MockReader()]
        outputs = [os.path.join(temp_dir, f"freq_test_{i}.log") for i in range(2)]
        tracker_array = TrackerArray(
            readers, dt_read=0.01, freq_write=9, outputs=outputs
        )  # type: ignore

        # Mock the base class method to verify correct parameter passing
        with patch.object(BaseTracker, "track_until_forced_exit") as mock_base:
            tracker_array.track_until_forced_exit()

        # Verify base method was called with instance's freq_write
        mock_base.assert_called_once_with(9)


class TestIntegration:
    """Integration tests for tracker functionality."""

    def test_full_tracking_workflow(self, temp_dir):
        """Test complete tracking workflow from start to finish."""
        reader = MockReader(read_return_value=[100, 200])
        output_file = os.path.join(temp_dir, "tracking_test.log")
        tracker = Tracker(reader, dt_read=0.01, freq_write=5, output=output_file)

        # Run tracker for a short time
        start_time = time.time()
        with tracker:
            while time.time() - start_time < 0.1:  # Run for 100ms
                time.sleep(0.01)

        # Verify file was created and has expected content
        assert os.path.exists(output_file)

        with open(output_file, "r") as f:
            content = f.read()

        assert "timestamp" in content
        assert "reading-time[ns]" in content
        assert "device0[W]" in content
        assert "100" in content  # Data values
        assert "200" in content

    def test_threading_safety(self):
        """Test that tracker is thread-safe."""
        reader = MockReader(read_return_value=[50, 100])
        tracker = Tracker(reader, dt_read=0.01)

        def reader_thread():
            for _ in range(10):
                tracker.read()
                time.sleep(0.001)

        # Start multiple threads reading simultaneously
        threads = [threading.Thread(target=reader_thread) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have 30 readings total (10 per thread * 3 threads)
        assert len(tracker.time_series) == 30
        assert len(tracker.data) == 30


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    # # Run tests
    # pytest.main([__file__, "-v"])

    TestBaseTracker().test_update_series_no_write()
