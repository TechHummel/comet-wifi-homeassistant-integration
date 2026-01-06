"""Test MQTT temperature caching functionality."""
import sys
import time
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock homeassistant modules before importing
sys.modules['homeassistant'] = Mock()
sys.modules['homeassistant.config_entries'] = Mock()
sys.modules['homeassistant.const'] = Mock()
sys.modules['homeassistant.core'] = Mock()
sys.modules['homeassistant.exceptions'] = Mock()
sys.modules['homeassistant.helpers'] = Mock()
sys.modules['homeassistant.helpers.update_coordinator'] = Mock()

from custom_components.eurotronic_comet_wifi.mqtt import EurotronicMQTTClient


def test_temperature_caching():
    """Test that temperature caching works correctly."""
    print("Testing MQTT temperature caching...")
    
    # Create client (don't need to connect for cache testing)
    client = EurotronicMQTTClient(
        broker="mqtt.eurotronic.io",
        port=1883,
        username="test_user",
        password="test_pass",
    )
    
    # Test 1: No temperature stored
    print("\n1. Testing no temperature stored...")
    assert client.get_temperature("AA:BB:CC:DD:EE:FF", "A1") is None
    assert client.get_temperature_age("AA:BB:CC:DD:EE:FF", "A1") is None
    assert not client.has_recent_temperature("AA:BB:CC:DD:EE:FF", "A1")
    print("   ✓ No temperature returns None")
    
    # Test 2: Store a temperature
    print("\n2. Testing temperature storage...")
    mac = "AA:BB:CC:DD:EE:FF"
    # Note: Directly accessing private attributes in tests is acceptable for unit testing
    # internal state. In production, temperatures are set via MQTT message callbacks.
    client._temperatures[mac] = {"A1": 21.5}
    client._temperature_timestamps[mac] = {"A1": time.time()}
    
    temp = client.get_temperature(mac, "A1")
    assert temp == 21.5
    print(f"   ✓ Temperature stored and retrieved: {temp}°C")
    
    # Test 3: Recent temperature
    print("\n3. Testing recent temperature detection...")
    age = client.get_temperature_age(mac, "A1")
    assert age is not None and age < 1  # Should be less than 1 second old
    assert client.has_recent_temperature(mac, "A1", max_age=600)
    print(f"   ✓ Temperature age: {age:.2f}s (recent)")
    
    # Test 4: Old temperature
    print("\n4. Testing old temperature detection...")
    # Set timestamp to 11 minutes ago
    client._temperature_timestamps[mac]["A1"] = time.time() - 660
    age = client.get_temperature_age(mac, "A1")
    assert age > 660
    assert not client.has_recent_temperature(mac, "A1", max_age=600)
    print(f"   ✓ Temperature age: {age:.2f}s (too old)")
    
    # Temperature value should still be accessible
    temp = client.get_temperature(mac, "A1")
    assert temp == 21.5
    print(f"   ✓ Old temperature still accessible: {temp}°C")
    
    # Test 5: Multiple profiles
    print("\n5. Testing multiple temperature profiles...")
    client._temperatures[mac]["A0"] = 20.0  # Target temperature
    client._temperature_timestamps[mac]["A0"] = time.time()
    
    temp_a1 = client.get_temperature(mac, "A1")
    temp_a0 = client.get_temperature(mac, "A0")
    assert temp_a1 == 21.5
    assert temp_a0 == 20.0
    
    age_a1 = client.get_temperature_age(mac, "A1")
    age_a0 = client.get_temperature_age(mac, "A0")
    assert age_a1 > 660  # Old
    assert age_a0 < 1    # Recent
    
    assert not client.has_recent_temperature(mac, "A1", max_age=600)
    assert client.has_recent_temperature(mac, "A0", max_age=600)
    print(f"   ✓ A1 (current): {temp_a1}°C, age: {age_a1:.2f}s")
    print(f"   ✓ A0 (target): {temp_a0}°C, age: {age_a0:.2f}s")
    
    print("\n✅ All tests passed!")
    return True


def test_reconnection_logic():
    """Test that reconnection attempts are tracked."""
    print("\nTesting reconnection logic...")
    
    client = EurotronicMQTTClient(
        broker="mqtt.eurotronic.io",
        port=1883,
        username="test_user",
        password="test_pass",
    )
    
    # Test 1: Initial state
    print("\n1. Testing initial reconnection state...")
    assert client._reconnect_attempts == 0
    assert client._max_reconnect_delay == 300
    print("   ✓ Initial state correct")
    
    # Test 2: Simulate disconnection
    print("\n2. Testing disconnection counter...")
    client._on_disconnect(client.client, None, 7)  # Error code 7
    assert client._reconnect_attempts == 1
    assert not client._connected
    print("   ✓ Reconnection attempt incremented")
    
    # Test 3: Multiple disconnections with exponential backoff
    print("\n3. Testing exponential backoff...")
    for i in range(2, 6):
        client._on_disconnect(client.client, None, 7)
        expected_delay = min(1 * (2 ** (i - 1)), 300)
        print(f"   Attempt {i}: expected delay up to {expected_delay}s")
    assert client._reconnect_attempts == 5
    print(f"   ✓ Reconnection attempts: {client._reconnect_attempts}")
    
    # Test 4: Successful reconnection resets counter
    print("\n4. Testing reconnection reset...")
    client._on_connect(client.client, None, {}, 0)  # Successful connection
    assert client._reconnect_attempts == 0
    assert client._connected
    print("   ✓ Reconnection counter reset on success")
    
    print("\n✅ All reconnection tests passed!")
    return True


if __name__ == "__main__":
    print("=" * 70)
    print("MQTT Temperature Caching and Reconnection Tests")
    print("=" * 70)
    
    try:
        test_temperature_caching()
        test_reconnection_logic()
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
