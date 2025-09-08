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

    @property
    def derived_quantities(self):
        return []

    @property
    def derived_tags(self):
        return []


def test_quantities():
    reader = DummyReader([Energy, Power])
    assert reader.quantities == [Energy, Power]


def test_tags():
    reader = DummyReader([Energy])
    assert reader.tags == ["tag1", "tag2"]


def test_read():
    reader = DummyReader([Energy])
    assert reader.read() == [1, 2]


def test_get_unit():
    reader = DummyReader([Energy, Power])
    assert isinstance(reader.get_unit(Energy), Joule)
    assert isinstance(reader.get_unit(Power), Watt)

    class DummyQuantity(Quantity):
        @staticmethod
        def units():
            return [Unit]

    assert isinstance(reader.get_unit(DummyQuantity), Unit)


def test_compute_derived():
    reader = DummyReader([Energy])
    # Should just return [] for default DummyReader
    assert reader.compute_derived([0, 1], [[1, 2], [3, 4]]) == []


def test_derived_quantities_and_tags():
    reader = DummyReader([Energy])
    assert isinstance(reader.derived_quantities, list)
    assert reader.derived_quantities == []
    assert isinstance(reader.derived_tags, list)
    assert reader.derived_tags == []
