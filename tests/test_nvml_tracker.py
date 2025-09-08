from wattameter import Tracker
from wattameter.readers import NVMLReader, Power
import time
import pytest


def test_integration_of_power_tracker():
    reader = NVMLReader((Power,))
    if len(reader.tags) == 0:
        pytest.skip("No NVML devices found, skipping test.")

    tracker = Tracker(reader, dt_read=0.1)

    # Read
    tracker.start()
    e0 = reader.read_energy_on_device(0)
    time.sleep(10)
    tracker.stop()
    e1 = reader.read_energy_on_device(0)

    # Collect power and time data
    power_data = [p[0] for p in tracker.data]  # Power data for device 0

    # Integrate power using trapezoidal rule
    t = list(tracker.time_series)
    energy_from_power = 0.0
    for i in range(1, len(power_data)):
        energy_from_power += (0.5 * (power_data[i] + power_data[i - 1])) * (
            t[i] - t[i - 1]
        )
    energy_from_power *= 1e-3 * 1e-9  # Convert from mW*ns to J

    # Energy difference from NVML
    delta_e = (e1 - e0) * 1e-3  # Convert from millijoules to joules

    # Assert that the two energy calculations are at least 2% close
    assert pytest.approx(delta_e, rel=0.02) == energy_from_power, (
        f"Delta E from NVML: {delta_e} J, Integrated Energy from Power: {energy_from_power} J"
    )


if __name__ == "__main__":
    test_integration_of_power_tracker()
