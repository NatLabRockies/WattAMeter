# MQTT Publishing in WattAMeter

WattAMeter can publish power measurement data to an MQTT broker in real-time, enabling integration with monitoring systems, dashboards, and other applications.

## Installation

To use MQTT publishing, install WattAMeter with the MQTT extra:

```bash
pip install wattameter[mqtt]
# or
pip install paho-mqtt
```

## Overview

When MQTT publishing is enabled, WattAMeter will:
- Connect to the specified MQTT broker on startup
- Publish each batch of power measurements as JSON messages
- Continue writing to local files as usual (dual output)
- Handle connection failures gracefully and log errors

## Configuration

### Command-Line Interface

MQTT publishing is configured via command-line arguments:

```bash
wattameter \
  --tracker 0.1,nvml-power,rapl \
  --mqtt-broker mqtt.example.com \
  --mqtt-port 1883 \
  --mqtt-username myuser \
  --mqtt-password mypassword \
  --mqtt-topic-prefix "hpc/wattameter" \
  --mqtt-qos 1
```

#### MQTT Options

| Option | Default | Description |
|--------|---------|-------------|
| `--mqtt-broker` | None | MQTT broker hostname or IP. Required to enable MQTT publishing. |
| `--mqtt-port` | 1883 | MQTT broker port |
| `--mqtt-username` | None | Username for authentication (optional) |
| `--mqtt-password` | None | Password for authentication (optional) |
| `--mqtt-topic-prefix` | "wattameter" | Topic prefix for all messages |
| `--mqtt-qos` | 1 | Quality of Service: 0 (at most once), 1 (at least once), 2 (exactly once) |

If `--mqtt-broker` is not specified, MQTT publishing is disabled and WattAMeter operates normally.

### Python API

You can enable MQTT publishing when using WattAMeter as a library:

```python
from wattameter import Tracker
from wattameter.readers import NVMLReader, Power

# Configure MQTT publishing
mqtt_config = {
    "broker_host": "mqtt.example.com",
    "broker_port": 1883,
    "username": "myuser",
    "password": "mypassword",
    "topic_prefix": "hpc/wattameter",
    "qos": 1,
}

# Create tracker with MQTT enabled
tracker = Tracker(
    reader=NVMLReader((Power,)),
    dt_read=0.1,
    freq_write=600,
    output="power_log.txt",
    mqtt_config=mqtt_config,
)

with tracker:
    # Your code here
    pass
```

### Environment Variables

For security, you can use environment variables for credentials:

```bash
export MQTT_BROKER="mqtt.example.com"
export MQTT_USERNAME="myuser"
export MQTT_PASSWORD="mypassword"

# Then use in your script
import os

mqtt_config = {
    "broker_host": os.getenv("MQTT_BROKER"),
    "username": os.getenv("MQTT_USERNAME"),
    "password": os.getenv("MQTT_PASSWORD"),
}
```

## MQTT Message Format

### Topic Structure

Messages are published to topics with this structure:

```
{topic_prefix}/{reader_name}/data
```

Examples:
- `wattameter/nvmlreader/data`
- `wattameter/raplreader/data`
- `hpc/wattameter/nvmlreader/data` (with custom prefix)

### Message Payload

Each message is a JSON object containing:

```json
{
  "timestamp[ns]": 1703347200000000000,
  "timestamp[iso]": "2023-12-23T12:00:00.000000",
  "reading-time[ns]": 1234567,
  "gpu-0[mW]": 300000.5,
  "metadata": {
    "experiment_id": "job-12345"
  }
}
```

Fields:
- `timestamp[ns]`: Measurement timestamp in nanoseconds (Unix epoch)
- `timestamp[iso]`: Human-readable ISO 8601 timestamp
- `reading-time[ns]`: Time taken to perform the measurement in nanoseconds
- Dynamic fields for each measured quantity (e.g., `gpu-0[mW]`, `cpu-0[W]`)
- `metadata`: Optional additional information (currently unused, available for future extensions)

## Use Cases

### Real-Time Monitoring Dashboard

Subscribe to the MQTT topic to display live power consumption:

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    print(f"GPU 0 Power: {data.get('gpu-0[mW]', 'N/A')} W at {data['timestamp[iso]']}")

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt.example.com", 1883)
client.subscribe("wattameter/+/data")
client.loop_forever()
```

### Time-Series Database Integration

Forward MQTT messages to InfluxDB, Prometheus, or other time-series databases for long-term storage and analysis.

### HPC Job Accounting

Correlate power measurements with job IDs and compute energy costs:

```bash
# Run WattAMeter for a specific job
wattameter \
  --tracker 0.1,nvml-power \
  --mqtt-broker mqtt.hpc.local \
  --mqtt-topic-prefix "hpc/jobs/$SLURM_JOB_ID" \
  --id $SLURM_JOB_ID
```

### Alert Systems

Set up alerts for abnormal power consumption:

```python
import paho.mqtt.client as mqtt
import json

POWER_THRESHOLD = 900000  # mW

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    power = data.get('gpu-0[mW]', 0)
    if power > POWER_THRESHOLD:
        send_alert(f"High power consumption: {power}W")

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt.example.com", 1883)
client.subscribe("wattameter/nvmlreader/data")
client.loop_forever()
```

## Connection Behavior

### Connection Management

- WattAMeter attempts to connect to the MQTT broker on startup
- If connection fails, an error is logged but WattAMeter continues running
- Data continues to be written to local files even if MQTT is unavailable
- Connection is maintained throughout the tracking session

### Error Handling

- If MQTT publishing fails for individual messages, errors are logged
- Failed MQTT publishes do not affect file writing
- WattAMeter is designed to be resilient: MQTT is an optional enhancement, not a requirement

### Disconnection

- Clean disconnection occurs when WattAMeter stops
- Final data batch is written to both file and MQTT before shutdown

## Security Considerations

### Authentication

Always use username/password authentication when connecting to production MQTT brokers:

```bash
wattameter \
  --mqtt-broker mqtt.example.com \
  --mqtt-username myuser \
  --mqtt-password mypassword
