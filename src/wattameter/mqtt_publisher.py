# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025, Alliance for Sustainable Energy, LLC

"""MQTT Publisher for WattAMeter power usage data.

This module provides functionality to publish power measurement data to an MQTT broker.
It handles connection management, reconnection logic, and data serialization.
"""

import json
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

# MQTT client is an optional dependency
try:
    import paho.mqtt.client as mqtt  # type: ignore
    MQTT_AVAILABLE = True
except ImportError:
    mqtt = None  # type: ignore
    MQTT_AVAILABLE = False

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """Publisher for sending power usage data to an MQTT broker.
    
    This class manages the connection to an MQTT broker and provides methods
    to publish power measurement data. It handles connection failures gracefully
    and will attempt to reconnect if the connection is lost.
    
    Configuration is typically done via environment variables or passed directly:
    - MQTT_BROKER_HOST: Hostname or IP of the MQTT broker
    - MQTT_BROKER_PORT: Port number (default: 1883)
    - MQTT_USERNAME: Optional username for authentication
    - MQTT_PASSWORD: Optional password for authentication
    - MQTT_TOPIC_PREFIX: Optional prefix for all topics (default: "wattameter")
    
    :param broker_host: MQTT broker hostname or IP address
    :param broker_port: MQTT broker port (default: 1883)
    :param username: Optional username for broker authentication
    :param password: Optional password for broker authentication
    :param topic_prefix: Prefix for all MQTT topics (default: "wattameter")
    :param client_id: MQTT client identifier (default: auto-generated)
    :param qos: Quality of Service level (0, 1, or 2; default: 1)
    :param keepalive: Keepalive interval in seconds (default: 60)
    """
    
    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        topic_prefix: str = "wattameter",
        client_id: Optional[str] = None,
        qos: int = 1,
        keepalive: int = 60,
    ):
        """Initialize the MQTT publisher with connection parameters."""
        if not MQTT_AVAILABLE:
            raise ImportError(
                "paho-mqtt is not installed. Install it with: pip install paho-mqtt"
            )
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix.rstrip("/")  # Remove trailing slash
        self.qos = qos
        self.keepalive = keepalive
        
        # Generate a client ID if not provided
        if client_id is None:
            client_id = f"wattameter_{int(time.time() * 1000)}"
        
        # Create MQTT client instance
        self.client = mqtt.Client(client_id=client_id)  # type: ignore
        
        # Set authentication if provided
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Set callback functions for connection events
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # Connection state
        self._connected = False
        self._connection_attempted = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when the client connects to the broker.
        
        :param client: MQTT client instance
        :param userdata: User data (unused)
        :param flags: Response flags from the broker
        :param rc: Connection result code
        """
        if rc == 0:
            self._connected = True
            logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
        else:
            self._connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized",
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            logger.error(f"Failed to connect to MQTT broker: {error_msg}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the broker.
        
        :param client: MQTT client instance
        :param userdata: User data (unused)
        :param rc: Disconnection result code
        """
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker (code: {rc})")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for when a message is published.
        
        :param client: MQTT client instance
        :param userdata: User data (unused)
        :param mid: Message ID
        """
        logger.debug(f"Message {mid} published successfully")
    
    def connect(self, timeout: float = 10.0) -> bool:
        """Connect to the MQTT broker.
        
        Attempts to establish a connection to the configured MQTT broker.
        This method will block for up to timeout seconds waiting for the connection.
        
        :param timeout: Maximum time to wait for connection (seconds)
        :return: True if connection successful, False otherwise
        """
        if self._connected:
            logger.info("Already connected to MQTT broker")
            return True
        
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, self.keepalive)
            
            # Start the network loop in a background thread
            self.client.loop_start()
            
            # Wait for connection with timeout
            start_time = time.time()
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            self._connection_attempted = True
            
            if not self._connected:
                logger.error(f"Connection timeout after {timeout} seconds")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the MQTT broker.
        
        Cleanly disconnects from the broker and stops the network loop.
        """
        if self._connection_attempted:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                self._connected = False
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.error(f"Error disconnecting from MQTT broker: {e}")
    
    def publish_data(
        self,
        reader_name: str,
        timestamp_ns: int,
        reading_time_ns: int,
        tags: list[str],
        values: list[float],
        derived_tags: Optional[list[str]] = None,
        derived_values: Optional[list[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Publish a single data reading to MQTT.
        
        Publishes power measurement data as a JSON message to the MQTT broker.
        The message structure includes timestamp, reading time, and all measured values.
        
        Topic structure: {topic_prefix}/{reader_name}/data
        
        :param reader_name: Name of the reader (e.g., "nvmlreader", "raplreader")
        :param timestamp_ns: Reading timestamp in nanoseconds
        :param reading_time_ns: Time taken for the reading in nanoseconds
        :param tags: List of measurement tags (e.g., ["power[W]", "temp[C]"])
        :param values: List of measurement values corresponding to tags
        :param derived_tags: Optional list of derived measurement tags
        :param derived_values: Optional list of derived measurement values
        :param metadata: Optional additional metadata to include
        :return: True if publish successful, False otherwise
        """
        if not self._connected:
            logger.warning("Not connected to MQTT broker, skipping publish")
            return False
        
        # Build the message payload
        payload = {
            "timestamp_ns": timestamp_ns,
            "timestamp_iso": datetime.fromtimestamp(timestamp_ns / 1e9).isoformat(),
            "reading_time_ns": reading_time_ns,
        }
        
        # Add main measurements
        for tag, value in zip(tags, values):
            # Use the tag as the key (e.g., "power[W]")
            payload[tag] = value
        
        # Add derived measurements if provided
        if derived_tags and derived_values:
            for tag, value in zip(derived_tags, derived_values):
                payload[tag] = value
        
        # Add optional metadata
        if metadata:
            payload["metadata"] = metadata
        
        # Construct the topic
        topic = f"{self.topic_prefix}/{reader_name}/data"
        
        # Serialize to JSON
        try:
            message = json.dumps(payload)
        except (TypeError, ValueError) as e:
            logger.error(f"Error serializing data to JSON: {e}")
            return False
        
        # Publish the message
        try:
            result = self.client.publish(topic, message, qos=self.qos)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:  # type: ignore
                logger.error(f"Failed to publish message: {result.rc}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")
            return False
    
    def publish_batch(
        self,
        reader_name: str,
        time_series: list[int],
        reading_times: list[int],
        tags: list[str],
        data_series: list[list[float]],
        derived_tags: Optional[list[str]] = None,
        derived_data_series: Optional[list[list[float]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Publish a batch of readings to MQTT.
        
        Publishes multiple power measurements as individual messages.
        This is useful when flushing accumulated data from the tracker.
        
        :param reader_name: Name of the reader
        :param time_series: List of timestamps in nanoseconds
        :param reading_times: List of reading times in nanoseconds
        :param tags: List of measurement tags
        :param data_series: List of measurement value arrays
        :param derived_tags: Optional list of derived measurement tags
        :param derived_data_series: Optional list of derived measurement arrays
        :param metadata: Optional additional metadata
        :return: Number of messages successfully published
        """
        if not self._connected:
            logger.warning("Not connected to MQTT broker, skipping batch publish")
            return 0
        
        published_count = 0
        
        # Iterate through all readings
        for i, (ts, rtime, values) in enumerate(zip(time_series, reading_times, data_series)):
            # Get derived values for this reading if available
            derived_vals = None
            if derived_data_series and i < len(derived_data_series):
                derived_vals = derived_data_series[i]
            
            # Publish individual reading
            success = self.publish_data(
                reader_name=reader_name,
                timestamp_ns=ts,
                reading_time_ns=rtime,
                tags=tags,
                values=values,
                derived_tags=derived_tags,
                derived_values=derived_vals,
                metadata=metadata,
            )
            
            if success:
                published_count += 1
        
        logger.info(f"Published {published_count}/{len(time_series)} messages to MQTT")
        return published_count
    
    def __enter__(self):
        """Context manager entry - connect to broker."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit - disconnect from broker."""
        self.disconnect()
        return None
