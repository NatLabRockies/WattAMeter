# Contributing to WattAMeter

Thank you for your interest in contributing to WattAMeter. Contributions to improve monitoring, documentation, testing, portability, and HPC workflows are welcome.

## Contribute

### Before you start

1. Check the existing issues and pull requests to see whether the change has already been discussed. See [GitHub issues](https://github.com/NatLabRockies/WattAMeter/issues).
2. For significant changes, open an issue first to describe the proposed approach.
3. Keep changes focused and consistent with the existing project structure.
4. Do not include credentials, private system information, or generated measurement data in commits.

### Development setup

WattAMeter requires Python 3.9 or newer. Clone the repository and install the development dependencies:

```bash
git clone https://github.com/NatLabRockies/WattAMeter.git
cd WattAMeter
pdm install -G test
```

We use PDM (Python Development Master) to manage dependencies and the development environment. Install optional dependencies when working on a specific feature:

```bash
pdm install -G example
pip install -e ".[postprocessing,mqtt,benchmark]"
```

The CPU monitoring functionality requires access to RAPL interfaces, which are typically available on modern Intel processors. No additional Python packages are needed for CPU energy monitoring.

The NVIDIA monitoring functionality requires an NVIDIA driver and the `nvidia-ml-py` package. Install the optional `nvidia` dependency when working with NVIDIA monitoring features.

### Make a change

1. Create a branch from `main`.
2. Implement the change with focused modifications.
3. Add or update tests for changed behavior.
4. Update documentation when user-facing behavior changes.
5. Run the relevant test suite locally. Optionally, install Nektos Act and run the CI workflow locally. See [Nektos Act documentation](https://nektosact.com/).
6. Submit a pull request against `main`.

Use descriptive branch names and commit messages, for example:

```text
fix nvml initialization without available gpu
add mqtt topic configuration tests
```

### Run tests

Run the complete test suite with:

```bash
pdm run pytest
```

When reporting a pull request, include the commands you ran and note any tests that could not be executed because hardware or optional dependencies were unavailable.

### Pull requests

A pull request should include:

- A concise description of the problem and solution.
- The relevant tests or examples.
- Documentation updates for user-visible changes.
- Any hardware, operating system, or optional-dependency requirements.
- Known limitations or follow-up work.

Keep pull requests focused. Separate unrelated fixes into separate issues or pull requests.

## Report Issues

Report bugs and feature requests through the project's GitHub issue tracker:

https://github.com/NatLabRockies/WattAMeter/issues

Before opening an issue, search existing issues to avoid duplicates.

### Bug reports

Include enough information to reproduce the problem:

- A concise title.
- WattAMeter version, commit, or branch.
- Python version and operating system.
- Installation method and relevant optional dependencies.
- Hardware and driver details when the issue involves RAPL, NVML, SLURM, or MQTT.
- The exact command or minimal code example.
- The complete error message or traceback.
- Expected behavior.
- Actual behavior.
- Relevant logs, configuration, or test output.

Please remove passwords, tokens, hostnames, job identifiers, and other sensitive information before posting.

### Feature requests

Describe:

- The problem or use case.
- The behavior you would like to see.
- Why the feature is useful.
- Any proposed API, command-line, file-format, or compatibility considerations.

A feature request is easier to evaluate when it includes a concrete example of the desired usage.

## Seek Support

Start with the project documentation:

- [README](README.md)
- [API documentation](https://NatLabRockies.github.io/WattAMeter/)
- [MQTT usage documentation](docs/mqtt_usage.md)
- [NLR HPC documentation](https://natlabrockies.github.io/HPC/Documentation/Development/Performance_Tools/WattAMeter/)

For questions, troubleshooting, or usage guidance, open a GitHub issue and label it as a question or support request when appropriate.

When seeking support, include:

- What you are trying to accomplish.
- The command or code you are using.
- What you expected to happen.
- What happened instead.
- Relevant environment, hardware, and dependency details.
- Any troubleshooting steps you have already tried.

Do not post confidential workload data, credentials, or sensitive infrastructure information.

## License

By contributing to WattAMeter, you agree that your contributions are provided under the project's [BSD-3-Clause license](LICENSE).