import pytest
import logging
import tempfile
import os
import shutil
from unittest.mock import patch, mock_open
import numpy as np

# Add the src directory to the path so we can import our module
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from wattameter.readers.rapl import RAPLDevice, RAPLReader, _get_rapl_domain_name
from wattameter.readers.utils import Energy, Second, Temperature


class TestRAPLDomainName:
    """Test cases for _get_rapl_domain_name function."""

    def test_get_rapl_domain_name_simple(self):
        """Test domain name generation for simple case."""
        with patch("builtins.open", mock_open(read_data="package-0\n")):
            name = _get_rapl_domain_name("/sys/class/powercap/intel-rapl:0", "unknown")
            assert name == "cpu-0"

    def test_get_rapl_domain_name_nested(self):
        """Test domain name generation for nested case."""

        def mock_open_side_effect(filepath, mode="r"):
            if filepath.endswith("intel-rapl:0/name"):
                return mock_open(read_data="package-0\n").return_value
            elif filepath.endswith("intel-rapl:0:0/name"):
                return mock_open(read_data="core\n").return_value
            else:
                raise FileNotFoundError()

        with patch("builtins.open", side_effect=mock_open_side_effect):
            name = _get_rapl_domain_name(
                "/sys/class/powercap/intel-rapl:0:0", "unknown"
            )
            assert name == "cpu-0-core"

    def test_get_rapl_domain_name_file_not_found(self):
        """Test domain name generation when name file is not found."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            name = _get_rapl_domain_name("/sys/class/powercap/intel-rapl:0", "unknown")
            assert name == "0"

    def test_get_rapl_domain_name_permission_error(self):
        """Test domain name generation when permission is denied."""
        with patch("builtins.open", side_effect=PermissionError()):
            name = _get_rapl_domain_name("/sys/class/powercap/intel-rapl:0", "unknown")
            assert name == "0"

    def test_get_rapl_domain_name_no_digit(self):
        """Test domain name generation when path has no digit."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            name = _get_rapl_domain_name("/sys/class/powercap/intel-rapl", "fallback")
            assert name == "fallback"

    def test_get_rapl_domain_name_package_replacement(self):
        """Test that package- prefix is replaced with cpu-."""
        with patch("builtins.open", mock_open(read_data="package-1\n")):
            name = _get_rapl_domain_name("/sys/class/powercap/intel-rapl:1", "unknown")
            assert name == "cpu-1"

    def test_get_rapl_domain_name_other_names(self):
        """Test domain name generation for non-package names."""
        with patch("builtins.open", mock_open(read_data="dram\n")):
            name = _get_rapl_domain_name(
                "/sys/class/powercap/intel-rapl:0:1", "unknown"
            )
            assert name == "dram-dram"


