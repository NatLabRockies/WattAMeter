import logging
import os
import re
import numpy as np

from .base import BaseReader
from .utils import Quantity, Energy, Joule, Unit

# Module-level logger
logger = logging.getLogger(__name__)


def _get_rapl_domain_name(rapl_device_path, tag_for_unnamed_device: str) -> str:
    """Generate a domain name for the RAPL device based on its name and path.

    :param rapl_device_path: Path to the RAPL device directory.
    :param tag_for_unnamed_device: Tag to use if the device name cannot be determined.
    """

    # If the path ends in a pattern like :<number>:<number>
    if re.search(r":\d+:\d+$", rapl_device_path):
        # Remove the last part after the last colon
        parent_rapl_component_dir = re.sub(r":\d+$", "", rapl_device_path)
        domain_name = (
            _get_rapl_domain_name(parent_rapl_component_dir, tag_for_unnamed_device)
            + "-"
        )
    else:
        domain_name = ""

    try:
        # Read the actual domain name from the 'name' file
        with open(os.path.join(rapl_device_path, "name"), "r") as f:
            _name = f.read().strip()

        # Replace "package-" prefix by "cpu-"
        if _name.startswith("package-"):
            _name = "cpu-" + _name.split("-")[1]

        # Append the name to the domain name
        domain_name += _name

    except (FileNotFoundError, PermissionError, OSError):
        # Fallback to extracting from path if name file is not readable
        last_digit = re.search(r"\d+$", rapl_device_path)
        if last_digit:
            domain_name += last_digit[0]
        else:
            domain_name += tag_for_unnamed_device

    return domain_name


class RAPLDevice(BaseReader):
    """Reader for RAPL (Running Average Power Limit) devices.

    :param rapl_device_path: Path to the RAPL device directory.

    .. attribute:: UNITS

        Dictionary of measurement units for physical quantities.

    .. attribute:: path

        Path to the RAPL device directory, typically under /sys/class/powercap/intel-rapl.

    .. attribute:: name

        Name of the RAPL device, read from the 'name' file.

    .. attribute:: max_energy_range

        Maximum energy range, read from the 'max_energy_range_uj' file.

    """

    UNITS = {Energy: Joule("u")}

    def __init__(self, rapl_device_path: str) -> None:
        super().__init__((Energy,))

        self.path = rapl_device_path

        # Read name file
        self.name = None
        try:
            with open(os.path.join(self.path, "name"), "r") as f:
                self.name = f.read().strip()
        except FileNotFoundError:
            logger.warning(f"Name file not found for {self.path}")

        # Read max energy range file
        self.max_energy_range = 0
        try:
            with open(os.path.join(self.path, "max_energy_range_uj"), "r") as f:
                self.max_energy_range = int(f.read().strip())
        except FileNotFoundError:
            logger.warning(f"Max energy range file not found for {self.path}")

        # Open handle to energy file, which is used to read the energy counter
        self._energy_file = None
        try:
            self._energy_file = open(os.path.join(self.path, "energy_uj"), "r")
        except FileNotFoundError:
            logger.warning(f"Energy file not found for {self.path}")

        # Post-process tags
        self._tag = _get_rapl_domain_name(self.path, tag_for_unnamed_device="unknown")

    def __del__(self):
        """Ensure the energy file is closed when the object is deleted."""
        if self._energy_file:
            self._energy_file.close()

    @property
    def tags(self) -> list[str]:
        return [self._tag]

    def get_unit(self, quantity: type[Quantity]) -> Unit:
        if quantity in self.UNITS:
            return self.UNITS[quantity]
        else:
            logger.warning(
                f"Invalid quantity requested: {quantity}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )
            return Unit()

    def read_energy(self) -> int:
        """Read the energy counter for the i-th device."""
        if self._energy_file:
            try:
                self._energy_file.seek(0)
                return int(self._energy_file.read().strip())
            except ValueError as e:
                logger.error(f"Failed to read energy for {self.path}: {e}")
                return 0
        else:
            logger.error(f"Energy file is not open for {self.path}.")
            return 0

    def read(self) -> list[int]:
        return [self.read_energy()]

    def compute_energy_delta(self, energy_series: np.ndarray) -> np.ndarray:
        res = super().compute_energy_delta(energy_series)
        if len(res) > 0:
            res[res < 0] += self.max_energy_range
        return res


class RAPLReader(BaseReader):
    """Reader for RAPL devices in the system.

    :param rapl_dir: Directory where RAPL devices are located, typically /sys/class/powercap/intel-rapl/subsystem.

    .. attribute:: rapl_dir

        Directory where RAPL devices are located.

    .. attribute:: devices

        List of RAPLDevice instances for available RAPL devices.
    """

    UNITS = RAPLDevice.UNITS

    def __init__(self, rapl_dir="/sys/class/powercap/intel-rapl/subsystem") -> None:
        super().__init__((Energy,))

        self.rapl_dir = rapl_dir

        # Find all RAPL devices in the specified directory
        self.devices = []
        for root, dirs, _ in os.walk(rapl_dir):
            for dir_name in dirs:
                rapl_file = os.path.join(root, dir_name, "energy_uj")
                if os.path.exists(rapl_file):
                    self.devices.append(RAPLDevice(os.path.join(root, dir_name)))

        # Order devices by their path for consistency
        self.devices.sort(key=lambda d: d.path)

        # Post-process tags
        count = 0
        self._tags = []
        for device in self.devices:
            tag = self.devices[count].tags[0]

            if "unknown" in tag:
                tag = f"unknown-{count}"
            count += 1

            self._tags.append(tag)

    @property
    def tags(self) -> list[str]:
        return self._tags

    def get_unit(self, quantity: type[Quantity]) -> Unit:
        if quantity in self.UNITS:
            return self.UNITS[quantity]
        else:
            logger.warning(
                f"Invalid quantity requested: {quantity}. "
                f"Supported quantities are: {list(self.UNITS.keys())}."
            )
            return Unit("")

    def read_energy_on_device(self, i: int) -> int:
        """Read the energy counter of the i-th device."""
        try:
            return self.devices[i].read_energy()
        except IndexError:
            logger.error(f"Device index {i} out of range.")
            return 0
        except Exception as e:
            logger.error(f"Failed to read energy for device {i}: {e}")
            return 0

    def read_energy(self) -> list[int]:
        """Read the current energy counter for all RAPL devices."""
        return [self.read_energy_on_device(i) for i in range(len(self.devices))]

    # Alias for read_energy to match the BaseReader interface
    read = read_energy

    def compute_energy_delta(self, energy_series: np.ndarray) -> np.ndarray:
        res = super().compute_energy_delta(energy_series)
        if len(res) > 0:
            for i in range(len(self.devices)):
                res_i = res[:, i]
                res_i[res_i < 0] += self.devices[i].max_energy_range
        return res
