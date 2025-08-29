import numpy as np

from wattameter.readers.base import BaseReader
from wattameter.readers.utils import Quantity, Energy, Power, Unit, Joule, Watt


class DummyReader(BaseReader):
    def __init__(self, quantities):
        super().__init__(quantities)

    @property
    def tags(self):
        return ["tag1", "tag2"]

    def read(self):
        return [1, 2]

    def get_unit(self, quantity: type[Quantity]) -> Unit:
        units = {Energy: Joule(), Power: Watt()}
        return units.get(quantity, Unit())


def test_energy_without_power_true():
    reader = DummyReader([Energy])
    assert reader.energy_without_power is True


def test_energy_without_power_false():
    reader = DummyReader([Energy, Power])
    assert reader.energy_without_power is False


def test_compute_energy_delta_empty():
    reader = DummyReader([Energy])
    arr = np.array([])
    result = reader.compute_energy_delta(arr)
    assert result.size == 0


def test_compute_energy_delta_single():
    reader = DummyReader([Energy])
    arr = np.array([10])
    result = reader.compute_energy_delta(arr)
    assert np.all(result == np.zeros(0))


def test_compute_energy_delta_multiple():
    reader = DummyReader([Energy])
    arr = np.array([10, 15, 25])
    result = reader.compute_energy_delta(arr)
    assert np.all(result == np.array([5, 10]))


def test_compute_power_series_1d():
    reader = DummyReader([Energy])
    time_series = np.array([0, 1, 2])
    energy_data = np.array([0, 10, 30])
    power = reader.compute_power_series(time_series, energy_data)
    assert np.allclose(power, np.array([10, 20, 0]))


def test_compute_power_series_2d():
    reader = DummyReader([Energy])
    time_series = np.array([0, 1, 2])
    energy_data = np.array([[0, 0], [10, 20], [30, 60]])
    power = reader.compute_power_series(time_series, energy_data)
    assert np.allclose(power, np.array([[10, 20], [20, 40], [0, 0]]))
