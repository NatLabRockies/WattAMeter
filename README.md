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
wattameter --suffix test --id 0 --dt-read 0.1 --freq-write 600 --log-level info
```

| Option       | Short | Default  | Description                                              |
| ------------ | ----- | -------- | -------------------------------------------------------- |
| --suffix     | -s    | None     | Suffix for output files                                  |
| --id         | -i    | None     | Identifier for the experiment                            |
| --dt-read    | -t    | 1        | Time interval (seconds) between readings                 |
| --freq-write | -f    | 3600     | Frequency (# reads) for writing data to file             |
| --log-level  | -l    | warning  | Logging level: debug, info, warning, error, critical     |
| --help       | -h    |          | Show the help message and exit                           |

### Command-line interface with SLURM

For asynchronous usage with SLURM, we recommend using [wattameter.sh](src/wattameter/utils/wattameter.sh). Follow the example [examples/slurm.sh](examples/slurm.sh), i.e.,

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
srun --overlap --wait=0 --output=slurm-$SLURM_JOB_ID-wattameter.txt --nodes=$SLURM_JOB_NUM_NODES --ntasks-per-node=1 "${WATTASCRIPT}" -i $SLURM_JOB_ID & # Use other options here as needed
wait $WAIT_PID

# Run your script here...

# Cancel the job to stop wattameter
scancel $SLURM_JOB_ID
```

All options are the same as the regular command-line interface. The script will automatically handle the output file naming based on the provided SLURM_JOB_ID and node information.

## Contributing

Contributions are welcome! Please open issues or submit pull requests.

## License

See the [LICENSE](LICENSE) file for details.

---

_NREL Software Record number: SWR-25-101_
