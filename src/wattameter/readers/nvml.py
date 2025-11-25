# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import pynvml
import logging

from .base import BaseReader
from .utils import (
    Power,
    Energy,
    Temperature,
    Quantity,
    Joule,
    Watt,
    Celsius,
    Unit,
    Utilization,
    Byte,
)

# Module-level logger
logger = logging.getLogger(__name__)


class DataThroughput(Quantity):
    """Data throughput quantity (e.g., NVLink throughput)."""

    @staticmethod
    def units() -> list[type[Unit]]:
        return [Byte]


class NVMLReader(BaseReader):
    """Reader for NVIDIA Management Library (NVML) to monitor GPU

    .. attribute:: devices

        List of NVML device handles for available GPUs.

    """

    UNITS = {
        Energy: Joule("m"),
        Temperature: Celsius(),
        Power: Watt("m"),
        DataThroughput: Byte("Ki"),
    }  #: Dictionary of measurement units for physical quantities.

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
        invalid_quantities = [
            q for q in quantities if q not in self.UNITS and q != Utilization
        ]
        if invalid_quantities:
            raise ValueError(
                f"Unsupported quantities: {invalid_quantities}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )

    @property
    def tags(self) -> list[str]:
        _tags = []
        for q in self.quantities:
            if q == Utilization:
                _tags.extend([f"gpu-{i}[%gpu]" for i in range(len(self.devices))])
                _tags.extend([f"gpu-{i}[%mem]" for i in range(len(self.devices))])
            else:
                unit = self.get_unit(q)
                if q == DataThroughput:
                    _tags.extend(
                        [f"gpu-{i}[TX {unit}]" for i in range(len(self.devices))]
                    )
                    _tags.extend(
                        [f"gpu-{i}[RX {unit}]" for i in range(len(self.devices))]
                    )
                else:
                    _tags.extend([f"gpu-{i}[{unit}]" for i in range(len(self.devices))])
        return _tags

    def get_unit(self, quantity: type[Quantity]) -> Unit:
        if quantity in self.UNITS:
            return self.UNITS[quantity]
        else:
            logger.warning(
                f"The quantity: {quantity} is either unsupported or has no associated unit. "
                f"Supported quantities with units are: {list(self.UNITS.keys())}."
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

    def read_utilization_on_device(self, i: int) -> tuple[int, int]:
        """Read the current utilization for the i-th device."""
        try:
            utilization = pynvml.nvmlDeviceGetUtilizationRates(self.devices[i])
            return utilization.gpu, utilization.memory
        except pynvml.NVMLError as e:
            logger.error(f"Failed to get utilization for device {i}: {e}")
            return 0, 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0, 0

    def read_nvlink_throughput_on_device(self, i: int) -> tuple[int, int]:
        """Read the current NVLink throughput for the i-th device."""
        try:
            nvlink_throughput = pynvml.nvmlDeviceGetFieldValues(
                self.devices[i],
                [
                    pynvml.NVML_FI_DEV_NVLINK_THROUGHPUT_DATA_TX,  # Transmitted data in KiB
                    pynvml.NVML_FI_DEV_NVLINK_THROUGHPUT_DATA_RX,  # Received data in KiB
                ],
            )
            return nvlink_throughput[0].value.ullVal, nvlink_throughput[1].value.ullVal
        except pynvml.NVMLError as e:
            logger.error(f"Failed to get NVLink throughput for device {i}: {e}")
            return 0, 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0, 0

    def read_energy(self) -> list[int]:
        """Read the current power usage for all devices."""
        return [self.read_energy_on_device(i) for i in range(len(self.devices))]

    def read_temperature(self) -> list[int]:
        """Read the current temperature for all devices."""
        return [self.read_temperature_on_device(i) for i in range(len(self.devices))]

    def read_power(self) -> list[int]:
        """Read the current power usage for all devices."""
        return [self.read_power_on_device(i) for i in range(len(self.devices))]

    def read_utilization(self) -> list[tuple[int, int]]:
        """Read the current utilization for all devices."""
        return [self.read_utilization_on_device(i) for i in range(len(self.devices))]

    def read_nvlink_throughput(self) -> list[tuple[int, int]]:
        """Read the current NVLink throughput for all devices."""
        return [
            self.read_nvlink_throughput_on_device(i) for i in range(len(self.devices))
        ]

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
            elif q == Utilization:
                util = self.read_utilization()
                res = res + [u[0] for u in util]  # GPU utilization
                res = res + [u[1] for u in util]  # Memory utilization
            elif q == DataThroughput:
                nvlink = self.read_nvlink_throughput()
                res = res + [n[0] for n in nvlink]  # TX throughput
                res = res + [n[1] for n in nvlink]  # RX throughput
            else:
                logger.warning(f"Unsupported quantity requested: {q}. Skipping.")
        return res
