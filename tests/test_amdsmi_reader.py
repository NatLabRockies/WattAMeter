import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

import wattameter.readers as readers
from wattameter.readers import Power, Utilization


@pytest.fixture
def amd_reader(monkeypatch):
    amdsmi = ModuleType("amdsmi")
    amdsmi.AmdSmiException = type("AmdSmiException", (Exception,), {})
    amdsmi.amdsmi_init = Mock(return_value=0)
    amdsmi.amdsmi_shut_down = Mock()
    amdsmi.amdsmi_get_processor_handles = Mock(return_value=["gpu-0"])
    amdsmi.amdsmi_get_power_info = Mock()
    amdsmi.amdsmi_get_gpu_activity = Mock()
    monkeypatch.setitem(sys.modules, "amdsmi", amdsmi)

    # Load the real reader without leaving a fake AMD backend in package imports.
    spec = importlib.util.spec_from_file_location(
        "wattameter.readers._amdsmi_test",
        Path(readers.__file__).with_name("amdsmi.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AMDSMIReader, amdsmi


@pytest.mark.parametrize(
    "average,current,expected",
    [(250, 275, 250), ("N/A", 275, 275), ("N/A", "N/A", 0), (0, 275, 0)],
)
def test_power_readings(amd_reader, average, current, expected, caplog):
    reader_class, amdsmi = amd_reader
    amdsmi.amdsmi_get_power_info.return_value = {
        "average_socket_power": average,
        "current_socket_power": current,
    }
    reader = reader_class(quantities=(Power,))

    assert reader.tags == ["gpu-0[W]"]
    assert reader.read() == [expected]
    amdsmi.amdsmi_get_power_info.assert_called_once_with("gpu-0")
    if average == current == "N/A":
        assert "Power unavailable for device 0" in caplog.text


def test_utilization_percentages_match_tags(amd_reader):
    reader_class, amdsmi = amd_reader
    amdsmi.amdsmi_get_processor_handles.return_value = ["gpu-0", "gpu-1"]
    amdsmi.amdsmi_get_gpu_activity.side_effect = [
        {"gfx_activity": 75, "umc_activity": 20},
        {"gfx_activity": 50, "umc_activity": 10},
    ]
    reader = reader_class(quantities=(Utilization,))

    assert reader.tags == ["gpu-0[%gpu]", "gpu-1[%gpu]", "gpu-0[%mem]", "gpu-1[%mem]"]
    assert reader.read() == [75, 50, 20, 10]
    assert [call.args for call in amdsmi.amdsmi_get_gpu_activity.call_args_list] == [
        ("gpu-0",), ("gpu-1",)
    ]


def test_api_errors_keep_zero_fallback(amd_reader):
    reader_class, amdsmi = amd_reader
    amdsmi.amdsmi_get_power_info.side_effect = amdsmi.AmdSmiException("unavailable")
    amdsmi.amdsmi_get_gpu_activity.side_effect = amdsmi.AmdSmiException("unavailable")
    reader = reader_class(quantities=(Power, Utilization))

    assert reader.read() == [0, 0, 0]