```

### TLS/SSL

The current implementation uses unencrypted connections. For production deployments with sensitive data:

1. Use environment variables for credentials (never hardcode passwords)
2. Configure your MQTT broker with TLS/SSL
3. Restrict MQTT broker access via firewall rules
4. Use MQTT ACLs to limit topic permissions

### Network Isolation

In HPC environments:
- Deploy MQTT broker on a management network
- Restrict access to compute nodes only
- Use VLANs or network segmentation for isolation

## Troubleshooting

### MQTT Module Not Available

Error: `paho-mqtt is not installed`

Solution:
```bash
pip install paho-mqtt
# or
pip install wattameter[mqtt]
```

### Connection Timeout

Error: `Connection timeout after 10 seconds`

Possible causes:
- MQTT broker is not running or unreachable
- Firewall blocking connection
- Incorrect hostname or port

Solutions:
1. Verify broker is running: `telnet mqtt.example.com 1883`
2. Check firewall rules
3. Verify hostname resolves: `ping mqtt.example.com`

### Authentication Failed

Error: `Connection refused - bad username or password`

Solutions:
1. Verify credentials are correct
2. Check MQTT broker user configuration
3. Ensure username/password are properly URL-encoded if they contain special characters

### Messages Not Appearing

If WattAMeter connects but you don't see messages:

1. Verify topic subscription matches published topics
2. Check QoS levels are compatible
3. Enable debug logging: `--log-level debug`
4. Monitor MQTT broker logs

### Performance Impact

MQTT publishing adds minimal overhead:
- Network latency for each publish (typically <10ms on local network)
- JSON serialization overhead (negligible for small messages)
- No impact on measurement accuracy or timing

If performance is critical:
- Increase `--freq-write` to batch more measurements before publishing
- Use QoS 0 for lowest latency (with potential message loss)
- Deploy MQTT broker on local network to minimize latency

## Examples

### Basic Usage with MQTT

```bash
# Publish NVML power data every 0.1 seconds to local MQTT broker
wattameter \
  --tracker 0.1,nvml-power \
  --mqtt-broker localhost \
  --freq-write 600
```

### Multi-Reader with MQTT

```bash
# Track both GPU and CPU power at different intervals
wattameter \
  --tracker 0.1,nvml-power,nvml-temp \
  --tracker 1.0,rapl \
  --mqtt-broker mqtt.hpc.local \
  --mqtt-port 1883 \
  --mqtt-topic-prefix "hpc/node01"
```

### Python API with MQTT

```python
from wattameter import Tracker, TrackerArray
from wattameter.readers import NVMLReader, RAPLReader, Power

# Configure MQTT
mqtt_config = {
    "broker_host": "mqtt.example.com",
    "broker_port": 1883,
    "topic_prefix": "hpc/experiment",
    "qos": 1,
}

# Track multiple readers with MQTT
readers = [NVMLReader((Power,)), RAPLReader()]
tracker_array = TrackerArray(
    readers=readers,
    dt_read=0.1,
    freq_write=600,
    mqtt_config=mqtt_config,
)

with tracker_array:
    # Your code here
    import time
    time.sleep(60)

print("Power tracking complete. Check MQTT topics for data.")
```

## Integration with Monitoring Tools

### Grafana

Use MQTT data source plugin or forward to InfluxDB:

1. Install InfluxDB MQTT consumer
2. Configure topics: `wattameter/+/data`
3. Create Grafana dashboard with InfluxDB data source
4. Visualize power consumption over time

### Prometheus

Use MQTT exporter to convert messages to Prometheus metrics:

```yaml
# mqtt_exporter config
mqtt:
  server: tcp://mqtt.example.com:1883
  topic: wattameter/+/data
metrics:
  - name: wattameter_power_watts
    help: "GPU/CPU power consumption"
    type: gauge
    mqtt_topic: wattameter/+/data
    value_path: "power[W]"
```

## Advanced Topics

### Custom Metadata

Future versions may support custom metadata in MQTT messages:

```python
# Planned feature (not yet implemented)
tracker = Tracker(
    reader=NVMLReader((Power,)),
    mqtt_config={
        "broker_host": "mqtt.example.com",
        "metadata": {
            "experiment_id": "exp-123",
            "node_id": "node-01",
        }
    }
)
```

### Multiple MQTT Brokers

To publish to multiple brokers, run separate WattAMeter instances or implement custom forwarding logic.

### Message Retention

Configure MQTT broker message retention for historical data:

```bash
# Mosquitto configuration
persistence true
persistence_location /var/lib/mosquitto/
```

### Quality of Service Levels

- **QoS 0**: Messages delivered at most once (fastest, potential loss)
- **QoS 1**: Messages delivered at least once (reliable, potential duplicates)
- **QoS 2**: Messages delivered exactly once (slowest, guaranteed delivery)

Choose based on your requirements:
- Real-time dashboards: QoS 0 or 1
- Critical accounting: QoS 1 or 2
- High-frequency logging: QoS 0
