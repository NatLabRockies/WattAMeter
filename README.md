[![CI](https://github.com/NREL/WattAMeter/actions/workflows/ci.yml/badge.svg)](https://github.com/NREL/WattAMeter/actions/workflows/ci.yml)

![wattameter_logo](wattameter_logo.png)

**wattameter** is a Python package for monitoring and recording power consumption over time, enabling users to collect time series data on CPU, GPU, and RAM power usage. It also estimates energy consumption and CO₂ emissions.

## Features

- Track power usage for CPU, GPU, and RAM
- Periodically log power data to file
- Estimate energy consumption and CO₂ emissions
- Customizable logging and output options
- Command-line interface for easy usage

## Installation

You can install **wattameter** via pip:

```bash
pip install wattameter
```

## Usage

### As a Python module

```python
from wattameter.codecarbon_tracker import CodeCarbonTracker

tracker = CodeCarbonTracker(
    country_iso_code="USA",
    region="colorado",
    measure_power_secs=1,
    api_call_interval=3600,
    output_dir=".",
    output_file="emissions_data.csv",
    output_power_file="power_data.log",
)
tracker.start()
# ... your code ...
tracker.stop()
```

### Command-line interface

```sh
wattameter \
    --id id \
    --dt-read 1 \
    --freq-write 3600 \
    --log-level info \
    --country USA \
    --region colorado
```

| Option       | Short | Default  | Description                                              |
| ------------ | ----- | -------- | -------------------------------------------------------- |
| --id         | -i    | None     | Unique identifier for the machine (used in output files) |
| --dt-read    | -t    | 1        | Time interval (seconds) for reading power data           |
| --freq-write | -f    | 3600     | Frequency (# reads) for writing power data to file       |
| --log-level  | -l    | warning  | Logging level: debug, info, warning, error, critical     |
| --country    | -c    | USA      | ISO code of the country for CO₂ emissions tracking       |
| --region     | -r    | colorado | Region for CO₂ emissions tracking                        |
| --help       | -h    |          | Show the help message and exit                           |

### Command-line interface with SLURM

For asynchronous usage with SLURM, we recommend using our [wattameter.sh](src/wattameter/utils/wattameter.sh) script as in [examples/slurm.sh](examples/slurm.sh), i.e.,

```bash
#SBATCH --signal=USR1@0 # Send USR1 signal at the end of the job to stop wattameter

# Load Python environment with wattameter installed...

# Get the path of the wattameter script
WATTAPATH=$(python -c 'import wattameter; import os; print(os.path.dirname(wattameter.__file__))')
WATTASCRIPT="${WATTAPATH}/utils/wattameter.sh"
WATTAWAIT="${WATTAPATH}/utils/wattawait.sh"

# Run wattameter on all nodes
srun --overlap --wait=0 --nodes=$SLURM_JOB_NUM_NODES --ntasks-per-node=1 "${WATTAWAIT}" $SLURM_JOB_ID &
WAIT_PID=$!
srun --overlap --wait=0 --output=slurm-$SLURM_JOB_ID-wattameter.txt --nodes=$SLURM_JOB_NUM_NODES --ntasks-per-node=1 "${WATTASCRIPT}" -i $SLURM_JOB_ID \
    [-t dt_read] \
    [-f freq_write] \
    [-l log_level] \
    &
wait $WAIT_PID

# Run your script here...

# Cancel the job to stop wattameter
scancel $SLURM_JOB_ID
```

Almost all options are the same as the regular command-line interface. The script will automatically handle the output file naming based on the provided SLURM_JOB_ID and node information. Mind that this option currently does not compute carbon emissions.

## Contributing

Contributions are welcome! Please open issues or submit pull requests.

## License

This project is planned to be licensed under the BSD-3-Clause License.

## Acknowledgements

- [CodeCarbon](https://github.com/mlco2/codecarbon) for emissions tracking and wrappers to energy tracking tools.

---

_NREL Software Record number: SWR-25-101_
