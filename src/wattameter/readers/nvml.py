import pynvml
import logging

from .base import BaseReader

# Module-level logger
logger = logging.getLogger(__name__)


class NVMLReader(BaseReader):
    """Reader for NVIDIA Management Library (NVML) to monitor GPU

    .. attribute:: UNITS

        Dictionary of measurement units for physical quantities.

    .. attribute:: devices

        List of NVML device handles for available GPUs.

    """

    UNITS = {"energy": "mJ", "temperature": "C", "power": "W"}

    def __init__(self, quantities=("power",)) -> None:
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
        if any(q not in self.UNITS for q in quantities):
            logger.error(
                f"Invalid quantities specified: {quantities}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )

    @property
    def tags(self) -> list[str]:
        return ["gpu-" + str(i) for i in range(len(self.devices))]

    def get_unit(self, quantity: str) -> str:
        if quantity in self.UNITS:
            return self.UNITS[quantity]
        else:
            logger.warning(
                f"Invalid quantity requested: {quantity}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )
            return ""

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
        if "energy" in self.quantities:
            res = res + self.read_energy()
        if "temperature" in self.quantities:
            res = res + self.read_temperature()
        if "power" in self.quantities:
            res = res + self.read_power()
        return res
