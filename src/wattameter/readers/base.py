from abc import ABC, abstractmethod
from typing import Sequence
import numpy as np
import logging

from .utils import get_conversion_factor


# Module-level logger
logger = logging.getLogger(__name__)


class BaseReader(ABC):
    """Base class for all readers."""

    UNITS = {}

    def __init__(self, quantities: Sequence[str]) -> None:
        """Initialize the reader with the specified quantities."""
        self.quantities = quantities

    @property
    @abstractmethod
    def tags(self) -> list[str]:
        """Return a list of tags for reading stream."""
        pass

    @abstractmethod
    def read(self) -> Sequence:
        """Read the quantities of interest."""
        pass

    @abstractmethod
    def get_unit(self, quantity: str) -> str:
        """Get the unit for a given quantity."""
        pass

    def compute_energy_delta(self, energy_series: np.ndarray) -> np.ndarray:
        if len(energy_series) == 0:
            return np.empty_like(energy_series)
        elif len(energy_series) == 1:
            return np.zeros_like(energy_series[1:])
        else:
            return energy_series[1:] - energy_series[:-1]

    def compute_power_series(
        self, time_series: np.ndarray, energy_data: np.ndarray
    ) -> np.ndarray:
        n = min(len(time_series), len(energy_data))
        power_series = np.zeros(energy_data.shape)
        power_series = power_series[:n]
        if n >= 2:
            factor = get_conversion_factor(self.get_unit("energy"))
            energy_delta = (
                factor
                * np.atleast_2d(
                    self.compute_energy_delta(energy_data[:n]).transpose()
                ).transpose()
            )
            time_delta = (
                1e-9
                * np.atleast_2d(time_series[1:n] - time_series[: n - 1]).transpose()
            )

            power_series[1:] = energy_delta / time_delta
        return power_series
