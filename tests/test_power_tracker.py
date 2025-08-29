from wattameter import Tracker
from wattameter.readers import RAPLReader, BaseReader, NVMLReader
import time
import pytest


@pytest.mark.parametrize("reader", [RAPLReader(), NVMLReader()])
def test_start_stop_write(reader: BaseReader):
    tracker = Tracker(reader)
    tracker.start()
    time.sleep(5)  # Allow some time for tracking
    tracker.stop()
    tracker.write_header()
    tracker.write_data(*tracker.flush_data())
