#!/usr/bin/env python3
"""
Example: Using WattAMeter with MQTT Publishing

This script demonstrates how to use WattAMeter to track GPU power consumption
and publish the data to an MQTT broker in real-time.

Requirements:
    pip install wattameter[mqtt]

Usage:
    # With environment variables for credentials
    export MQTT_BROKER="mqtt.example.com"
    export MQTT_USERNAME="myuser"
    export MQTT_PASSWORD="mypassword"
    python mqtt_example.py

    # Or with direct configuration (see script)
"""

import os
import time
from wattameter import Tracker, TrackerArray
from wattameter.readers import RAPLReader, NVMLReader, Power

# Configure MQTT connection
# Option 1: Use environment variables (recommended for security)
mqtt_config = {
    "broker_host": os.getenv("MQTT_BROKER", "localhost"),
    "broker_port": int(os.getenv("MQTT_PORT", "1883")),
    # "username": os.getenv("MQTT_USERNAME"),
    # "password": os.getenv("MQTT_PASSWORD"),
    "topic_prefix": os.getenv("MQTT_TOPIC_PREFIX", "wattameter"),
    "qos": int(os.getenv("MQTT_QOS", "1")),
}

# Option 2: Direct configuration (not recommended for production)
# mqtt_config = {
#     "broker_host": "mqtt.example.com",
#     "broker_port": 1883,
#     "username": "myuser",
#     "password": "mypassword",
#     "topic_prefix": "hpc/wattameter",
#     "qos": 1,
# }


def main():
    """Run power tracking with MQTT publishing."""
    
    # Check if MQTT broker is configured
    if not mqtt_config["broker_host"]:
        print("Warning: MQTT_BROKER not set. Using localhost.")
        print("Set environment variable MQTT_BROKER or edit this script.")
    
    print(f"Configuring WattAMeter with MQTT broker: {mqtt_config['broker_host']}:{mqtt_config['broker_port']}")
    print(f"Topic prefix: {mqtt_config['topic_prefix']}")
    print()
    
    try:
        # Create tracker with MQTT publishing enabled
        # This will:
        # 1. Read GPU power every 0.1 seconds
        # 2. Write to local file every 20 reads (2 seconds)
        # 3. Publish each batch to MQTT when writing to file
        tracker = Tracker(
            reader=NVMLReader((Power,)),
            dt_read=0.1,  # Read power every 0.1 seconds
            freq_write=20,  # Write/publish every 20 reads (2 seconds)
            output="power_mqtt_example.log",
            mqtt_config=mqtt_config,
        )
        # readers = [NVMLReader((Power,)), RAPLReader()]
        # tracker = TrackerArray(
        #     readers=readers,
        #     dt_read=0.1,
        #     freq_write=600,
        #     mqtt_config=mqtt_config,
        # )
        
        print("Starting power tracking...")
        print("Data will be published to MQTT topic:")
        print(f"  {mqtt_config['topic_prefix']}/nvmlreader/data")
        print()
        print("Press Ctrl+C to stop")
        print()
        
        # Start tracking in context manager
        with tracker:
            # Simulate some work
            # In a real scenario, this would be your actual computation
            duration = 10  # Run for 10 seconds
            
            print(f"Tracking power for {duration} seconds...")
            for i in range(duration):
                time.sleep(1)
                if (i + 1) % 60 == 0:
                    print(f"  ... {i + 1} seconds elapsed")
        
        print("\nTracking complete!")
        print(f"Data written to: power_mqtt_example.log")
        print(f"Data published to MQTT: {mqtt_config['topic_prefix']}/nvmlreader/data")
        
    except KeyboardInterrupt:
        print("\n\nTracking interrupted by user")
        print("Final data has been written and published")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nCommon issues:")
        print("  - MQTT broker not reachable")
        print("  - Invalid credentials")
        print("  - paho-mqtt not installed (pip install paho-mqtt)")
        print("  - No NVIDIA GPU available")
        raise


def test_mqtt_subscriber():
    """
    Example MQTT subscriber to verify messages are being received.
    
    Run this in a separate terminal to see the published messages.
    Requires: pip install paho-mqtt
    """
    import paho.mqtt.client as mqtt
    import json
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker")
            # Subscribe to all wattameter topics
            topic = f"{mqtt_config['topic_prefix']}/+/data"
            client.subscribe(topic)
            print(f"Subscribed to: {topic}")
        else:
            print(f"Connection failed with code {rc}")
    
    def on_message(client, userdata, msg):
        try:
            # data = json.loads(msg.payload)
            # timestamp = data.get("timestamp[iso]", "unknown")
            # power = data.get("gpu-0[mW]", "N/A")
            # reading_time = data.get("reading-time[ns]", 0) / 1e6  # Convert to ms
            
            # print(f"[{timestamp}] GPU 0 Power: {power} mW (reading took {reading_time:.2f} ms)")
            print(msg.payload)
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
    
    # Create MQTT client and connect
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Use credentials if provided
    if mqtt_config.get("username") and mqtt_config.get("password"):
        client.username_pw_set(mqtt_config["username"], mqtt_config["password"])
    
    try:
        client.connect(mqtt_config["broker_host"], mqtt_config["broker_port"], 60)
        print("Starting MQTT subscriber...")
        print("Waiting for messages... (Press Ctrl+C to stop)")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nSubscriber stopped")
        client.disconnect()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    # Check if user wants to run subscriber mode
    if len(sys.argv) > 1 and sys.argv[1] == "subscribe":
        print("Running in subscriber mode to receive MQTT messages")
        print()
        test_mqtt_subscriber()
    else:
        # Run the main tracking example
        main()
        print()
        print("Tip: Run 'python mqtt_example.py subscribe' in another terminal")
        print("     to see the MQTT messages being published in real-time")
