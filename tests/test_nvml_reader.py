import pytest
import logging
from unittest.mock import Mock, patch
import pynvml

from wattameter.readers.nvml import NVMLReader, DataThroughput
from wattameter.readers.utils import Quantity, Energy, Power, Temperature, Utilization


class TestNVMLReader:
    """Test cases for NVMLReader class."""

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    def test_init_success(self, mock_get_handle, mock_get_count, mock_init):
        """Test successful initialization with one GPU."""
        # Setup mocks
        mock_get_count.return_value = 1
        mock_device = Mock()
        mock_get_handle.return_value = mock_device

        # Create reader
        reader = NVMLReader(quantities=(Power,))

        # Verify calls
        mock_init.assert_called_once()
        mock_get_count.assert_called_once()
        mock_get_handle.assert_called_once_with(0)

        # Verify state
        assert len(reader.devices) == 1
        assert reader.devices[0] == mock_device
        assert reader.quantities == (Power,)

    @patch("pynvml.nvmlInit")
    def test_init_nvml_init_failure(self, mock_init):
        """Test initialization when NVML init fails."""
        mock_init.side_effect = pynvml.NVMLError(pynvml.NVML_ERROR_UNINITIALIZED)

        reader = NVMLReader()

        # Should handle gracefully
        assert len(reader.devices) == 0
        mock_init.assert_called_once()

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    def test_init_multiple_devices(self, mock_get_handle, mock_get_count, mock_init):
        """Test initialization with multiple GPUs."""
        mock_get_count.return_value = 3
        mock_devices = [Mock(), Mock(), Mock()]
        mock_get_handle.side_effect = mock_devices

        reader = NVMLReader()

        assert len(reader.devices) == 3
        assert reader.devices == mock_devices
        assert mock_get_handle.call_count == 3

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    def test_init_device_handle_failure(
        self, mock_get_handle, mock_get_count, mock_init
    ):
        """Test initialization when getting device handle fails."""
        mock_get_count.return_value = 2
        mock_device = Mock()
        mock_get_handle.side_effect = [
            mock_device,
            pynvml.NVMLError(pynvml.NVML_ERROR_INVALID_ARGUMENT),
        ]

        reader = NVMLReader()

        # Should only have one device (the successful one)
        assert len(reader.devices) == 1
        assert reader.devices[0] == mock_device

    def test_init_invalid_quantities(self):
        """Test initialization with invalid quantities."""
        with (
            patch("pynvml.nvmlInit"),
            patch("pynvml.nvmlDeviceGetCount", return_value=0),
        ):
            with pytest.raises(ValueError, match="Unsupported quantities"):
                NVMLReader(quantities=(Quantity,))

    def test_init_valid_new_quantities(self):
        """Test initialization with new valid quantities."""
        with (
            patch("pynvml.nvmlInit"),
            patch("pynvml.nvmlDeviceGetCount", return_value=0),
            patch("pynvml.nvmlDeviceGetHandleByIndex"),
        ):
            # Should not raise an exception
            reader = NVMLReader(quantities=(Utilization, DataThroughput))
            assert reader.quantities == (Utilization, DataThroughput)

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    def test_tags_property(self, mock_get_count, mock_init):
        """Test tags property generation."""
        mock_get_count.return_value = 2

        with patch("pynvml.nvmlDeviceGetHandleByIndex"):
            reader = NVMLReader(quantities=(Power, Energy))

        expected_tags = ["gpu-0[mW]", "gpu-1[mW]", "gpu-0[mJ]", "gpu-1[mJ]"]
        assert reader.tags == expected_tags

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    def test_tags_property_utilization(self, mock_get_count, mock_init):
        """Test tags property with utilization quantities."""
        mock_get_count.return_value = 1

        with patch("pynvml.nvmlDeviceGetHandleByIndex"):
            reader = NVMLReader(quantities=(Utilization,))

        expected_tags = ["gpu-0[%gpu]", "gpu-0[%mem]"]
        assert reader.tags == expected_tags

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    def test_tags_property_data_throughput(self, mock_get_count, mock_init):
        """Test tags property with data throughput quantities."""
        mock_get_count.return_value = 1

        with patch("pynvml.nvmlDeviceGetHandleByIndex"):
            reader = NVMLReader(quantities=(DataThroughput,))

        expected_tags = ["gpu-0[TX KiB]", "gpu-0[RX KiB]"]
        assert reader.tags == expected_tags

    def test_get_unit(self):
        """Test get_unit method."""
        with (
            patch("pynvml.nvmlInit"),
            patch("pynvml.nvmlDeviceGetCount", return_value=0),
        ):
            reader = NVMLReader()

        # Now returns Unit objects, not strings
        assert str(reader.get_unit(Power)) == "mW"
        assert str(reader.get_unit(Energy)) == "mJ"
        assert str(reader.get_unit(Temperature)) == "C"
        assert str(reader.get_unit(DataThroughput)) == "KiB"
        assert str(reader.get_unit(Quantity)) == ""

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    @patch("time.perf_counter_ns")
    @patch("pynvml.nvmlDeviceGetTotalEnergyConsumption")
    def test_read_energy_on_device_success(
        self, mock_energy, mock_time, mock_get_handle, mock_get_count, mock_init
    ):
        """Test successful energy reading."""
        # Setup
        mock_get_count.return_value = 1
        mock_device = Mock()
        mock_get_handle.return_value = mock_device
        mock_energy.return_value = 1000000  # 1M mJ
        mock_time.side_effect = [0, 1000000]  # 1ms elapsed

        reader = NVMLReader()
        result = reader.read_energy_on_device(0)

        assert result == 1000000
        mock_energy.assert_called_once_with(mock_device)

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    @patch("pynvml.nvmlDeviceGetTotalEnergyConsumption")
    def test_read_energy_on_device_nvml_error(
        self, mock_energy, mock_get_handle, mock_get_count, mock_init
    ):
        """Test energy reading with NVML error."""
        mock_get_count.return_value = 1
        mock_get_handle.return_value = Mock()
        mock_energy.side_effect = pynvml.NVMLError(pynvml.NVML_ERROR_NOT_SUPPORTED)

        reader = NVMLReader()
        result = reader.read_energy_on_device(0)

        assert result == 0

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    def test_read_energy_on_device_index_error(self, mock_get_count, mock_init):
        """Test energy reading with invalid device index."""
        mock_get_count.return_value = 1

        with patch("pynvml.nvmlDeviceGetHandleByIndex"):
            reader = NVMLReader()

        result = reader.read_energy_on_device(5)  # Invalid index
        assert result == 0

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    @patch("pynvml.nvmlDeviceGetTemperature")
    def test_read_temperature_on_device_success(
        self, mock_temp, mock_get_handle, mock_get_count, mock_init
    ):
        """Test successful temperature reading."""
        mock_get_count.return_value = 1
        mock_device = Mock()
        mock_get_handle.return_value = mock_device
        mock_temp.return_value = 65  # 65°C

        reader = NVMLReader()
        result = reader.read_temperature_on_device(0)

        assert result == 65
        mock_temp.assert_called_once_with(mock_device, pynvml.NVML_TEMPERATURE_GPU)

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    @patch("pynvml.nvmlDeviceGetPowerUsage")
    def test_read_power_on_device_success(
        self, mock_power, mock_get_handle, mock_get_count, mock_init
    ):
        """Test successful power reading."""
        mock_get_count.return_value = 1
        mock_device = Mock()
        mock_get_handle.return_value = mock_device
        mock_power.return_value = 250000

        reader = NVMLReader()
        result = reader.read_power_on_device(0)

        assert result == 250000
        mock_power.assert_called_once_with(mock_device)

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    @patch("pynvml.nvmlDeviceGetUtilizationRates")
    def test_read_utilization_on_device_success(
        self, mock_util, mock_get_handle, mock_get_count, mock_init
    ):
        """Test successful utilization reading."""
        mock_get_count.return_value = 1
        mock_device = Mock()
        mock_get_handle.return_value = mock_device

        # Mock utilization object
        mock_utilization = Mock()
        mock_utilization.gpu = 75
        mock_utilization.memory = 60
        mock_util.return_value = mock_utilization

        reader = NVMLReader()
        result = reader.read_utilization_on_device(0)

        assert result == (75, 60)
        mock_util.assert_called_once_with(mock_device)

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    @patch("pynvml.nvmlDeviceGetFieldValues")
    def test_read_nvlink_throughput_on_device_success(
        self, mock_field_values, mock_get_handle, mock_get_count, mock_init
    ):
        """Test successful NVLink throughput reading."""
        mock_get_count.return_value = 1
        mock_device = Mock()
        mock_get_handle.return_value = mock_device

        # Mock field values
        mock_tx = Mock()
        mock_tx.value.ullVal = 1024
        mock_rx = Mock()
        mock_rx.value.ullVal = 2048
        mock_field_values.return_value = [mock_tx, mock_rx]

        reader = NVMLReader()
        result = reader.read_nvlink_throughput_on_device(0)

        assert result == (1024, 2048)
        mock_field_values.assert_called_once_with(
            mock_device,
            [
                pynvml.NVML_FI_DEV_NVLINK_THROUGHPUT_DATA_TX,
                pynvml.NVML_FI_DEV_NVLINK_THROUGHPUT_DATA_RX,
            ],
        )

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    def test_read_energy_multiple_devices(
        self, mock_get_handle, mock_get_count, mock_init
    ):
        """Test reading energy from multiple devices."""
        mock_get_count.return_value = 2
        mock_devices = [Mock(), Mock()]
        mock_get_handle.side_effect = mock_devices

        reader = NVMLReader(quantities=(Energy,))

        with patch.object(reader, "read_energy_on_device", side_effect=[1000, 2000]):
            result = reader.read_energy()

        assert result == [1000, 2000]

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    def test_read_mixed_quantities(self, mock_get_handle, mock_get_count, mock_init):
        """Test reading mixed quantities."""
        mock_get_count.return_value = 1
        mock_get_handle.return_value = Mock()

        reader = NVMLReader(quantities=(Power, Energy, Temperature))

        with (
            patch.object(reader, "read_power_on_device", return_value=250),
            patch.object(reader, "read_energy_on_device", return_value=1000),
            patch.object(reader, "read_temperature_on_device", return_value=65),
        ):
            result = reader.read()

        assert result == [250, 1000, 65]

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    def test_read_utilization_quantities(
        self, mock_get_handle, mock_get_count, mock_init
    ):
        """Test reading utilization quantities."""
        mock_get_count.return_value = 1
        mock_get_handle.return_value = Mock()

        reader = NVMLReader(quantities=(Utilization,))

        with patch.object(reader, "read_utilization_on_device", return_value=(75, 60)):
            result = reader.read()

        # Should return GPU utilization first, then memory utilization
        assert result == [75, 60]

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    @patch("pynvml.nvmlDeviceGetHandleByIndex")
    def test_read_data_throughput_quantities(
        self, mock_get_handle, mock_get_count, mock_init
    ):
        """Test reading data throughput quantities."""
        mock_get_count.return_value = 1
        mock_get_handle.return_value = Mock()

        reader = NVMLReader(quantities=(DataThroughput,))

        with patch.object(
            reader, "read_nvlink_throughput_on_device", return_value=(1024, 2048)
        ):
            result = reader.read()

        # Should return TX throughput first, then RX throughput
        assert result == [1024, 2048]

    @patch("pynvml.nvmlInit")
    @patch("pynvml.nvmlDeviceGetCount")
    def test_read_no_devices(self, mock_get_count, mock_init):
        """Test reading when no devices are available."""
        mock_get_count.return_value = 0

        reader = NVMLReader()
        result = reader.read()

        assert result == []

    def test_logging_configuration(self, caplog):
        """Test that logging works correctly."""
        with (
            patch("pynvml.nvmlInit"),
            patch("pynvml.nvmlDeviceGetCount", return_value=1),
            patch("pynvml.nvmlDeviceGetHandleByIndex"),
        ):
            with caplog.at_level(logging.INFO):
                _ = NVMLReader()

            assert "NVML initialized successfully" in caplog.text
            assert "Handle for device 0 initialized successfully" in caplog.text

    def test_logging_nvml_error(self, caplog):
        """Test logging when NVML initialization fails."""
        with patch(
            "pynvml.nvmlInit",
            side_effect=pynvml.NVMLError(pynvml.NVML_ERROR_UNINITIALIZED),
        ):
            with caplog.at_level(logging.WARNING):
                _ = NVMLReader()

            assert "Failed to initialize NVML" in caplog.text


# Integration test (requires actual NVIDIA GPU)
@pytest.mark.integration
class TestNVMLReaderIntegration:
    """Integration tests that require actual NVIDIA hardware."""

    def test_real_nvml_initialization(self):
        """Test with real NVML (requires NVIDIA GPU)."""
        try:
            reader = NVMLReader()
            if len(reader.devices) > 0:
                # Test reading from actual device
                energy = reader.read_energy_on_device(0)
                assert isinstance(energy, int)
                assert energy >= 0
        except Exception as e:
            pytest.skip(f"No NVIDIA GPU available or NVML not working: {e}")


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(level=logging.DEBUG)

    # Run tests
    pytest.main([__file__, "-v"])
