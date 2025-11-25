# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import pytest
import argparse
from wattameter.cli.utils import parse_tracker_spec
from wattameter.readers import RAPLReader, NVMLReader
from wattameter.readers import Energy, Power, Temperature, Utilization, DataThroughput


class TestParseTrackerSpec:
    """Tests for parse_tracker_spec function."""

    def test_parse_single_metric(self):
        """Test parsing a tracker spec with a single metric."""
        dt_read, readers = parse_tracker_spec("0.5,rapl")

        assert dt_read == 0.5
        assert len(readers) == 1
        assert isinstance(readers[0], RAPLReader)

    def test_parse_multiple_metrics_same_reader(self):
        """Test parsing a tracker spec with multiple metrics for the same reader."""
        dt_read, readers = parse_tracker_spec("1.0,nvml-power,nvml-temp")

        assert dt_read == 1.0
        assert len(readers) == 1
        assert isinstance(readers[0], NVMLReader)
        # Check that the reader was initialized with both Power and Temperature
        quantities_list = list(readers[0].quantities)
        assert len(quantities_list) == 2
        assert Power in quantities_list
        assert Temperature in quantities_list

    def test_parse_multiple_metrics_different_readers(self):
        """Test parsing a tracker spec with metrics for different readers."""
        dt_read, readers = parse_tracker_spec("0.1,rapl,nvml-power")

        assert dt_read == 0.1
        assert len(readers) == 2

        # Check that we have both RAPL and NVML readers
        reader_types = [type(r) for r in readers]
        assert RAPLReader in reader_types
        assert NVMLReader in reader_types

    def test_parse_all_nvml_metrics(self):
        """Test parsing all NVML metric types."""
        dt_read, readers = parse_tracker_spec(
            "2.0,nvml-energy,nvml-power,nvml-temp,nvml-util,nvml-nvlink"
        )

        assert dt_read == 2.0
        assert len(readers) == 1
        assert isinstance(readers[0], NVMLReader)

        # Check that all quantities are present
        quantities = list(readers[0].quantities)
        assert len(quantities) == 5
        assert Energy in quantities
        assert Power in quantities
        assert Temperature in quantities
        assert Utilization in quantities
        assert DataThroughput in quantities

    def test_parse_case_insensitive(self):
        """Test that metric names are case-insensitive."""
        dt_read1, readers1 = parse_tracker_spec("0.5,RAPL")
        dt_read2, readers2 = parse_tracker_spec("0.5,rapl")
        dt_read3, readers3 = parse_tracker_spec("0.5,Rapl")

        assert dt_read1 == dt_read2 == dt_read3 == 0.5
        for readers in [readers1, readers2, readers3]:
            assert len(readers) == 1
            assert isinstance(readers[0], RAPLReader)

    def test_parse_with_whitespace(self):
        """Test that whitespace in metric names is handled correctly."""
        dt_read, readers = parse_tracker_spec("1.0, nvml-power , nvml-temp ")

        assert dt_read == 1.0
        assert len(readers) == 1
        assert isinstance(readers[0], NVMLReader)

    def test_parse_float_dt_read(self):
        """Test parsing various float values for dt_read."""
        test_cases = ["0.01,rapl", "1.5,rapl", "10.0,rapl", "100,rapl"]
        expected_dts = [0.01, 1.5, 10.0, 100.0]

        for spec, expected_dt in zip(test_cases, expected_dts):
            dt_read, readers = parse_tracker_spec(spec)
            assert dt_read == expected_dt

    def test_parse_duplicate_metrics_ignored(self):
        """Test that duplicate metrics for the same reader are deduplicated."""
        dt_read, readers = parse_tracker_spec("1.0,nvml-power,nvml-power,nvml-temp")

        assert dt_read == 1.0
        assert len(readers) == 1
        assert isinstance(readers[0], NVMLReader)
        # Should only have 2 unique quantities: Power and Temperature
        assert len(list(readers[0].quantities)) == 2

    def test_error_missing_metric(self):
        """Test error when no metric is provided."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_tracker_spec("0.5")

        assert "must have at least dt and one metric" in str(exc_info.value)

    def test_error_invalid_dt_read(self):
        """Test error when dt_read is not a valid number."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_tracker_spec("invalid,rapl")

        assert "Invalid dt_read value" in str(exc_info.value)

    def test_error_negative_dt_read(self):
        """Test error when dt_read is negative."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_tracker_spec("-0.5,rapl")

        assert "dt_read must be positive" in str(exc_info.value)

    def test_error_zero_dt_read(self):
        """Test error when dt_read is zero."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_tracker_spec("0,rapl")

        assert "dt_read must be positive" in str(exc_info.value)

    def test_error_unknown_metric(self):
        """Test error when an unknown metric is provided."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_tracker_spec("0.5,unknown-metric")

        assert "Unknown metric" in str(exc_info.value)
        assert "unknown-metric" in str(exc_info.value)

    def test_error_empty_string(self):
        """Test error when an empty string is provided."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_tracker_spec("")

    def test_complex_mixed_configuration(self):
        """Test a complex configuration with multiple readers and metrics."""
        dt_read, readers = parse_tracker_spec(
            "0.25,rapl,nvml-power,nvml-util,nvml-temp"
        )

        assert dt_read == 0.25
        assert len(readers) == 2

        # Check reader types
        reader_types = {type(r): r for r in readers}
        assert RAPLReader in reader_types
        assert NVMLReader in reader_types

        # Check NVML reader has correct quantities
        nvml_reader = reader_types[NVMLReader]
        quantities = list(nvml_reader.quantities)
        assert len(quantities) == 3
        assert Power in quantities
        assert Utilization in quantities
        assert Temperature in quantities

    def test_only_nvml_energy(self):
        """Test parsing only NVML energy metric."""
        dt_read, readers = parse_tracker_spec("0.5,nvml-energy")

        assert dt_read == 0.5
        assert len(readers) == 1
        assert isinstance(readers[0], NVMLReader)
        assert Energy in readers[0].quantities

    def test_rapl_reader_no_quantities_parameter(self):
        """Test that RAPL reader is created without quantities parameter."""
        # RAPL reader doesn't take quantities parameter
        dt_read, readers = parse_tracker_spec("1.0,rapl")

        assert dt_read == 1.0
        assert len(readers) == 1
        assert isinstance(readers[0], RAPLReader)
        # RAPL reader should be initialized without issues


