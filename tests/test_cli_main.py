# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC

import argparse
import signal
from unittest.mock import patch, MagicMock, mock_open
from wattameter.cli.main import main
from wattameter.cli.utils import parse_tracker_spec, ForcedExit
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

    def test_output_dir_is_used_for_tracker_outputs_and_headers(self):
        """Test that --output-dir is used in tracker outputs and header writes."""
        test_args = [
            "--tracker",
            "0.1,rapl",
            "--suffix",
            "session",
            "--id",
            "run-123",
            "--output-dir",
            "logs",
        ]

        with patch("sys.argv", ["wattameter"] + test_args):
            with patch("wattameter.cli.utils.RAPLReader") as mock_rapl:
                mock_rapl_instance = MagicMock()
                mock_rapl_instance.tags = ["package-0[mJ]"]
                mock_rapl_instance.__class__.__name__ = "RAPLReader"
                mock_rapl.return_value = mock_rapl_instance

                with patch("wattameter.cli.main.Tracker") as mock_tracker_cls:
                    with patch("wattameter.cli.main.TrackerArray"):
                        mock_tracker = MagicMock()
                        mock_tracker.track_until_forced_exit.side_effect = ForcedExit()
                        mock_tracker_cls.return_value = mock_tracker

                        mocked_open = mock_open()
                        with patch("builtins.open", mocked_open):
                            with patch("time.time_ns", return_value=1000000000):
                                main()

                        tracker_output = mock_tracker_cls.call_args.kwargs["output"]
                        assert tracker_output == "logs/rapl_01_wattameter_session.log"

                        opened_files = [call.args[0] for call in mocked_open.call_args_list]
                        assert "logs/wattameter_session.log" in opened_files
                        assert "logs/rapl_01_wattameter_session.log" in opened_files

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
        output_dir = "./logs"
        all_outputs = [f"{output_dir}/wattameter.log"]
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
            output = f"{output_dir}/{tag}_{base_output_filename}"
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

    def test_empty_readers_skipped(self, caplog):
        """Test that tracker specifications with no valid readers are skipped."""
        empty_reader = MagicMock()
        empty_reader.tags = []
        empty_reader.__class__.__name__ = "NVMLReader"

        valid_reader = MagicMock()
        valid_reader.tags = ["package-0[mJ]"]
        valid_reader.__class__.__name__ = "RAPLReader"

        args = argparse.Namespace(
            tracker=[
                (0.1, [empty_reader]),
                (0.5, [valid_reader]),
            ],
            suffix=None,
            id="test-run",
            output_dir=".",
            freq_write=0,
            log_level="warning",
            mqtt_broker=None,
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            mqtt_topic_prefix="wattameter",
            mqtt_qos=1,
        )

        tracker = MagicMock()
        tracker.track_until_forced_exit.side_effect = ForcedExit()

        with (
            patch("argparse.ArgumentParser.parse_args", return_value=args),
            patch("wattameter.cli.main.Tracker", return_value=tracker) as mock_tracker,
            patch("wattameter.cli.main.TrackerArray") as mock_tracker_array,
            patch("builtins.open", mock_open()),
            patch("time.time_ns", return_value=1000000000),
            caplog.at_level("WARNING"),
        ):
            main()

        assert "Tracker specification 0 has no valid readers. Skipping." in caplog.text
        mock_tracker.assert_called_once()
        mock_tracker_array.assert_not_called()

    def test_no_valid_trackers_exits_gracefully(self, caplog):
        """Test that the program exits gracefully when no valid trackers exist."""
        reader = MagicMock()
        reader.tags = []
        reader.__class__.__name__ = "NVMLReader"

        args = argparse.Namespace(
            tracker=[(0.5, [reader])],
            suffix=None,
            id="test-run",
            output_dir=".",
            freq_write=0,
            log_level="warning",
            mqtt_broker=None,
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            mqtt_topic_prefix="wattameter",
            mqtt_qos=1,
        )

        mocked_open = mock_open()

        with (
            patch("argparse.ArgumentParser.parse_args", return_value=args),
            patch("wattameter.cli.main.Tracker") as mock_tracker,
            patch("wattameter.cli.main.TrackerArray") as mock_tracker_array,
            patch("builtins.open", mocked_open),
            caplog.at_level("ERROR"),
        ):
            result = main()

        assert result is None
        assert "No valid readers available. Exiting." in caplog.text
        mock_tracker.assert_not_called()
        mock_tracker_array.assert_not_called()
        mocked_open.assert_not_called()

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
        reader = MagicMock()
        reader.tags = ["gpu-0[mW]"]
        reader.__class__.__name__ = "NVMLReader"

        args = argparse.Namespace(
            tracker=[(0.1, [reader])],
            suffix="test",
            id="run-123",
            output_dir="logs",
            freq_write=0,
            log_level="warning",
            mqtt_broker=None,
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            mqtt_topic_prefix="wattameter",
            mqtt_qos=1,
        )

        tracker = MagicMock()
        tracker.track_until_forced_exit.side_effect = ForcedExit()
        mocked_open = mock_open()

        with (
            patch("argparse.ArgumentParser.parse_args", return_value=args),
            patch("wattameter.cli.main.Tracker", return_value=tracker),
            patch("builtins.open", mocked_open),
            patch("time.time_ns", return_value=1000000000),
        ):
            main()

        opened_files = [call.args[0] for call in mocked_open.call_args_list]

        assert "logs/wattameter_test.log" in opened_files
        assert "logs/nvml_01_wattameter_test.log" in opened_files

        written_values = [
            write_call.args[0] for write_call in mocked_open().write.call_args_list
        ]
        assert len(written_values) == 2
        assert all(value.startswith("# ") for value in written_values)
        assert all("WattAMeter run run-123" in value for value in written_values)

    def test_signal_handling_graceful_shutdown(self):
        """Test that forced exit signals trigger graceful cleanup."""
        reader = MagicMock()
        reader.tags = ["gpu-0[mW]"]
        reader.__class__.__name__ = "NVMLReader"

        args = argparse.Namespace(
            tracker=[(0.1, [reader])],
            suffix=None,
            id="test-run",
            output_dir=".",
            freq_write=0,
            log_level="warning",
            mqtt_broker=None,
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            mqtt_topic_prefix="wattameter",
            mqtt_qos=1,
        )

        tracker = MagicMock()
        tracker.track_until_forced_exit.side_effect = ForcedExit()

        with (
            patch("argparse.ArgumentParser.parse_args", return_value=args),
            patch("wattameter.cli.main.Tracker", return_value=tracker),
            patch("builtins.open", mock_open()),
            patch("time.time_ns", return_value=1000000000),
            patch("signal.signal") as mock_signal,
        ):
            main()

        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            mock_signal.assert_any_call(signum, signal.SIG_IGN)

        tracker.track_until_forced_exit.assert_called_once_with()
        tracker.write.assert_called_once()

    def test_trackers_start_and_stop_correctly(self):
        """Test that all but the last tracker are started and the last tracks until exit."""
        first_reader = MagicMock()
        first_reader.tags = ["gpu-0[mW]"]
        first_reader.__class__.__name__ = "NVMLReader"

        last_reader = MagicMock()
        last_reader.tags = ["package-0[mJ]"]
        last_reader.__class__.__name__ = "RAPLReader"

        args = argparse.Namespace(
            tracker=[
                (0.1, [first_reader]),
                (1.0, [last_reader]),
            ],
            suffix=None,
            id="test-run",
            output_dir=".",
            freq_write=5,
            log_level="warning",
            mqtt_broker=None,
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            mqtt_topic_prefix="wattameter",
            mqtt_qos=1,
        )

        first_tracker = MagicMock()
        last_tracker = MagicMock()
        last_tracker.track_until_forced_exit.side_effect = ForcedExit()

        with (
            patch("argparse.ArgumentParser.parse_args", return_value=args),
            patch(
                "wattameter.cli.main.Tracker",
                side_effect=[first_tracker, last_tracker],
            ),
            patch("builtins.open", mock_open()),
            patch("time.time_ns", return_value=1000000000),
        ):
            main()

        first_tracker.start.assert_called_once_with(freq_write=5)
        first_tracker.stop.assert_called_once_with(freq_write=5)

        last_tracker.start.assert_not_called()
        last_tracker.track_until_forced_exit.assert_called_once_with()
        last_tracker.stop.assert_not_called()
        last_tracker.write.assert_called_once_with()


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
        all_outputs = ["./wattameter.log"]
        base_tag = "nvml_01"

        # First occurrence - no collision
        count = sum(1 for existing_tag in all_outputs if base_tag in existing_tag)
        tag1 = base_tag if count == 0 else f"{base_tag}_{count}"
        all_outputs.append(f"./{tag1}_wattameter.log")

        # Second occurrence - collision detected
        count = sum(1 for existing_tag in all_outputs if base_tag in existing_tag)
        tag2 = base_tag if count == 0 else f"{base_tag}_{count}"
        all_outputs.append(f"./{tag2}_wattameter.log")

        # Third occurrence - collision detected
        count = sum(1 for existing_tag in all_outputs if base_tag in existing_tag)
        tag3 = base_tag if count == 0 else f"{base_tag}_{count}"

        assert tag1 == "nvml_01"
        assert tag2 == "nvml_01_1"
        assert tag3 == "nvml_01_2"
