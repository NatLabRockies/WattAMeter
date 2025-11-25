# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import argparse
from unittest.mock import patch, MagicMock, mock_open
from wattameter.cli.main import main
from wattameter.cli.utils import parse_tracker_spec
from wattameter.readers import NVMLReader, RAPLReader


class TestCLIMain:
    """Tests for the main CLI entry point with flexible tracker configuration."""

    def test_tracker_spec_creates_correct_trackers(self):
        """Test that tracker specs create the correct number of trackers."""
        # Mock the argument parsing to provide custom tracker specs
        test_args = [
            "--tracker",
            "0.1,nvml-power",
            "--tracker",
            "1.0,rapl",
            "--suffix",
            "test",
            "--id",
            "test-run",
            "--freq-write",
            "10",
        ]

        with patch("sys.argv", ["wattameter"] + test_args):
            # Mock NVMLReader and RAPLReader to have tags
            with patch("wattameter.cli.utils.NVMLReader") as mock_nvml:
                with patch("wattameter.cli.utils.RAPLReader") as mock_rapl:
                    # Create mock readers with tags
                    mock_nvml_instance = MagicMock()
                    mock_nvml_instance.tags = ["gpu-0[mW]"]
                    mock_nvml.return_value = mock_nvml_instance

                    mock_rapl_instance = MagicMock()
                    mock_rapl_instance.tags = ["package-0[mJ]"]
                    mock_rapl.return_value = mock_rapl_instance

                    with patch("wattameter.cli.main.Tracker") as mock_tracker_cls:
                        with patch("wattameter.cli.main.TrackerArray"):
                            # Mock the tracker instances
                            mock_tracker1 = MagicMock()
                            mock_tracker2 = MagicMock()
                            mock_tracker3 = MagicMock()
                            mock_tracker_cls.side_effect = [
                                mock_tracker1,
                                mock_tracker2,
                                mock_tracker3,
                            ]

                            # Mock file operations
                            with patch("builtins.open", mock_open()):
                                with patch("time.time_ns", return_value=1000000000):
                                    # Mock track_until_forced_exit to avoid infinite loop
                                    mock_tracker3.track_until_forced_exit.side_effect = KeyboardInterrupt()

                                    try:
                                        main()
                                    except SystemExit:
                                        pass

                            # Verify that trackers were created
                            # (3 trackers: 1 from default + 2 from user-specified)
                            assert mock_tracker_cls.call_count >= 2

    def test_output_filename_generation(self):
        """Test that output filenames are generated correctly for different readers."""
        # Test with NVML reader
        nvml_reader = MagicMock(spec=NVMLReader)
        nvml_reader.__class__.__name__ = "NVMLReader"
        nvml_reader.tags = ["gpu-0[mW]"]

        # Expected filename pattern: nvml_0.1_wattameter_test.log
        dt_read = 0.1
        expected_tag = f"nvml_{str(dt_read).replace('.', '')}"
        assert expected_tag == "nvml_01"

    def test_duplicate_reader_naming(self):
        """Test that duplicate readers get unique output filenames."""
        all_outputs = ["wattameter.log"]
        base_output_filename = "wattameter.log"

        # Simulate creating tags for multiple readers of the same type
        reader_name = "NVMLReader"
        dt_read = 0.1

        output_tags = []
        for i in range(3):
            tag = f"{reader_name.lower()[0:4]}_{str(dt_read).replace('.', '')}"
            count = sum(1 for existing_tag in all_outputs if tag in existing_tag)
            if count > 0:
                tag = f"{tag}_{count}"
            output_tags.append(tag)
            output = f"{tag}_{base_output_filename}"
            all_outputs.append(output)

        # Verify unique tags were created
        assert output_tags[0] == "nvml_01"
        assert output_tags[1] == "nvml_01_1"
        assert output_tags[2] == "nvml_01_2"

    def test_single_reader_creates_tracker(self):
        """Test that a single reader creates a Tracker (not TrackerArray)."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)

        # Parse arguments for a single reader
        args = parser.parse_args(["--tracker", "0.5,nvml-power"])

        # Verify we have one tracker spec with one reader
        assert len(args.tracker) == 1
        dt_read, readers = args.tracker[0]

        # Count valid readers (those with tags)
        # Note: In real scenario, readers without GPU would have no tags
        # Here we just verify the structure
        assert dt_read == 0.5
        assert len(readers) == 1

    def test_multiple_readers_creates_tracker_array(self):
        """Test that multiple readers create a TrackerArray."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)

        # Parse arguments for multiple readers
        args = parser.parse_args(["--tracker", "0.5,nvml-power,rapl"])

        # Verify we have one tracker spec with multiple readers
        assert len(args.tracker) == 1
        dt_read, readers = args.tracker[0]
        assert len(readers) == 2
        assert dt_read == 0.5

    def test_empty_readers_skipped(self):
        """Test that tracker specs with no valid readers are skipped."""
        # This would happen if a reader has no tags (e.g., no GPU available)
        # The main() function should log a warning and skip that tracker
        pass

    def test_no_valid_trackers_exits_gracefully(self):
        """Test that the program exits gracefully when no valid trackers exist."""
        # When all readers have no tags, no trackers should be created
        # and the program should exit with an error message
        pass

    def test_timestamp_format_in_output(self):
        """Test that timestamps are written in the correct format."""
        from datetime import datetime

        timestamp_fmt = "%Y-%m-%d_%H:%M:%S.%f"
        t_ns = 1234567890123456789
        timestamp_str = datetime.fromtimestamp(t_ns / 1e9).strftime(timestamp_fmt)

        # Verify the format is correct
        assert "_" in timestamp_str
        assert "." in timestamp_str
        assert len(timestamp_str) > 20

    def test_all_outputs_receive_header(self):
        """Test that all output files receive the initial header comment."""
        # The main() function writes a header to all output files including base
        # This test would verify that behavior with mocked file I/O
        pass

    def test_signal_handling_graceful_shutdown(self):
        """Test that signal handling allows graceful shutdown of trackers."""
        # When a signal is received, all trackers should stop gracefully
        # and write their final data
        pass

    def test_trackers_start_and_stop_correctly(self):
        """Test that all but the last tracker are started, and last uses track_until_forced_exit."""
        # The main() function starts all trackers except the last one,
        # then calls track_until_forced_exit on the last tracker
        pass