class TestDefaultCliArguments:
    """Tests for CLI argument parsing with tracker specs."""

    def test_default_tracker_configuration(self):
        """Test that default tracker configuration is set correctly."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)
        args = parser.parse_args([])

        # When no --tracker is specified, args.tracker should be empty
        # The default will be applied in main.py
        assert len(args.tracker) == 0

    def test_single_tracker_argument(self):
        """Test parsing a single --tracker argument."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)
        args = parser.parse_args(["--tracker", "0.5,rapl"])

        # User-specified tracker replaces default
        assert len(args.tracker) == 1
        dt_read, readers = args.tracker[0]
        assert dt_read == 0.5
        assert len(readers) == 1
        assert isinstance(readers[0], RAPLReader)

    def test_multiple_tracker_arguments(self):
        """Test parsing multiple --tracker arguments."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)
        args = parser.parse_args(
            [
                "--tracker",
                "0.1,nvml-power",
                "--tracker",
                "1.0,nvml-util",
                "--tracker",
                "0.5,rapl",
            ]
        )

        # Should have 3 trackers (user-specified only)
        assert len(args.tracker) == 3

        # Check first tracker
        dt_read1, readers1 = args.tracker[0]
        assert dt_read1 == 0.1
        assert len(readers1) == 1
        assert isinstance(readers1[0], NVMLReader)

        # Check second tracker
        dt_read2, readers2 = args.tracker[1]
        assert dt_read2 == 1.0
        assert len(readers2) == 1
        assert isinstance(readers2[0], NVMLReader)

        # Check third tracker
        dt_read3, readers3 = args.tracker[2]
        assert dt_read3 == 0.5
        assert len(readers3) == 1
        assert isinstance(readers3[0], RAPLReader)

    def test_tracker_with_other_arguments(self):
        """Test tracker argument combined with other CLI arguments."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)
        args = parser.parse_args(
            [
                "--tracker",
                "0.2,nvml-power,nvml-temp",
                "--suffix",
                "test",
                "--id",
                "experiment-123",
                "--freq-write",
                "1000",
                "--log-level",
                "debug",
            ]
        )

        # Check tracker (user-specified only)
        assert len(args.tracker) == 1
        dt_read, readers = args.tracker[0]
        assert dt_read == 0.2

        # Check other arguments
        assert args.suffix == "test"
        assert args.id == "experiment-123"
        assert args.freq_write == 1000
        assert args.log_level == "debug"

    def test_invalid_tracker_spec_raises_error(self):
        """Test that invalid tracker spec raises appropriate error."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)

        with pytest.raises(SystemExit):  # argparse exits on error
            parser.parse_args(["--tracker", "invalid"])
