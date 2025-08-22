from abc import ABC, abstractmethod
from typing import Sequence
import numpy as np

from .utils import get_conversion_factor


class BaseReader(ABC):
    """Base class for all readers.

    :param quantities: List of quantities to read.

    .. attribute quantities: List of quantities to read.
    """

    def __init__(self, quantities: Sequence[str]) -> None:
        """Initialize the reader with the specified quantities."""
        self.quantities = quantities

    @property
    @abstractmethod
    def tags(self) -> list[str]:
        """Return a list of tags for each reading stream."""
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
        """Compute the difference between consecutive energy readings.

        Mind that the returned array has one less element than the input
        array, as it represents the change in energy over time.

        :param energy_series: One or two-dimensional array of energy readings.
            In case of a two-dimensional array, the first dimension is expected
            to be the time dimension.
        """
        if len(energy_series) == 0:
            return np.empty_like(energy_series)
        elif len(energy_series) == 1:
            return np.zeros_like(energy_series[1:])
        else:
            return energy_series[1:] - energy_series[:-1]

    def compute_power_series(
        self, time_series: np.ndarray, energy_data: np.ndarray
    ) -> np.ndarray:
        """Compute the power series from the time and energy data.

        In the case time_series and energy_data lengths do not match,
        the shorter length will be used.

        :param time_series: One-dimensional array of time readings.
        :param energy_data: One or two-dimensional array of energy readings.
            In case of a two-dimensional array, the first dimension is expected
            to be the time dimension.
        """
        # Ensure that the time series and energy data are compatible
        n = min(len(time_series), len(energy_data))
        power_series = np.zeros(energy_data.shape)
        power_series = power_series[:n]

        if n >= 2:
            factor = get_conversion_factor(self.get_unit("energy"))
            energy_delta = factor * self.compute_energy_delta(energy_data[:n])
            time_delta = time_series[1:n] - time_series[: n - 1]

            if energy_delta.ndim == 1:
                power_series[1:] = energy_delta / time_delta
            else:
                power_series[1:] = energy_delta / time_delta.reshape(-1, 1)

        return power_series
