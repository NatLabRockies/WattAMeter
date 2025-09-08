import pynvml
import logging

from .base import BaseReader
from .utils import Power, Energy, Temperature, Quantity, Joule, Watt, Celsius, Unit

# Module-level logger
logger = logging.getLogger(__name__)


class NVMLReader(BaseReader):
    """Reader for NVIDIA Management Library (NVML) to monitor GPU

    .. attribute:: UNITS

        Dictionary of measurement units for physical quantities.

    .. attribute:: devices

        List of NVML device handles for available GPUs.

    """

    UNITS = {Energy: Joule("m"), Temperature: Celsius(), Power: Watt("m")}

    def __init__(self, quantities=(Power,)) -> None:
        super().__init__(quantities)

        self.devices = []

        # Initialize NVML
        try:
            pynvml.nvmlInit()
            logger.info("NVML initialized successfully.")
        except pynvml.NVMLError as e:
            logger.warning(
                f"Failed to initialize NVML: {e}. Continuing without NVML support."
            )
            return

        # Get the handles for all available devices
        for i in range(pynvml.nvmlDeviceGetCount()):
            try:
                self.devices.append(pynvml.nvmlDeviceGetHandleByIndex(i))
                logger.info(f"Handle for device {i} initialized successfully.")
            except pynvml.NVMLError as e:
                logger.error(f"Failed to get handle for device {i}: {e}")

        # Set the quantities to read
        invalid_quantities = [q for q in quantities if q not in self.UNITS]
        if invalid_quantities:
            raise ValueError(
                f"Unsupported quantities: {invalid_quantities}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )

    @property
    def tags(self) -> list[str]:
        units = [self.get_unit(q) for q in self.quantities]
        return [f"gpu-{i}[{unit}]" for unit in units for i in range(len(self.devices))]

    def get_unit(self, quantity: type[Quantity]) -> Unit:
        if quantity in self.UNITS:
            return self.UNITS[quantity]
        else:
            logger.warning(
                f"Unsupported quantity: {quantity}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )
            return Unit()  # Return a default Unit instance

    def read_energy_on_device(self, i: int) -> int:
        """Read the energy counter for the i-th device."""
        try:
            return pynvml.nvmlDeviceGetTotalEnergyConsumption(self.devices[i])
        except pynvml.NVMLError as e:
            logger.error(f"Failed to get power usage for device {i}: {e}")
            return 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0

    def read_temperature_on_device(self, i: int) -> int:
        """Read the temperature for the i-th device."""
        try:
            return pynvml.nvmlDeviceGetTemperature(
                self.devices[i], pynvml.NVML_TEMPERATURE_GPU
            )
        except pynvml.NVMLError as e:
            logger.error(f"Failed to get temperature for device {i}: {e}")
            return 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0

    def read_power_on_device(self, i: int) -> int:
        """Read the current power usage for the i-th device."""
        try:
            return pynvml.nvmlDeviceGetPowerUsage(self.devices[i])
        except pynvml.NVMLError as e:
            logger.error(f"Failed to get power usage for device {i}: {e}")
            return 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0

    def read_energy(self) -> list[int]:
        """Read the current power usage for all devices."""
        return [self.read_energy_on_device(i) for i in range(len(self.devices))]

    def read_temperature(self) -> list[int]:
        """Read the current temperature for all devices."""
        return [self.read_temperature_on_device(i) for i in range(len(self.devices))]

    def read_power(self) -> list[int]:
        """Read the current power usage for all devices."""
        return [self.read_power_on_device(i) for i in range(len(self.devices))]

    def read(self) -> list[int]:
        """Read the specified quantities for all devices."""
        res = []
        for q in self.quantities:
            if q == Energy:
                res = res + self.read_energy()
            elif q == Temperature:
                res = res + self.read_temperature()
            elif q == Power:
                res = res + self.read_power()
            else:
                logger.warning(f"Unsupported quantity requested: {q}. Skipping.")
        return res
