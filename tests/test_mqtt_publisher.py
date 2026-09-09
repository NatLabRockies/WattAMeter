# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Energy Innovation, LLC

import json
import socket
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, call, patch

import pytest

from wattameter import mqtt_publisher


class FakeCallbackAPIVersion:
    VERSION1 = 1
    VERSION2 = 2


class FakeMQTTModule:
    MQTT_ERR_SUCCESS = 0
    CallbackAPIVersion = FakeCallbackAPIVersion

    def __init__(self, client):
        self._client = client

    def Client(self, client_id=None, callback_api_version=None):
        self._client.client_id = client_id
        self._client.callback_api_version = callback_api_version
        return self._client


def test_publish_data_payload_includes_node_and_run_id():
    fake_client = MagicMock()
    fake_client.publish.return_value = MagicMock(rc=0)

    with patch.object(mqtt_publisher, "MQTT_AVAILABLE", True), patch.object(
        mqtt_publisher, "mqtt", FakeMQTTModule(fake_client)
    ), patch.object(mqtt_publisher, "get_node_name", return_value="node-a"):
        pub = mqtt_publisher.MQTTPublisher(
            broker_host="broker.local",
            topic_prefix="wattameter",
            run_id="run-42",
            qos=1,
        )
        pub._connected = True

        ok = pub.publish_data(
            reader_name="raplreader",
            timestamp_ns=1_000_000_000,
            reading_time_ns=12345,
            tags=["package-0[mJ]"],
            values=[10.5],
        )

    assert ok is True
    fake_client.publish.assert_called_once()

    topic = fake_client.publish.call_args.args[0]
    payload_json = fake_client.publish.call_args.args[1]
    qos = fake_client.publish.call_args.kwargs["qos"]

    assert topic == "wattameter/raplreader/data"
    assert qos == 1

    payload = json.loads(payload_json)
    assert payload["timestamp[ns]"] == 1_000_000_000
    assert payload["reading-time[ns]"] == 12345
    assert payload["node"] == "node-a"
    assert payload["run-id"] == "run-42"
    assert payload["package-0[mJ]"] == 10.5


def test_publish_data_returns_false_when_disconnected():
    fake_client = MagicMock()

    with patch.object(mqtt_publisher, "MQTT_AVAILABLE", True), patch.object(
        mqtt_publisher, "mqtt", FakeMQTTModule(fake_client)
    ):
        pub = mqtt_publisher.MQTTPublisher(broker_host="broker.local")

    pub._connected = False
    ok = pub.publish_data(
        reader_name="nvmlreader",
        timestamp_ns=1,
        reading_time_ns=2,
        tags=["gpu-0[mW]"],
        values=[250.0],
    )

    assert ok is False
    fake_client.publish.assert_not_called()


def test_publish_batch_counts_successful_messages():
    fake_client = MagicMock()

    with patch.object(mqtt_publisher, "MQTT_AVAILABLE", True), patch.object(
        mqtt_publisher, "mqtt", FakeMQTTModule(fake_client)
    ):
        pub = mqtt_publisher.MQTTPublisher(broker_host="broker.local")

    pub._connected = True
    with patch.object(pub, "publish_data", side_effect=[True, False, True]):
        count = pub.publish_batch(
            reader_name="nvmlreader",
            time_series=[1, 2, 3],
            reading_times=[11, 12, 13],
            tags=["gpu-0[mW]"],
            data_series=[[10.0], [20.0], [30.0]],
        )

    assert count == 2


def test_client_created_with_v2_callback_api():
    """Regression test for issue #15: paho-mqtt v2 callback API is used."""
    fake_client = MagicMock()

    with patch.object(mqtt_publisher, "MQTT_AVAILABLE", True), patch.object(
        mqtt_publisher, "mqtt", FakeMQTTModule(fake_client)
    ):
        pub = mqtt_publisher.MQTTPublisher(broker_host="broker.local")

    # The client must be constructed requesting the v2 callback API version.
    assert fake_client.callback_api_version == FakeCallbackAPIVersion.VERSION2
    assert pub.client is fake_client


def test_on_connect_uses_v2_signature():
    """Regression test for issue #15: _on_connect accepts the 5-arg v2 signature."""
    fake_client = MagicMock()

    with patch.object(mqtt_publisher, "MQTT_AVAILABLE", True), patch.object(
        mqtt_publisher, "mqtt", FakeMQTTModule(fake_client)
    ):
        pub = mqtt_publisher.MQTTPublisher(broker_host="broker.local")

    class ReasonCode:
        def __init__(self, value):
            self.value = value

        @property
        def is_failure(self):
            return self.value != 0

    # Success reason code marks the publisher connected.
    pub._on_connect(fake_client, None, {}, ReasonCode(0), properties=None)
    assert pub._connected is True

    # Failure reason code clears the connected flag.
    pub._on_connect(fake_client, None, {}, ReasonCode(5), properties=None)
    assert pub._connected is False


