# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import csv
import os
import tempfile
import unittest.mock
from pathlib import Path

import pytest

from wattameter.utils.codecarbon import add_cpu


class TestAddCPU:
    """Test suite for the add_cpu function."""

    def test_add_cpu_new_entry(self):
        """Test adding a new CPU entry to the database."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            # Write initial CSV content
            writer = csv.writer(temp_file)
            writer.writerow(["Intel Core i7-8700K", "95"])
            writer.writerow(["AMD Ryzen 7 3700X", "65"])
            temp_file.flush()

            # Mock the resources.path to return our temporary file
            with unittest.mock.patch(
                "wattameter.utils.codecarbon.resources.path"
            ) as mock_path:
                mock_path.return_value.__enter__.return_value = Path(temp_file.name)

                # Test adding a new CPU
                result = add_cpu("Intel Core i9-9900K", 95.0)

                # Should return True for new entry
                assert result is True

                # Verify the entry was added
                with open(temp_file.name, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    assert len(rows) == 3
                    assert ["Intel Core i9-9900K", "95.0"] in rows

        # Clean up
        Path(temp_file.name).unlink()

    def test_add_cpu_duplicate_entry(self):
        """Test adding a duplicate CPU entry returns False."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            # Write initial CSV content with the CPU we'll try to add
            writer = csv.writer(temp_file)
            writer.writerow(["Intel Core i7-8700K", "95"])
            writer.writerow(["AMD Ryzen 7 3700X", "65"])
            writer.writerow(["Intel Core i9-9900K", "95.0"])
            temp_file.flush()

            # Mock the resources.path to return our temporary file
            with unittest.mock.patch(
                "wattameter.utils.codecarbon.resources.path"
            ) as mock_path:
                mock_path.return_value.__enter__.return_value = Path(temp_file.name)

                # Test adding a duplicate CPU
                result = add_cpu("Intel Core i9-9900K", 95.0)

                # Should return False for duplicate entry
                assert result is False

                # Verify no new entry was added
                with open(temp_file.name, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    assert len(rows) == 3  # Should still be 3 rows

        # Clean up
        Path(temp_file.name).unlink()

    def test_add_cpu_empty_database(self):
        """Test adding a CPU to an empty database."""
        # Create an empty temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.flush()

            # Mock the resources.path to return our temporary file
            with unittest.mock.patch(
                "wattameter.utils.codecarbon.resources.path"
            ) as mock_path:
                mock_path.return_value.__enter__.return_value = Path(temp_file.name)

                # Test adding a CPU to empty database
                result = add_cpu("Intel Core i5-10400", 65.0)

                # Should return True for new entry
                assert result is True

                # Verify the entry was added
                with open(temp_file.name, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    assert len(rows) == 1
                    assert rows[0] == ["Intel Core i5-10400", "65.0"]

        # Clean up
        Path(temp_file.name).unlink()

    def test_add_cpu_string_conversion(self):
        """Test that TDP is properly converted to string."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.flush()

            # Mock the resources.path to return our temporary file
            with unittest.mock.patch(
                "wattameter.utils.codecarbon.resources.path"
            ) as mock_path:
                mock_path.return_value.__enter__.return_value = Path(temp_file.name)

                # Test with integer TDP
                result = add_cpu("Intel Core i3-10100", 65)
                assert result is True

                # Test with float TDP
                result = add_cpu("AMD Ryzen 5 3600", 65.5)
                assert result is True

                # Verify both entries were added with proper string conversion
                with open(temp_file.name, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    assert len(rows) == 2
                    assert ["Intel Core i3-10100", "65"] in rows
                    assert ["AMD Ryzen 5 3600", "65.5"] in rows

        # Clean up
        Path(temp_file.name).unlink()

    def test_add_cpu_case_sensitivity(self):
        """Test that CPU names are case-sensitive."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            # Write initial CSV content
            writer = csv.writer(temp_file)
            writer.writerow(["intel core i7-8700k", "95"])
            temp_file.flush()

            # Mock the resources.path to return our temporary file
            with unittest.mock.patch(
                "wattameter.utils.codecarbon.resources.path"
            ) as mock_path:
                mock_path.return_value.__enter__.return_value = Path(temp_file.name)

                # Test adding with different case
                result = add_cpu("Intel Core i7-8700K", 95.0)

                # Should return True (case-sensitive, so it's a new entry)
                assert result is True

                # Verify both entries exist
                with open(temp_file.name, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    assert len(rows) == 2
                    assert ["intel core i7-8700k", "95"] in rows
                    assert ["Intel Core i7-8700K", "95.0"] in rows

        # Clean up
        Path(temp_file.name).unlink()

    @pytest.mark.parametrize(
        "cpu_model,tdp",
        [
            ("Intel Xeon Platinum 8470QL", 95.0),
            ("AMD EPYC 7763", 280.0),
            ("Apple M1", 20.0),
            ("ARM Cortex-A78", 5.5),
        ],
    )
    def test_add_cpu_various_models(self, cpu_model, tdp):
        """Test adding various CPU models and TDP values."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.flush()

            # Mock the resources.path to return our temporary file
            with unittest.mock.patch(
                "wattameter.utils.codecarbon.resources.path"
            ) as mock_path:
                mock_path.return_value.__enter__.return_value = Path(temp_file.name)

                # Test adding the CPU
                result = add_cpu(cpu_model, tdp)

                # Should return True for new entry
                assert result is True

                # Verify the entry was added correctly
                with open(temp_file.name, "r", encoding="utf-8") as csvfile:
                    reader = csv.reader(csvfile)
                    rows = list(reader)
                    assert len(rows) == 1
                    assert rows[0] == [cpu_model, str(tdp)]

        # Clean up
        Path(temp_file.name).unlink()

    @pytest.mark.skipif(os.geteuid() == 0, reason="Test skipped when running as root")
    def test_add_cpu_file_permissions(self):
        """Test behavior when the CSV file cannot be written to."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.flush()

            # Make the file read-only
            Path(temp_file.name).chmod(0o444)

            # Mock the resources.path to return our temporary file
            with unittest.mock.patch(
                "wattameter.utils.codecarbon.resources.path"
            ) as mock_path:
                mock_path.return_value.__enter__.return_value = Path(temp_file.name)

                # Test adding a CPU when file is read-only
                with pytest.raises(PermissionError):
                    add_cpu("Intel Core i7-8700K", 95.0)

        # Clean up
        Path(temp_file.name).chmod(0o644)  # Restore permissions
        Path(temp_file.name).unlink()
