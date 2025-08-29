import numpy as np

from wattameter.readers.base import BaseReader


class DummyReader(BaseReader):
    def __init__(self, quantities):
        super().__init__(quantities)

    @property
    def tags(self):
        return ["tag1", "tag2"]

    def read(self):
        return [1, 2]

    def get_unit(self, quantity: str) -> str:
        units = {"energy": "J", "power": "W"}
        return units.get(quantity, "")


def test_energy_without_power_true():
    reader = DummyReader(["energy"])
    assert reader.energy_without_power is True


def test_energy_without_power_false():
    reader = DummyReader(["energy", "power"])
    assert reader.energy_without_power is False


def test_compute_energy_delta_empty():
    reader = DummyReader(["energy"])
    arr = np.array([])
    result = reader.compute_energy_delta(arr)
    assert result.size == 0


def test_compute_energy_delta_single():
    reader = DummyReader(["energy"])
    arr = np.array([10])
    result = reader.compute_energy_delta(arr)
    assert np.all(result == np.zeros(0))


def test_compute_energy_delta_multiple():
    reader = DummyReader(["energy"])
    arr = np.array([10, 15, 25])
    result = reader.compute_energy_delta(arr)
    assert np.all(result == np.array([5, 10]))


def test_compute_power_series_1d():
    reader = DummyReader(["energy"])
    time_series = np.array([0, 1, 2])
    energy_data = np.array([0, 10, 30])
    # get_conversion_factor("J") returns 1, so power = delta_energy / delta_time
    power = reader.compute_power_series(time_series, energy_data)
    assert np.allclose(power, np.array([10, 20, 0]))


def test_compute_power_series_2d():
    reader = DummyReader(["energy"])
    time_series = np.array([0, 1, 2])
    energy_data = np.array([[0, 0], [10, 20], [30, 60]])
    power = reader.compute_power_series(time_series, energy_data)
    assert np.allclose(power, np.array([[10, 20], [20, 40], [0, 0]]))
