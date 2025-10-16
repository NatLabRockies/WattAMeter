# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from abc import abstractmethod
from enum import Enum


class SIPrefix(Enum):
    """An enumeration of SI prefixes."""

    NONE = 1.0
    NANO = 1e-9
    MICRO = 1e-6
    MILLI = 1e-3
    KILO = 1e3
    MEGA = 1e6
    GIGA = 1e9
    TERA = 1e12

    # Addendum for binary prefixes
    KIBI = 2**10
    MIBI = 2**20
    GIBI = 2**30
    TEBI = 2**40
    PEBI = 2**50

    @classmethod
    def from_string(cls, prefix: str) -> "SIPrefix":
        """Get the SIPrefix enum member from a string.

        :param prefix: The SI prefix as a string (e.g., "m" for milli, "k" for kilo).
        :raises ValueError: If the prefix is not recognized.
        """
        mapping = {
            "": cls.NONE,
            "n": cls.NANO,
            "u": cls.MICRO,
            "m": cls.MILLI,
            "k": cls.KILO,
            "M": cls.MEGA,
            "G": cls.GIGA,
            "T": cls.TERA,
            "Ki": cls.KIBI,
            "Mi": cls.MIBI,
            "Gi": cls.GIBI,
            "Ti": cls.TEBI,
            "Pi": cls.PEBI,
        }
        if prefix in mapping:
            return mapping[prefix]
        else:
            raise ValueError(f"Unknown SI prefix: {prefix}")


class Unit(str):
    """Default unit class."""

    @staticmethod
    def symbol() -> str:
        """Return the symbol of the unit."""
        return ""

    def __new__(cls, si_prefix_str: str = ""):
        return super().__new__(cls, si_prefix_str + cls.symbol())

    def __init__(self, si_prefix_str: str = "") -> None:
        super().__init__()
        self.si_prefix = SIPrefix.from_string(si_prefix_str)

    def to_si(self) -> float:
        """Convert 1 unit to the SI unit."""
        return self.si_prefix.value


class Second(Unit):
    """Second unit."""

    @staticmethod
    def symbol() -> str:
        return "s"

    def to_si(self) -> float:
        return self.si_prefix.value


class Joule(Unit):
    """Joule unit."""

    @staticmethod
    def symbol() -> str:
        return "J"

    def to_si(self) -> float:
        return self.si_prefix.value


class WattHour(Unit):
    """Watt-hour unit."""

    @staticmethod
    def symbol() -> str:
        return "Wh"

    def to_si(self) -> float:
        return self.si_prefix.value * 3600.0  # 1 Wh = 3600 J


class Watt(Unit):
    """Watt unit."""

    @staticmethod
    def symbol() -> str:
        return "W"

    def to_si(self) -> float:
        return self.si_prefix.value


class Celsius(Unit):
    """Celsius unit."""

    @staticmethod
    def symbol() -> str:
        return "C"

    def to_si(self) -> float:
        return self.si_prefix.value


class Byte(Unit):
    """Byte unit."""

    @staticmethod
    def symbol() -> str:
        return "B"

    def to_si(self) -> float:
        return self.si_prefix.value


class Quantity(float):
    """A base class for physical quantities."""

    @staticmethod
    @abstractmethod
    def units() -> list[type[Unit]]:
        """Return a list of possible units for this quantity."""
        pass


class Energy(Quantity):
    """A physical quantity representing energy."""

    @staticmethod
    def units() -> list[type[Unit]]:
        return [Joule, WattHour]


class Power(Quantity):
    """A physical quantity representing power."""

    @staticmethod
    def units() -> list[type[Unit]]:
        return [Watt]


class Temperature(Quantity):
    """A physical quantity representing temperature."""

    @staticmethod
    def units() -> list[type[Unit]]:
        return [Celsius]


class Utilization(Quantity):
    """Percentage utilization quantity."""

    @staticmethod
    def units() -> list[type[Unit]]:
        return [Unit]