def test_on_disconnect_uses_v2_signature():
    """Regression test for issue #15: _on_disconnect accepts the v2 signature."""
    fake_client = MagicMock()

    with patch.object(mqtt_publisher, "MQTT_AVAILABLE", True), patch.object(
        mqtt_publisher, "mqtt", FakeMQTTModule(fake_client)
    ):
        pub = mqtt_publisher.MQTTPublisher(broker_host="broker.local")

    pub._connected = True
    pub._on_disconnect(fake_client, None, {}, 0, properties=None)
    assert pub._connected is False


@pytest.fixture
def publisher(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(mqtt_publisher, "MQTT_AVAILABLE", True)
    monkeypatch.setattr(mqtt_publisher, "mqtt", FakeMQTTModule(client))
    pub = mqtt_publisher.MQTTPublisher(broker_host="broker.local")
    client.connect.side_effect = lambda *args: pub._on_connect(client, None, {}, 0)
    return pub


def test_disconnect_order_and_idempotence(publisher):
    publisher.disconnect()
    publisher.client.disconnect.assert_not_called()
    assert publisher.connect()
    publisher.client.reset_mock()
    publisher.disconnect()
    publisher.disconnect()
    assert publisher.client.mock_calls == [call.disconnect(), call.loop_stop()]
    assert not publisher._connected
    assert not publisher._connection_attempted


def test_disconnect_exception_still_stops_loop(publisher, caplog):
    assert publisher.connect()
    publisher.client.disconnect.side_effect = RuntimeError("disconnect failed")
    publisher.disconnect()
    assert publisher.client.mock_calls[-2:] == [call.disconnect(), call.loop_stop()]
    assert not publisher._connected
    assert not publisher._connection_attempted
    assert "disconnect failed" in caplog.text


@pytest.mark.parametrize("failure", ["connect", "timeout", "interrupt"])
def test_failed_connect_cleanup_and_reconnect(publisher, monkeypatch, failure):
    publisher.client.connect.side_effect = OSError("unavailable") if failure == "connect" else None
    monkeypatch.setattr(mqtt_publisher, "time", MagicMock(monotonic=MagicMock(side_effect=[0, 1])))
    if failure == "interrupt":
        publisher.client.loop_start.side_effect = KeyboardInterrupt
        with pytest.raises(KeyboardInterrupt):
            publisher.connect()
    else:
        assert not publisher.connect(timeout=0.5)
    assert publisher.client.mock_calls[-2:] == [call.disconnect(), call.loop_stop()]
    assert not publisher._connected
    assert not publisher._connection_attempted
    publisher.client.loop_start.side_effect = None
    publisher.client.connect.side_effect = lambda *args: publisher._on_connect(None, None, {}, 0)
    mqtt_publisher.time.monotonic.side_effect = None
    assert publisher.connect()
    publisher.disconnect()
    assert publisher.client.loop_stop.call_count == 2


def test_real_paho_callback_lifecycle(monkeypatch):
    mqtt = pytest.importorskip("paho.mqtt.client")
    monkeypatch.setattr(mqtt_publisher, "mqtt", mqtt)
    monkeypatch.setattr(mqtt_publisher, "MQTT_AVAILABLE", True)
    pub = mqtt_publisher.MQTTPublisher("broker.local", qos=0)
    for name in ("on_connect", "on_publish", "on_disconnect"):
        setattr(pub.client, name, MagicMock(wraps=getattr(pub.client, name)))
    transport, peer = socket.socketpair()
    with transport, peer, ThreadPoolExecutor(max_workers=1) as executor:
        peer.settimeout(2)

        def broker():
            with peer.makefile("rb") as stream:
                for expected in (0x10, 0x30, 0xE0):
                    assert stream.read(1) == bytes([expected])
                    length, shift = 0, 0
                    while True:
                        byte = stream.read(1)[0]
                        length += (byte & 127) << shift
                        if byte < 128:
                            break
                        shift += 7
                    assert len(stream.read(length)) == length
                    if expected == 0x10:
                        peer.sendall(b"\x20\x02\x00\x00")

        result = executor.submit(broker)
        try:
            with patch("socket.create_connection", return_value=transport):
                assert pub.connect(timeout=1)
            assert pub.publish_data("reader", 1, 2, [], [])
            pub.disconnect()
            result.result(timeout=2)
            for name in ("on_connect", "on_publish", "on_disconnect"):
                getattr(pub.client, name).assert_called_once()
            assert not pub._connected
            assert not pub._connection_attempted
        finally:
            pub.disconnect()