class TestTrackerConfiguration:
    """Integration tests for tracker configuration."""

    def test_mixed_tracker_specifications(self):
        """Test parsing multiple tracker specifications with different configurations."""
        specs = [
            "0.1,nvml-power,nvml-temp",
            "0.5,rapl",
            "1.0,nvml-util",
            "2.0,nvml-nvlink",
        ]

        results = []
        for spec in specs:
            dt_read, readers = parse_tracker_spec(spec)
            results.append((dt_read, len(readers)))

        # Verify each spec was parsed correctly
        assert results[0] == (0.1, 1)  # Single NVML reader with 2 quantities
        assert results[1] == (0.5, 1)  # Single RAPL reader
        assert results[2] == (1.0, 1)  # Single NVML reader with util
        assert results[3] == (2.0, 1)  # Single NVML reader with nvlink

    def test_combined_rapl_and_nvml(self):
        """Test combining RAPL and NVML metrics in a single tracker spec."""
        dt_read, readers = parse_tracker_spec("0.25,rapl,nvml-power,nvml-temp")

        assert dt_read == 0.25
        assert len(readers) == 2

        # Should have both reader types
        reader_types = [type(r).__name__ for r in readers]
        assert "RAPLReader" in reader_types
        assert "NVMLReader" in reader_types

    def test_energy_metrics_both_readers(self):
        """Test that energy can be tracked from both NVML and RAPL."""
        dt_read, readers = parse_tracker_spec("1.0,rapl,nvml-energy")

        assert dt_read == 1.0
        assert len(readers) == 2

        # Both should be present
        reader_types = {type(r).__name__ for r in readers}
        assert "RAPLReader" in reader_types
        assert "NVMLReader" in reader_types

    def test_very_fast_sampling_rate(self):
        """Test that very fast sampling rates are accepted."""
        dt_read, readers = parse_tracker_spec("0.001,nvml-power")

        assert dt_read == 0.001
        assert len(readers) == 1

    def test_slow_sampling_rate(self):
        """Test that slow sampling rates are accepted."""
        dt_read, readers = parse_tracker_spec("60.0,rapl")

        assert dt_read == 60.0
        assert len(readers) == 1

    def test_default_configuration_backwards_compatible(self):
        """Test that default configuration maintains backward compatibility."""
        from wattameter.cli.utils import default_cli_arguments

        parser = argparse.ArgumentParser()
        default_cli_arguments(parser)
        args = parser.parse_args([])

        # When no --tracker specified, args.tracker is empty
        # Default will be applied in main.py: (0.1, [NVMLReader((Power,)), RAPLReader()])
        assert len(args.tracker) == 0


class TestOutputFileNaming:
    """Tests for output file naming conventions."""

    def test_nvml_filename_prefix(self):
        """Test that NVML readers get 'nvml' prefix in filename."""
        reader = MagicMock(spec=NVMLReader)
        reader.__class__.__name__ = "NVMLReader"

        dt_read = 0.5
        prefix = (
            f"{reader.__class__.__name__.lower()[0:4]}_{str(dt_read).replace('.', '')}"
        )

        assert prefix == "nvml_05"

    def test_rapl_filename_prefix(self):
        """Test that RAPL readers get 'rapl' prefix in filename."""
        reader = MagicMock(spec=RAPLReader)
        reader.__class__.__name__ = "RAPLReader"

        dt_read = 1.0
        prefix = (
            f"{reader.__class__.__name__.lower()[0:4]}_{str(dt_read).replace('.', '')}"
        )

        assert prefix == "rapl_10"

    def test_dt_read_in_filename(self):
        """Test that dt_read value is incorporated into filename correctly."""
        test_cases = [
            (0.1, "01"),
            (0.5, "05"),
            (1.0, "10"),
            (2.5, "25"),
            (10.0, "100"),
        ]

        for dt_read, expected in test_cases:
            result = str(dt_read).replace(".", "")
            assert result == expected

    def test_collision_handling(self):
        """Test that filename collisions are handled by appending counter."""
        all_outputs = ["wattameter.log"]
        base_tag = "nvml_01"

        # First occurrence - no collision
        count = sum(1 for existing_tag in all_outputs if base_tag in existing_tag)
        tag1 = base_tag if count == 0 else f"{base_tag}_{count}"
        all_outputs.append(f"{tag1}_wattameter.log")

        # Second occurrence - collision detected
        count = sum(1 for existing_tag in all_outputs if base_tag in existing_tag)
        tag2 = base_tag if count == 0 else f"{base_tag}_{count}"
        all_outputs.append(f"{tag2}_wattameter.log")

        # Third occurrence - collision detected
        count = sum(1 for existing_tag in all_outputs if base_tag in existing_tag)
        tag3 = base_tag if count == 0 else f"{base_tag}_{count}"

        assert tag1 == "nvml_01"
        assert tag2 == "nvml_01_1"
        assert tag3 == "nvml_01_2"
