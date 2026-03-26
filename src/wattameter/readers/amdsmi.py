# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC

import amdsmi
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


class AMDSMIReader(BaseReader):
    """Reader for AMD System Management Interface (AMDSMI) to monitor AMD GPUs.

    .. attribute:: devices

        List of AMDSMI device handles for available GPUs.

    """

    UNITS = {
        Temperature: Celsius(),
        Power: Watt("m"),
    }  #: Dictionary of measurement units for physical quantities.

    def __init__(self, quantities=(Power,)) -> None:
        super().__init__(quantities)

        self.devices = []

        # Initialize AMDSMI
        try:
            ret = amdsmi.amdsmi_init()
            logger.info("AMDSMI initialized successfully.")
        except amdsmi.AmdSmiException as e:
            logger.warning(
                f"Failed to initialize AMDSMI: {e}. Continuing without AMDSMI support."
            )
            return

        # Get the handles for all available devices
        try:
            self.devices = amdsmi.amdsmi_get_processor_handles()
            logger.info(f"Found {len(self.devices)} AMD GPU(s) on the system.")
        except amdsmi.AmdSmiException as e:
            logger.error(f"Failed to get device handles: {e}")
            self.devices = []

        # Set the quantities to read
        invalid_quantities = [
            q for q in quantities if q not in self.UNITS and q != Utilization
        ]
        if invalid_quantities:
            raise ValueError(
                f"Unsupported quantities: {invalid_quantities}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )

    def __del__(self):
        """Shutdown AMDSMI on deletion."""
        try:
            amdsmi.amdsmi_shut_down()
            logger.info("AMDSMI shutdown successfully.")
        except amdsmi.AmdSmiException as e:
            logger.warning(f"Failed to shutdown AMDSMI: {e}")

    @property
    def tags(self) -> list[str]:
        _tags = []
        for q in self.quantities:
            if q == Utilization:
                _tags.extend([f"gpu-{i}[%gpu]" for i in range(len(self.devices))])
                _tags.extend([f"gpu-{i}[%mem]" for i in range(len(self.devices))])
            else:
                unit = self.get_unit(q)
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

    def read_temperature_on_device(self, i: int) -> int:
        """Read the temperature for the i-th device."""
        try:
            return amdsmi.amdsmi_get_temp_metric(self.devices[i], amdsmi.AmdSmiTemperatureType.EDGE,
                            amdsmi.AmdSmiTemperatureMetric.CURRENT)
        except amdsmi.AmdSmiException as e:
            logger.error(f"Failed to get temperature for device {i}: {e}")
            return 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0

    def read_power_on_device(self, i: int) -> int:
        """Read the current power usage for the i-th device."""
        try:
            return int(amdsmi.amdsmi_get_power_info(self.devices[i])['average_socket_power'])
        except amdsmi.AmdSmiException as e:
            logger.error(f"Failed to get power usage for device {i}: {e}")
            return 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0

    def read_utilization_on_device(self, i: int) -> tuple[int, int]:
        """Read the current utilization for the i-th device."""
        try:
            utilization = amdsmi.amdsmi_get_utilization_count(
                            self.devices[i],
                            [amdsmi.AmdSmiUtilizationCounterType.COARSE_GRAIN_GFX_ACTIVITY,
                            amdsmi.AmdSmiUtilizationCounterType.COARSE_GRAIN_MEM_ACTIVITY]
            )
            return utilization[0]['value'], utilization[1]['value']  # GPU utilization, Memory utilization
        except amdsmi.AmdSmiException as e:
            logger.error(f"Failed to get utilization for device {i}: {e}")
            return 0, 0
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0, 0

    def read_temperature(self) -> list[int]:
        """Read the current temperature for all devices."""
        return [self.read_temperature_on_device(i) for i in range(len(self.devices))]

    def read_power(self) -> list[int]:
        """Read the current power usage for all devices."""
        return [self.read_power_on_device(i) for i in range(len(self.devices))]

    def read_utilization(self) -> list[tuple[int, int]]:
        """Read the current utilization for all devices."""
        return [self.read_utilization_on_device(i) for i in range(len(self.devices))]

    def read(self) -> list[int]:
        """Read the specified quantities for all devices."""
        res = []
        for q in self.quantities:
            if q == Temperature:
                res = res + self.read_temperature()
            elif q == Power:
                res = res + self.read_power()
            elif q == Utilization:
                util = self.read_utilization()
                res = res + [u[0] for u in util]  # GPU utilization
                res = res + [u[1] for u in util]  # Memory utilization
            else:
                logger.warning(f"Unsupported quantity requested: {q}. Skipping.")
        return res
