"""Test MQTT connection for Eurotronic Comet WIFI.

This script tests if MQTT can be used to get real-time temperature readings.
"""
import os
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt


MQTT_BROKER = "mqtt.eurotronic.io"
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "02"


class EurotronicMQTTTest:
    """Test MQTT client for Eurotronic."""

    def __init__(self, username: str, password: str):
        """Initialize."""
        self.username = username
        self.password = password
        self.client = None
        self.devices = {}
        self.temperatures = {}
        self.connected = False
        self.message_count = 0

    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection."""
        if rc == 0:
            print(f"✅ Connected to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
            self.connected = True
            
            # Subscribe to all device topics
            topic = f"{MQTT_TOPIC_PREFIX}/{self.username}/#"
            print(f"📡 Subscribing to: {topic}")
            client.subscribe(topic)
        else:
            print(f"❌ Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection."""
        self.connected = False
        if rc != 0:
            print(f"Unexpected disconnection: {rc}")

    def _on_message(self, client, userdata, msg):
        """Handle incoming message."""
        self.message_count += 1
        topic = msg.topic
        payload = msg.payload.decode()
        
        print(f"\n📨 Message #{self.message_count}:")
        print(f"   Topic: {topic}")
        print(f"   Payload: {payload}")
        
        # Parse topic: 02/{username}/{mac}/{command}
        parts = topic.split("/")
        if len(parts) >= 4:
            mac = parts[2]
            command = "/".join(parts[3:])
            
            self.devices[mac] = self.devices.get(mac, {})
            self.devices[mac][command] = payload
            
            # Try to parse temperature
            if command == "T/B1":  # Current temperature
                try:
                    if payload.startswith("#"):
                        # Hex format
                        temp = int(payload[1:], 16) / 2
                    else:
                        # Decimal format
                        temp = float(payload)
                    
                    self.temperatures[mac] = temp
                    print(f"   🌡️  Current Temperature (T/B1): {temp}°C")
                except ValueError:
                    print(f"   ⚠️  Could not parse temperature: {payload}")
            
            # Parse target temperature
            elif command == "V/A0":  # Target temperature
                try:
                    if payload.startswith("#"):
                        temp = int(payload[1:], 16) / 2
                    else:
                        temp = float(payload)
                    print(f"   🎯 Target Temperature (V/A0): {temp}°C")
                except ValueError:
                    print(f"   ⚠️  Could not parse temperature: {payload}")

    def connect(self, timeout=10):
        """Connect to MQTT broker."""
        try:
            self.client = mqtt.Client(client_id=f"ha-test-{os.getpid()}")
            self.client.username_pw_set(self.username, self.password)
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            print(f"\n🔌 Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
            print(f"   Username: {self.username}")
            print("   Password: ****** (hidden)")
            
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            
            # Wait for connection
            start_time = time.time()
            while not self.connected:
                if time.time() - start_time > timeout:
                    print(f"❌ Connection timeout ({timeout}s)")
                    return False
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def disconnect(self):
        """Disconnect."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def wait_for_messages(self, timeout=15):
        """Wait for MQTT messages."""
        print(f"\n⏳ Waiting {timeout} seconds for messages from thermostat...")
        print("   (Make sure thermostat is online and receiving data)")
        
        start_time = time.time()
        last_count = 0
        
        while time.time() - start_time < timeout:
            if self.message_count > last_count:
                last_count = self.message_count
                remaining = timeout - (time.time() - start_time)
                print(f"   ({int(remaining)}s remaining...)")
            
            time.sleep(1)
        
        print(f"\n📊 Total messages received: {self.message_count}")
        
        if self.devices:
            print(f"\n📊 Devices found:")
            for mac, data in self.devices.items():
                print(f"\n   MAC: {mac}")
                for key, value in data.items():
                    print(f"      {key}: {value}")


def load_env():
    """Load environment variables."""
    env_file = Path(__file__).parent / ".env.test"
    if env_file.exists():
        print(f"📁 Loading: {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


def main():
    """Run test."""
    print("=" * 70)
    print("Eurotronic COMET WIFI - MQTT Real-Time Temperature Test")
    print("=" * 70)
    
    load_env()
    
    # Get credentials - either from env or use defaults from earlier connection
    mqtt_username = os.getenv("MQTT_USERNAME", "")
    mqtt_password = os.getenv("MQTT_PASSWORD", "")
    
    if not mqtt_username or not mqtt_password:
        print("\n❌ Error: MQTT credentials not found!")
        print("\nTo get MQTT credentials:")
        print("  1. Run: python test_api_standalone.py")
        print("  2. Copy the MQTT username and password from output")
        print("  3. Set environment variables:")
        print("     export MQTT_USERNAME='your-username'")
        print("     export MQTT_PASSWORD='your-password'")
        return False
    
    print(f"\n📡 MQTT Configuration:")
    print(f"   Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"   Username: {mqtt_username}")
    masked_password = "*" * len(mqtt_password) if mqtt_password else ""
    print(f"   Password: {masked_password}")
    
    # Connect to MQTT
    client = EurotronicMQTTTest(mqtt_username, mqtt_password)
    
    if not client.connect(timeout=10):
        print("\n❌ Failed to connect to MQTT broker")
        print("\nPossible reasons:")
        print("  • MQTT credentials are incorrect")
        print("  • Network connectivity issue")
        print("  • MQTT broker is not accessible")
        return False
    
    # Wait for messages
    client.wait_for_messages(timeout=20)
    
    client.disconnect()
    
    # Report results
    print("\n" + "=" * 70)
    if client.temperatures:
        print("✅ SUCCESS: Retrieved real-time temperatures via MQTT!")
        print("\n   Devices with temperature data:")
        for mac, temp in client.temperatures.items():
            print(f"   • {mac}: {temp}°C")
        print("\n💡 Next step: MQTT will be integrated into Home Assistant for")
        print("   real-time temperature readings!")
        return True
    elif client.message_count > 0:
        print("⚠️  MQTT connection successful but no temperature data yet")
        print(f"   Received {client.message_count} message(s)")
        print("   Device might not be actively sending temperature data")
        print("   Try again in a few seconds")
        return True
    else:
        print("❌ No MQTT messages received")
        print("\n   Possible reasons:")
        print("   • Thermostat is offline")
        print("   • Device not assigned to this account")
        print("   • MQTT credentials don't match device owner")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
