# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

import json
from unittest.mock import MagicMock, patch

from wattameter import mqtt_publisher


class FakeMQTTModule:
    MQTT_ERR_SUCCESS = 0

    def __init__(self, client):
        self._client = client

    def Client(self, client_id=None):
        self._client.client_id = client_id
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
