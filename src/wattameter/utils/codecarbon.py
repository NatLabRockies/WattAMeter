# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import csv
from importlib import resources


def add_cpu(cpu_model: str, tdp: float) -> bool:
    """
    Add a CPU model and its TDP (Thermal Design Power) to codecarbon's CPU power database.

    This function adds a new CPU entry to codecarbon's hardware database CSV file,
    which is used for power consumption calculations. The function checks if the
    CPU model already exists in the database before adding it to avoid duplicates.

    Example usage:
    .. code-block:: python
        >>> add_cpu("Intel Xeon Platinum 8470QL", 95.0)
        True
        >>> add_cpu("Intel Xeon Platinum 8470QL", 95.0)  # Already exists
        False

    Note:
        This function modifies the codecarbon package's internal CPU power database.
        The changes will persist across sessions but may be overwritten when
        codecarbon is updated.

    :param cpu_model: The name/model of the CPU (e.g., "Intel Xeon Platinum 8470QL").
    :param tdp: The Thermal Design Power of the CPU in watts.

    :return: True if the CPU was successfully added to the database,
             False if the CPU already existed in the database.
    """
    # Get the path to the CSV file using importlib.resources
    with resources.path(
        "codecarbon.data.hardware", "cpu_power.csv"
    ) as cpu_power_csv_path:
        # Check if the line already exists
        line_exists = False
        new_row = [cpu_model, str(tdp)]
        with open(cpu_power_csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row == new_row:
                    line_exists = True
                    break

        # Only add the line if it doesn't already exist
        if not line_exists:
            with open(cpu_power_csv_path, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(new_row)

    return (
        not line_exists
    )  # Return True if the line was added, False if it already existed
