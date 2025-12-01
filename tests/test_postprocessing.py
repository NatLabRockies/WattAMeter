"""
Test suite for postprocessing.py module.

This module tests the postprocessing utility functions:
- file_to_df: Convert Wattameter output files to pandas DataFrames
- align_and_concat_df: Align and concatenate multiple DataFrames with time indices
"""

import pytest
from datetime import datetime
from io import StringIO
import tempfile
import os
import sys
import importlib.util

# Skip this test module if pandas is not available
pd = pytest.importorskip("pandas")

# Add the src directory to the path so we can import our module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wattameter.utils.postprocessing import file_to_df, align_and_concat_df

# Check if scipy is available
HAS_SCIPY = importlib.util.find_spec("scipy") is not None


class TestFileToDf:
    """Test suite for the file_to_df function."""

    def test_basic_file_conversion(self):
        """Test basic file conversion with default parameters."""
        file_content = """# WattAMeter Output
# Timestamp Power Temperature
2024-01-01_10:00:00.000000 100.5 45.2
2024-01-01_10:00:01.000000 105.3 46.1
2024-01-01_10:00:02.000000 98.7 44.8
"""
        f = StringIO(file_content)
        df = file_to_df(f)

        assert len(df) == 3
        assert list(df.columns) == ["Power", "Temperature"]
        assert df.index.name == "Timestamp"
        assert isinstance(df.index[0], datetime)
        assert df["Power"].iloc[0] == 100.5
        assert df["Temperature"].iloc[0] == 45.2

    def test_custom_header(self):
        """Test file conversion with custom header."""
        file_content = """# WattAMeter Output
2024-01-01_10:00:00.000000 100.5 45.2
2024-01-01_10:00:01.000000 105.3 46.1
"""
        f = StringIO(file_content)
        custom_header = ["Timestamp", "CustomPower", "CustomTemp"]
        df = file_to_df(f, header=custom_header)

        assert len(df) == 2
        assert list(df.columns) == ["CustomPower", "CustomTemp"]
        assert df.index.name == "Timestamp"

    def test_custom_timestamp_format(self):
        """Test file conversion with custom timestamp format."""
        file_content = """# Header line
# Timestamp Power
01/01/2024-10:00:00 100.5
01/01/2024-10:00:01 105.3
"""
        f = StringIO(file_content)
        df = file_to_df(f, timestamp_fmt="%m/%d/%Y-%H:%M:%S")

        assert len(df) == 2
        assert isinstance(df.index[0], datetime)
        assert df.index[0].month == 1
        assert df.index[0].day == 1
        assert df.index[0].year == 2024

    def test_skip_lines_parameter(self):
        """Test file conversion with different skip_lines values."""
        file_content = """# Line 1
# Line 2
# Line 3
# Timestamp Power
2024-01-01_10:00:00.000000 100.5
2024-01-01_10:00:01.000000 105.3
"""
        f = StringIO(file_content)
        df = file_to_df(f, skip_lines=3)

        assert len(df) == 2
        assert "Power" in df.columns

    def test_missing_values_handling(self):
        """Test that missing values are handled correctly."""
        file_content = """# Header
# Timestamp Power Temperature
2024-01-01_10:00:00.000000 100.5
2024-01-01_10:00:01.000000 105.3 46.1
"""
        f = StringIO(file_content)
        df = file_to_df(f)

        assert len(df) == 2
        # First row should have NaN for Temperature since it's missing
        assert pd.isna(df["Temperature"].iloc[0])
        assert df["Temperature"].iloc[1] == 46.1

    def test_multiple_numeric_columns(self):
        """Test conversion with multiple numeric columns."""
        file_content = """# Header
# Timestamp Power Energy Temp CPU GPU
2024-01-01_10:00:00.000000 100.5 500.2 45.3 55.1 72.8
2024-01-01_10:00:01.000000 105.3 520.1 46.1 56.2 73.5
"""
        f = StringIO(file_content)
        df = file_to_df(f)

        assert len(df) == 2
        assert len(df.columns) == 5
        assert list(df.columns) == ["Power", "Energy", "Temp", "CPU", "GPU"]
        # All columns should be numeric
        for dtype in df.dtypes:
            assert pd.api.types.is_numeric_dtype(dtype)

    def test_empty_file_handling(self):
        """Test handling of empty or minimal files."""
        file_content = """# Header
# Timestamp Power
"""
        f = StringIO(file_content)
        df = file_to_df(f)

        assert len(df) == 0
        assert "Power" in df.columns

    def test_with_actual_file(self):
        """Test conversion from an actual file on disk."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp:
            tmp.write("# WattAMeter Output\n")
            tmp.write("# Timestamp Power Temperature\n")
            tmp.write("2024-01-01_10:00:00.000000 100.5 45.2\n")
            tmp.write("2024-01-01_10:00:01.000000 105.3 46.1\n")
            tmp_path = tmp.name

        try:
            with open(tmp_path, "r") as f:
                df = file_to_df(f)

            assert len(df) == 2
            assert list(df.columns) == ["Power", "Temperature"]
        finally:
            os.unlink(tmp_path)


class TestAlignAndConcatDf:
    """Test suite for the align_and_concat_df function."""

    def test_basic_alignment(self):
        """Test basic alignment of two dataframes."""
        # Create two dataframes with slightly different time indices
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df1 = pd.DataFrame({"Power": [100, 101, 102, 103, 104]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df2 = pd.DataFrame({"Power": [200, 201, 202, 203, 204]}, index=idx2)

        result = align_and_concat_df([df1, df2], dt=1.0)

        assert len(result) == 5
        # Columns should be prefixed with index
        assert "0_Power" in result.columns
        assert "1_Power" in result.columns

    def test_alignment_with_offset_start_times(self, capsys):
        """Test alignment when dataframes have different start times."""
        # df1 starts earlier
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=10, freq="1s")
        df1 = pd.DataFrame({"Power": range(10)}, index=idx1)

        # df2 starts 3 seconds later
        idx2 = pd.date_range("2024-01-01 10:00:03", periods=7, freq="1s")
        df2 = pd.DataFrame({"Power": range(100, 107)}, index=idx2)

        result = align_and_concat_df([df1, df2], dt=1.0)

        # Result should start at the later start time (10:00:03)
        # and end at the earlier end time (10:00:09)
        assert len(result) == 7
        captured = capsys.readouterr()
        assert "Common start time" in captured.out

    @pytest.mark.skipif(not HAS_SCIPY, reason="scipy required for interpolation")
    def test_custom_dt_parameter(self, capsys):
        """Test using custom dt parameter."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df1 = pd.DataFrame({"Power": [100, 101, 102, 103, 104]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df2 = pd.DataFrame({"Power": [200, 201, 202, 203, 204]}, index=idx2)

        result = align_and_concat_df([df1, df2], dt=0.5)

        captured = capsys.readouterr()
        assert "Using user-provided dt = 0.5 seconds" in captured.out
        # With dt=0.5, we should have approximately twice as many points
        assert len(result) > 5

    def test_auto_dt_calculation(self, capsys):
        """Test automatic dt calculation from dataframes."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="2s")
        df1 = pd.DataFrame({"Power": [100, 101, 102, 103, 104]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="2s")
        df2 = pd.DataFrame({"Power": [200, 201, 202, 203, 204]}, index=idx2)

        result = align_and_concat_df([df1, df2])

        captured = capsys.readouterr()
        assert "Average dt per node:" in captured.out
        assert "Using dt = 2.0 seconds" in captured.out
        assert len(result) == 5

    def test_start_at_0_option(self):
        """Test the start_at_0 option."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df1 = pd.DataFrame({"Power": [100, 101, 102, 103, 104]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df2 = pd.DataFrame({"Power": [200, 201, 202, 203, 204]}, index=idx2)

        result = align_and_concat_df([df1, df2], dt=1.0, start_at_0=True)

        # Index should start at 0
        assert result.index[0] == 0
        assert result.index[1] == 1.0
        assert result.index[-1] == 4.0

    @pytest.mark.skipif(not HAS_SCIPY, reason="scipy required for interpolation")
    def test_interpolation(self):
        """Test that interpolation works correctly."""
        # Create dataframes with gaps
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=3, freq="2s")
        df1 = pd.DataFrame({"Power": [100, 120, 140]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=3, freq="2s")
        df2 = pd.DataFrame({"Power": [200, 220, 240]}, index=idx2)

        # Request dt=1s, which will require interpolation
        result = align_and_concat_df([df1, df2], dt=1.0)

        # Check that interpolated values exist
        assert len(result) > 3
        # The interpolation should create values between the original points

    def test_multiple_dataframes(self):
        """Test alignment with more than two dataframes."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df1 = pd.DataFrame({"Power": [100, 101, 102, 103, 104]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df2 = pd.DataFrame({"Power": [200, 201, 202, 203, 204]}, index=idx2)

        idx3 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df3 = pd.DataFrame({"Power": [300, 301, 302, 303, 304]}, index=idx3)

        result = align_and_concat_df([df1, df2, df3], dt=1.0)

        assert "0_Power" in result.columns
        assert "1_Power" in result.columns
        assert "2_Power" in result.columns

    def test_multiple_columns_per_dataframe(self):
        """Test alignment with dataframes containing multiple columns."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df1 = pd.DataFrame(
            {"Power": [100, 101, 102, 103, 104], "Temp": [45, 46, 47, 48, 49]},
            index=idx1,
        )

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df2 = pd.DataFrame(
            {"Power": [200, 201, 202, 203, 204], "Temp": [55, 56, 57, 58, 59]},
            index=idx2,
        )

        result = align_and_concat_df([df1, df2], dt=1.0)

        assert "0_Power" in result.columns
        assert "0_Temp" in result.columns
        assert "1_Power" in result.columns
        assert "1_Temp" in result.columns

    def test_misaligned_end_times(self):
        """Test handling of dataframes with different end times."""
        # df1 is longer
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=10, freq="1s")
        df1 = pd.DataFrame({"Power": range(10)}, index=idx1)

        # df2 is shorter
        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df2 = pd.DataFrame({"Power": range(100, 105)}, index=idx2)

        result = align_and_concat_df([df1, df2], dt=1.0)

        # Result should end at the earlier end time
        assert len(result) == 5

    def test_single_dataframe(self):
        """Test alignment with a single dataframe."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df1 = pd.DataFrame({"Power": [100, 101, 102, 103, 104]}, index=idx1)

        result = align_and_concat_df([df1], dt=1.0)

        assert len(result) == 5
        assert "0_Power" in result.columns

    def test_preserves_datetime_index_when_not_start_at_0(self):
        """Test that datetime index is preserved when start_at_0 is False."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df1 = pd.DataFrame({"Power": [100, 101, 102, 103, 104]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=5, freq="1s")
        df2 = pd.DataFrame({"Power": [200, 201, 202, 203, 204]}, index=idx2)

        result = align_and_concat_df([df1, df2], dt=1.0, start_at_0=False)

        # Index should still be datetime objects
        assert isinstance(result.index[0], pd.Timestamp)

    @pytest.mark.skipif(not HAS_SCIPY, reason="scipy required for interpolation")
    def test_very_small_dt(self):
        """Test with very small dt values (subsecond)."""
        idx1 = pd.date_range("2024-01-01 10:00:00", periods=3, freq="1s")
        df1 = pd.DataFrame({"Power": [100, 101, 102]}, index=idx1)

        idx2 = pd.date_range("2024-01-01 10:00:00", periods=3, freq="1s")
        df2 = pd.DataFrame({"Power": [200, 201, 202]}, index=idx2)

        result = align_and_concat_df([df1, df2], dt=0.1)

        # With dt=0.1s over 2 seconds, we should have about 21 points
        assert len(result) > 10


class TestIntegration:
    """Integration tests combining both functions."""

    def test_file_to_df_then_align(self):
        """Test reading files and then aligning them."""
        # Create two temporary files
        file1_content = """# WattAMeter Output
# Timestamp Power
2024-01-01_10:00:00.000000 100.0
2024-01-01_10:00:01.000000 101.0
2024-01-01_10:00:02.000000 102.0
2024-01-01_10:00:03.000000 103.0
"""
        file2_content = """# WattAMeter Output
# Timestamp Power
2024-01-01_10:00:00.000000 200.0
2024-01-01_10:00:01.000000 201.0
2024-01-01_10:00:02.000000 202.0
2024-01-01_10:00:03.000000 203.0
"""
        f1 = StringIO(file1_content)
        f2 = StringIO(file2_content)

        df1 = file_to_df(f1)
        df2 = file_to_df(f2)

        result = align_and_concat_df([df1, df2], dt=1.0)

        assert len(result) == 4
        assert "0_Power" in result.columns
        assert "1_Power" in result.columns
        # Values should be combined
        assert result["0_Power"].iloc[0] == 100.0
        assert result["1_Power"].iloc[0] == 200.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