class TestRAPLDevice:
    """Test cases for RAPLDevice class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary directory structure
        self.temp_dir = tempfile.mkdtemp()
        self.rapl_device_path = os.path.join(self.temp_dir, "intel-rapl:0")
        os.makedirs(self.rapl_device_path)

    def teardown_method(self):
        """Clean up after each test method."""
        shutil.rmtree(self.temp_dir)

    def create_rapl_files(
        self, name="package-0", max_energy="1000000000", energy="500000"
    ):
        """Helper to create RAPL device files."""
        # Create name file
        with open(os.path.join(self.rapl_device_path, "name"), "w") as f:
            f.write(f"{name}\n")

        # Create max_energy_range_uj file
        with open(os.path.join(self.rapl_device_path, "max_energy_range_uj"), "w") as f:
            f.write(f"{max_energy}\n")

        # Create energy_uj file
        with open(os.path.join(self.rapl_device_path, "energy_uj"), "w") as f:
            f.write(f"{energy}\n")

    def test_init_success(self):
        """Test successful initialization of RAPLDevice."""
        self.create_rapl_files()

        with patch(
            "wattameter.readers.rapl._get_rapl_domain_name", return_value="cpu-0"
        ):
            device = RAPLDevice(self.rapl_device_path)

        assert device.name == "package-0"
        assert device.max_energy_range == 1000000000
        assert device.path == self.rapl_device_path
        assert device.quantities == (Energy,)
        assert device.energy_file is not None

    def test_init_missing_name_file(self, caplog):
        """Test initialization when name file is missing."""
        # Create only some files
        with open(os.path.join(self.rapl_device_path, "max_energy_range_uj"), "w") as f:
            f.write("1000000000\n")
        with open(os.path.join(self.rapl_device_path, "energy_uj"), "w") as f:
            f.write("500000\n")

        with caplog.at_level(logging.WARNING):
            device = RAPLDevice(self.rapl_device_path)

        assert "Name file not found" in caplog.text
        assert device.name is None

    def test_init_missing_max_energy_file(self, caplog):
        """Test initialization when max energy file is missing."""
        # Create only some files
        with open(os.path.join(self.rapl_device_path, "name"), "w") as f:
            f.write("package-0\n")
        with open(os.path.join(self.rapl_device_path, "energy_uj"), "w") as f:
            f.write("500000\n")

        with caplog.at_level(logging.WARNING):
            device = RAPLDevice(self.rapl_device_path)

        assert "Max energy range file not found" in caplog.text
        assert device.max_energy_range == 0

    def test_init_missing_energy_file(self, caplog):
        """Test initialization when energy file is missing."""
        # Create only some files
        with open(os.path.join(self.rapl_device_path, "name"), "w") as f:
            f.write("package-0\n")
        with open(os.path.join(self.rapl_device_path, "max_energy_range_uj"), "w") as f:
            f.write("1000000000\n")

        with caplog.at_level(logging.WARNING):
            device = RAPLDevice(self.rapl_device_path)

        assert "Energy file not found" in caplog.text
        assert device.energy_file is None

    def test_tags_property(self):
        """Test tags property."""
        self.create_rapl_files()

        with patch(
            "wattameter.readers.rapl._get_rapl_domain_name", return_value="cpu-0"
        ):
            device = RAPLDevice(self.rapl_device_path)

        assert device.tags == ["cpu-0[uJ]"]

    def test_get_unit_valid(self):
        """Test get_unit with valid quantity."""
        self.create_rapl_files()
        device = RAPLDevice(self.rapl_device_path)

        assert device.get_unit(Energy) == "uJ"

    def test_get_unit_invalid(self, caplog):
        """Test get_unit with invalid quantity."""
        self.create_rapl_files()
        device = RAPLDevice(self.rapl_device_path)

        with caplog.at_level(logging.WARNING):
            result = device.get_unit(Temperature)

        assert result == ""
        assert "Invalid quantity requested" in caplog.text

    def test_read_energy_success(self):
        """Test successful energy reading."""
        self.create_rapl_files(energy="750000")
        device = RAPLDevice(self.rapl_device_path)

        energy = device.read_energy()
        assert energy == 750000

    def test_read_energy_file_not_open(self, caplog):
        """Test energy reading when file is not open."""
        self.create_rapl_files()
        device = RAPLDevice(self.rapl_device_path)

        # Close the file to simulate missing file
        if device.energy_file:
            device.energy_file.close()
        device.energy_file = None

        with caplog.at_level(logging.ERROR):
            energy = device.read_energy()

        assert energy == 0
        assert "Energy file is not open" in caplog.text

    def test_read_energy_invalid_content(self, caplog):
        """Test energy reading with invalid file content."""
        self.create_rapl_files(energy="invalid_number")
        device = RAPLDevice(self.rapl_device_path)

        with caplog.at_level(logging.ERROR):
            energy = device.read_energy()

        assert energy == 0
        assert "Failed to read energy" in caplog.text

    def test_read_method(self):
        """Test read method returns list."""
        self.create_rapl_files(energy="123456")
        device = RAPLDevice(self.rapl_device_path)

        result = device.read()
        assert result == [123456]

    def test_compute_energy_delta_with_overflow(self):
        """Test energy delta computation with counter overflow."""
        self.create_rapl_files()
        device = RAPLDevice(self.rapl_device_path)
        device.max_energy_range = 1000

        # Test overflow scenario: [900, 100] should become [900, 1100]
        time_series = [0, 1, 2]
        energy_series = [900, 100, 200]
        result = device.compute_derived(time_series, energy_series, Second("u"))

        # Expected: [100-900+1000, 200-100] = [200, 100]
        expected = [200, 100]
        np.testing.assert_array_equal(result, expected)

    def test_compute_energy_delta_no_overflow(self):
        """Test energy delta computation without overflow."""
        self.create_rapl_files()
        device = RAPLDevice(self.rapl_device_path)
        device.max_energy_range = 1000

        # Test normal scenario: [100, 200, 300]
        time_series = [0, 1, 2]
        energy_series = [100, 200, 300]
        result = device.compute_derived(time_series, energy_series, Second("u"))

        expected = [100, 100]
        np.testing.assert_array_equal(result, expected)

    def test_destructor_closes_file(self):
        """Test that destructor closes the energy file."""
        self.create_rapl_files()
        device = RAPLDevice(self.rapl_device_path)

        energy_file = device.energy_file
        if energy_file:
            assert not energy_file.closed

            # Manually call destructor
            device.__del__()
            assert energy_file.closed
        else:
            # If file is None, destructor should handle gracefully
            device.__del__()  # Should not raise exception


class TestRAPLReader:
    """Test cases for RAPLReader class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.rapl_dir = os.path.join(self.temp_dir, "intel-rapl", "subsystem")
        os.makedirs(self.rapl_dir)

    def teardown_method(self):
        """Clean up after each test method."""
        shutil.rmtree(self.temp_dir)

    def create_rapl_device_dir(self, device_name, name="package-0", energy="500000"):
        """Helper to create a RAPL device directory."""
        device_path = os.path.join(self.rapl_dir, device_name)
        os.makedirs(device_path)

        # Create required files
        with open(os.path.join(device_path, "name"), "w") as f:
            f.write(f"{name}\n")
        with open(os.path.join(device_path, "max_energy_range_uj"), "w") as f:
            f.write("1000000000\n")
        with open(os.path.join(device_path, "energy_uj"), "w") as f:
            f.write(f"{energy}\n")

        return device_path

    def test_init_no_devices(self):
        """Test initialization when no RAPL devices are found."""
        reader = RAPLReader(self.rapl_dir)

        assert len(reader.devices) == 0
        assert reader.tags == []

    def test_init_single_device(self):
        """Test initialization with a single RAPL device."""
        self.create_rapl_device_dir("intel-rapl:0")

        with patch(
            "wattameter.readers.rapl._get_rapl_domain_name", return_value="cpu-0"
        ):
            reader = RAPLReader(self.rapl_dir)

        assert len(reader.devices) == 1
        assert reader.tags == ["cpu-0[uJ]"]

    def test_init_multiple_devices(self):
        """Test initialization with multiple RAPL devices."""
        self.create_rapl_device_dir("intel-rapl:0", name="package-0")
        self.create_rapl_device_dir("intel-rapl:1", name="package-1")

        def mock_domain_name(path, tag_for_unnamed_device):
            if "rapl:0" in path:
                return "cpu-0"
            elif "rapl:1" in path:
                return "cpu-1"
            return tag_for_unnamed_device

        with patch(
            "wattameter.readers.rapl._get_rapl_domain_name",
            side_effect=mock_domain_name,
        ):
            reader = RAPLReader(self.rapl_dir)

        assert len(reader.devices) == 2
        assert "cpu-0[uJ]" in reader.tags
        assert "cpu-1[uJ]" in reader.tags

    def test_init_unknown_devices(self):
        """Test initialization with devices that have unknown names."""
        self.create_rapl_device_dir("intel-rapl:0")
        self.create_rapl_device_dir("intel-rapl:1")

        with patch(
            "wattameter.readers.rapl._get_rapl_domain_name", return_value="unknown"
        ):
            reader = RAPLReader(self.rapl_dir)

        assert len(reader.devices) == 2
        assert reader.tags == ["unknown-0", "unknown-1"]

    def test_tags_property(self):
        """Test tags property."""
        self.create_rapl_device_dir("intel-rapl:0")

        with patch(
            "wattameter.readers.rapl._get_rapl_domain_name", return_value="cpu-0"
        ):
            reader = RAPLReader(self.rapl_dir)

        assert reader.tags == ["cpu-0[uJ]"]

    def test_get_unit_valid(self):
        """Test get_unit with valid quantity."""
        reader = RAPLReader(self.rapl_dir)
        assert reader.get_unit(Energy) == "uJ"

    def test_get_unit_invalid(self, caplog):
        """Test get_unit with invalid quantity."""
        reader = RAPLReader(self.rapl_dir)

        with caplog.at_level(logging.WARNING):
            result = reader.get_unit(Temperature)

        assert result == ""
        assert "Invalid quantity requested" in caplog.text

    def test_read_energy_on_device_success(self):
        """Test successful energy reading from specific device."""
        self.create_rapl_device_dir("intel-rapl:0", energy="123456")

        reader = RAPLReader(self.rapl_dir)
        energy = reader.read_energy_on_device(0)

        assert energy == 123456

    def test_read_energy_on_device_index_error(self, caplog):
        """Test energy reading with invalid device index."""
        reader = RAPLReader(self.rapl_dir)

        with caplog.at_level(logging.ERROR):
            energy = reader.read_energy_on_device(0)

        assert energy == 0
        assert "Device index 0 out of range" in caplog.text

    def test_read_energy_on_device_exception(self, caplog):
        """Test energy reading when device raises exception."""
        self.create_rapl_device_dir("intel-rapl:0")
        reader = RAPLReader(self.rapl_dir)

        with patch.object(
            reader.devices[0], "read_energy", side_effect=Exception("Test error")
        ):
            with caplog.at_level(logging.ERROR):
                energy = reader.read_energy_on_device(0)

        assert energy == 0
        assert "Failed to read energy for device 0" in caplog.text

    def test_read_energy_multiple_devices(self):
        """Test reading energy from multiple devices."""
        self.create_rapl_device_dir("intel-rapl:0", energy="100000")
        self.create_rapl_device_dir("intel-rapl:1", energy="200000")

        reader = RAPLReader(self.rapl_dir)
        energies = reader.read_energy()

        assert len(energies) == 2
        assert 100000 in energies
        assert 200000 in energies

    def test_read_alias(self):
        """Test that read() is an alias for read_energy()."""
        self.create_rapl_device_dir("intel-rapl:0", energy="333333")

        reader = RAPLReader(self.rapl_dir)

        assert reader.read() == reader.read_energy()
        assert reader.read() == [333333]

    def test_compute_energy_delta_with_overflow(self):
        """Test energy delta computation with overflow for multiple devices."""
        self.create_rapl_device_dir("intel-rapl:0")
        self.create_rapl_device_dir("intel-rapl:1")

        reader = RAPLReader(self.rapl_dir)

        # Set max energy ranges
        reader.devices[0].max_energy_range = 1000
        reader.devices[1].max_energy_range = 2000

        # Test with overflow for first device
        energy_series = np.array(
            [
                [900, 1800],  # Initial values
                [100, 1900],  # First device overflows, second doesn't
                [200, 100],  # Both normal, second overflows
            ]
        )

        time_series = [0, 1, 2]
        result = reader.compute_derived(time_series, energy_series, Second("u"))

        # Expected deltas:
        # Device 0: [100-900+1000, 200-100] = [200, 100]
        # Device 1: [1900-1800, 100-1900+2000] = [100, 200]
        expected = np.array([[200, 100], [100, 200]])
        np.testing.assert_array_equal(result, expected)


class TestRAPLReaderIntegration:
    """Integration tests for RAPL reader (requires actual RAPL hardware)."""

    @pytest.mark.integration
    def test_real_rapl_initialization(self):
        """Test with real RAPL hardware (requires Intel CPU with RAPL)."""
        try:
            reader = RAPLReader()

            # Basic checks if RAPL is available
            if len(reader.devices) > 0:
                assert isinstance(reader.tags, list)
                assert len(reader.tags) == len(reader.devices)

                # Test reading from actual devices
                energies = reader.read_energy()
                assert isinstance(energies, list)
                assert len(energies) == len(reader.devices)

                # All energy values should be non-negative integers
                for energy in energies:
                    assert isinstance(energy, int)
                    assert energy >= 0

            else:
                pytest.skip("No RAPL devices found on this system")

        except Exception as e:
            pytest.skip(f"RAPL not available or accessible: {e}")


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)

    # Run tests
    pytest.main([__file__, "-v"])
