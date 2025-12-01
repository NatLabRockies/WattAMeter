[![CI](https://github.com/NREL/WattAMeter/actions/workflows/ci.yml/badge.svg)](https://github.com/NREL/WattAMeter/actions/workflows/ci.yml)

![wattameter_logo](wattameter_logo.png)

**wattameter** is a Python package for monitoring and recording power usage over time, among other metrics. It enables time series data collection on hardware components such as CPUs and GPUs.

## Current Features

- Track power usage for CPU (using RAPL) and GPU (using nvidia-ml-py)
- Track GPU utilization and temperature
- Periodically log time series data to file
- Customizable logging and output options
- Command-line interface for easy usage
- Integration with SLURM for HPC environments

## Installation

You can install **wattameter** via pip:

```bash
pip install wattameter
```

## Optional extras

Some features (notably the post-processing utilities that use `pandas`) are optional and not required for the core runtime. To enable post-processing functionality, install the optional extra:

```bash
pip install wattameter[postprocessing]
# or just
pip install pandas
```

## Usage

### As a Python module

```python
from wattameter import Tracker
from wattameter.readers import NVMLReader

tracker = Tracker(
    reader=NVMLReader((Power,)),
    dt_read=0.1,  # Time interval for reading power data (seconds)
    freq_write=600,  # Frequency (# reads) for writing power data to file
    output="power_log.txt",
)
tracker.start()
# ... your code ...
tracker.stop()

# ... or ...

with Tracker(
    reader=NVMLReader((Power,)),
    dt_read=0.1,
    freq_write=600,
    output="power_log.txt",
) as tracker:
    # ... your code ...
```

### Command-line interface

```sh
wattameter --tracker 0.1,nvml-power,rapl --tracker 1.0,nvml-util --suffix test --id 0 --freq-write 600 --log-level info
```

| Option       | Short | Default             | Description                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------ | ----- | ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| --tracker    |       | 0.1,nvml-power,rapl | Tracker specification: `dt_read,metric1,metric2,...` where `dt_read` is the time interval in seconds between readings. Available metrics: `rapl` (CPU energy), `nvml-energy` (GPU energy), `nvml-power` (GPU power), `nvml-temp` (GPU temperature), `nvml-util` (GPU utilization), `nvml-nvlink` (GPU NVLink throughput). Can be specified multiple times to create multiple trackers with different configurations. |
| --suffix     | -s    | None                | Suffix for output files                                                                                                                                                                                                                                                                                                                                                                                              |
| --id         | -i    | UUID                | Identifier for the experiment                                                                                                                                                                                                                                                                                                                                                                                        |
| --freq-write | -f    | 3600                | Frequency (# reads) for writing data to file                                                                                                                                                                                                                                                                                                                                                                         |
| --log-level  | -l    | warning             | Logging level: debug, info, warning, error, critical                                                                                                                                                                                                                                                                                                                                                                 |
| --help       | -h    |                     | Show the help message and exit                                                                                                                                                                                                                                                                                                                                                                                       |

### Command-line interface with SLURM

For usage within SLURM jobs, we recommend using our utility functions `start_wattameter` and `stop_wattameter` in [slurm.sh](src/wattameter/utils/slurm.sh). Follow the example [examples/slurm.sh](examples/slurm.sh), i.e.,

```bash
# In a Python environment with wattameter installed,
# load wattameter slurm utilities
WATTAPATH=$(python -c 'import wattameter; import os; print(os.path.dirname(wattameter.__file__))')
source "${WATTAPATH}/utils/slurm.sh"

# Run wattameter on all nodes
start_wattameter

# Input your job commands here
# ...

# Stop wattameter on all nodes
stop_wattameter
```

All options are the same as the regular command-line interface. The script will automatically handle the output file naming based on the provided SLURM_JOB_ID and node information.

## Contributing

Contributions are welcome! Please open issues or submit pull requests.

## Documentation

The API documentation is available at [https://nrel.github.io/WattAMeter/](https://nrel.github.io/WattAMeter/).

## License

See the [LICENSE](LICENSE) file for details.

---

_NREL Software Record number: SWR-25-101_
