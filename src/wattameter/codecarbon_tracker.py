# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

from codecarbon import OfflineEmissionsTracker
from codecarbon.external.hardware import CPU, GPU
from codecarbon.external.ram import RAM
from codecarbon.core.util import count_physical_cpus

from collections import deque
from typing import Optional
from datetime import datetime
import re
import os


class CodeCarbonTracker(OfflineEmissionsTracker):
    """Power tracker based on the CodeCarbon offline emission tracker.

    :param output_power_file: Optional path to the output file where power data
        will be saved. If not provided, a default file named
        `power_<run_id>.log` will be created.
    :param time_fmt: Format for the time values in the output file.
    :param power_fmt: Format for the power values in the output file.
    """

    def __init__(
        self,
        *args,
        output_power_file: Optional[str] = None,
        time_fmt: str = ".3e",
        power_fmt: str = ".3e",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # Create queues to store power data
        self._time_series = deque([])
        self._timestamp_series = deque([])
        self._power_series = {key: [] for key in ("cpu", "gpu", "ram")}
        count_cpu = 0
        count_gpu = 0
        count_ram = 0
        for hw in self._hardware:
            if isinstance(hw, CPU):
                assert count_cpu < 1, "Only one CPU object is supported."
                if hw._mode == "intel_rapl":
                    self._power_series["cpu"] = [
                        deque([]) for _ in range(count_physical_cpus())
                    ]
                else:
                    self._power_series["cpu"] = [deque([])]
                count_cpu += 1
            elif isinstance(hw, GPU):
                assert count_gpu < 1, "Only one GPU object is supported."
                self._power_series["gpu"] = [deque([]) for _ in range(hw.num_gpus)]
                count_gpu += 1
            elif isinstance(hw, RAM):
                assert count_ram < 1, "Only one RAM object is supported."
                self._power_series["ram"] = [deque([])]
                count_ram += 1

        # Initialize the last time written to file
        if self._api_call_interval != -1:
            self.output_power_file = (
                f"power_{self.run_id}.log"
                if output_power_file is None
                else output_power_file
            )
            self.output_power_file = os.path.join(
                self._output_dir, self.output_power_file
            )
            self._last_time_written = 0

            # Get the format for time and power values
            self.timestamp_fmt = "%Y-%m-%d_%H:%M:%S.%f"
            self.time_fmt = time_fmt
            self.power_fmt = power_fmt

            # Write header to the power file
            timestamp_str = datetime.now().strftime(self.timestamp_fmt)[:-3]
            with open(self.output_power_file, "a", encoding="utf-8") as f:
                f.write(f"# {timestamp_str} - Power data for run {self.run_id}\n")

    def start(self) -> None:
        super().start()

        # I don't need their scheduler to monitor power, so I stop it
        if self._scheduler_monitor_power:
            self._scheduler_monitor_power.stop()

        if self._api_call_interval != -1:
            timestamp_str = datetime.now().strftime(self.timestamp_fmt)[:-3]

            timestamp_len = len(timestamp_str)
            time_len = len(f"{0:{self.time_fmt}}")
            power_len = len(f"{0:{self.power_fmt}}")

            with open(self.output_power_file, "a", encoding="utf-8") as f:
                f.write(
                    f"# {timestamp_str} - Tracking started using CodeCarbonTracker\n"
                )
                f.write("# timestamp" + " " * (timestamp_len - 9))
                f.write(" time (s)" + " " * (time_len - 8))
                for i in range(len(self._power_series["cpu"])):
                    f.write(f"{' cpu ' + str(i):>{power_len - 8}} (W)")
                for i in range(len(self._power_series["gpu"])):
                    f.write(f"{' gpu ' + str(i):>{power_len - 8}} (W)")
                for i in range(len(self._power_series["ram"])):
                    f.write(f"{' ram ' + str(i):>{power_len - 8}} (W)")
                f.write("\n")

    def _measure_power_and_energy(self) -> None:
        """Specialization of the method from the parent class that keeps track
        of the power for each component (CPU, GPU, RAM) and writes it to a file
        periodically."""
        # Measure power and energy consumption
        # Save measure_occurrence before it is modified inside the method
        measure_occurrence = self._measure_occurrence
        super()._measure_power_and_energy()
        timestamp_str = datetime.now().strftime(self.timestamp_fmt)[:-3]
        measure_occurrence += 1

        # Update power series
        self._time_series.append(self._last_measured_time - self._start_time)
        self._timestamp_series.append(timestamp_str)
        for hw in self._hardware:
            if isinstance(hw, CPU):
                if hw._mode == "intel_rapl":
                    all_cpu_details = hw._intel_interface.get_static_cpu_details()
                    i = 0
                    for metric, value in all_cpu_details.items():
                        if re.match(r"^Processor Power", metric):
                            self._power_series["cpu"][i].append(value)
                            i += 1
                else:
                    self._power_series["cpu"][0].append(self._cpu_power.W)
            elif isinstance(hw, GPU):
                for i in range(hw.num_gpus):
                    self._power_series["gpu"][i].append(hw.devices.devices[i].power.W)
            elif isinstance(hw, RAM):
                self._power_series["ram"][0].append(self._ram_power.W)

        # Write power to file if needed
        if (
            self._api_call_interval != -1
            and measure_occurrence >= self._api_call_interval
        ) or self._scheduler is None:
            n = len(self._time_series)
            if n == self._last_time_written:
                return

            buffer = ""
            for i in range(self._last_time_written, n):
                buffer += "  " + self._timestamp_series[i]
                buffer += f" {self._time_series[i]:{self.time_fmt}}"
                for k in range(len(self._power_series["cpu"])):
                    buffer += f" {self._power_series['cpu'][k][i]:{self.power_fmt}}"
                for k in range(len(self._power_series["gpu"])):
                    buffer += f" {self._power_series['gpu'][k][i]:{self.power_fmt}}"
                for k in range(len(self._power_series["ram"])):
                    buffer += f" {self._power_series['ram'][k][i]:{self.power_fmt}}"
                buffer += "\n"

            with open(self.output_power_file, "a", encoding="utf-8") as f:
                f.write(buffer)

            self._last_time_written = n
