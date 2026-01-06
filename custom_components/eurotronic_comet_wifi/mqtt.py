"""MQTT client for Eurotronic Comet WIFI."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import paho.mqtt.client as mqtt_client

_LOGGER = logging.getLogger(__name__)


class EurotronicMQTTClient:
    """MQTT client for real-time temperature updates."""

    def __init__(
        self,
        broker: str,
        port: int,
        username: str,
        password: str,
        on_message_callback: Callable[[str, str, str], None] | None = None,
    ) -> None:
        """Initialize MQTT client.
        
        Args:
            broker: MQTT broker address
            port: MQTT broker port
            username: MQTT username
            password: MQTT password
            on_message_callback: Callback for messages (topic, device_mac, payload)
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.on_message_callback = on_message_callback
        
        self.client = mqtt_client.Client(
            client_id=f"ha-eurotronic-{username}",
            clean_session=True,
            protocol=mqtt_client.MQTTv311,
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self._connected = False
        self._subscription_topic = f"02/{username}/#"
        self._temperatures: dict[str, dict[str, float]] = {}
        self._device_data: dict[str, dict[str, Any]] = {}  # Store all MQTT data

    def _on_connect(
        self, client: mqtt_client.Client, userdata: Any, flags: dict, rc: int
    ) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            _LOGGER.info("Connected to MQTT broker at %s:%d", self.broker, self.port)
            self._connected = True
            # Subscribe to device messages
            client.subscribe(self._subscription_topic, qos=1)
            _LOGGER.debug("Subscribed to: %s", self._subscription_topic)
        else:
            _LOGGER.error("Failed to connect to MQTT broker, code %d", rc)
            self._connected = False

    def _on_disconnect(
        self, client: mqtt_client.Client, userdata: Any, rc: int
    ) -> None:
        """Handle MQTT disconnection."""
        if rc != 0:
            _LOGGER.warning("Unexpected disconnection from MQTT broker, code %d", rc)
        self._connected = False

    def _on_message(
        self, client: mqtt_client.Client, userdata: Any, msg: mqtt_client.MQTTMessage
    ) -> None:
        """Handle MQTT message."""
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8") if msg.payload else ""
            
            # Parse topic: 02/{username}/{mac}/{category}/{profile}
            parts = topic.split("/")
            if len(parts) >= 4:
                mac = parts[2]
                category = parts[3]
                profile = parts[4] if len(parts) > 4 else ""
                
                _LOGGER.debug(
                    "MQTT Message - MAC: %s, Category: %s, Profile: %s, Payload: %s",
                    mac,
                    category,
                    profile,
                    payload,
                )
                
                # Parse temperature values
                if category == "V" and profile in ("A1", "A0", "A6"):
                    try:
                        if payload.startswith("#"):
                            hex_val = payload[1:]
                            temp = int(hex_val, 16) / 2 if hex_val else None
                            if mac not in self._temperatures:
                                self._temperatures[mac] = {}
                            self._temperatures[mac][profile] = temp
                            _LOGGER.debug(
                                "Temperature update - MAC: %s, Profile: %s, Value: %.1f°C",
                                mac,
                                profile,
                                temp,
                            )
                    except (ValueError, TypeError) as err:
                        _LOGGER.warning(
                            "Failed to parse temperature from %s: %s",
                            payload,
                            err,
                        )
                
                # Store other sensor data
                if mac not in self._device_data:
                    self._device_data[mac] = {}
                
                # Parse specific profiles for sensors
                if profile == "B3":  # RSSI / Signal Strength
                    try:
                        rssi = int(payload)
                        self._device_data[mac]["signal_strength"] = rssi
                    except (ValueError, TypeError):
                        pass
                
                elif profile == "A3":  # Ventilation / Window Detection
                    # A3 contains hex value for ventilation status
                    # Format: first byte = status, second byte = additional info
                    try:
                        if payload.startswith("#"):
                            hex_val = payload[1:]
                        else:
                            hex_val = payload
                        
                        if len(hex_val) >= 2:
                            status_byte = int(hex_val[:2], 16)
                            # Interpret ventilation status
                            if status_byte == 0x00:
                                self._device_data[mac]["ventilation_status"] = "closed"
                            elif status_byte in (0x01, 0x02):
                                self._device_data[mac]["ventilation_status"] = "tilted"
                            elif status_byte in (0x03, 0x04):
                                self._device_data[mac]["ventilation_status"] = "open"
                            else:
                                self._device_data[mac]["ventilation_status"] = f"unknown_{status_byte:02x}"
                    except (ValueError, TypeError):
                        self._device_data[mac]["ventilation_status"] = "unknown"
                
                elif profile == "B1":  # Regler Software Version (Battery in device_profile)
                    try:
                        version = payload
                        self._device_data[mac]["regler_version"] = version
                    except Exception:
                        pass
                
                # Call callback if provided
                if self.on_message_callback:
                    try:
                        self.on_message_callback(topic, mac, payload)
                    except Exception as err:
                        _LOGGER.error("Error in MQTT callback: %s", err)
        except Exception as err:
            _LOGGER.error("Error processing MQTT message: %s", err)

    async def async_connect(self) -> bool:
        """Connect to MQTT broker.
        
        Returns:
            True if connected successfully, False otherwise.
        """
        try:
            self.client.username_pw_set(self.username, self.password)
            self.client.connect(self.broker, self.port, keepalive=60)
            
            # Start the network loop in a separate thread
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            while not self._connected and timeout > 0:
                await asyncio.sleep(0.5)
                timeout -= 0.5
            
            if self._connected:
                _LOGGER.info("Successfully connected to MQTT broker")
                return True
            else:
                _LOGGER.error("Timeout waiting for MQTT connection")
                return False
        except Exception as err:
            _LOGGER.error("Error connecting to MQTT broker: %s", err)
            return False

    async def async_disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self._connected = False
            _LOGGER.info("Disconnected from MQTT broker")
        except Exception as err:
            _LOGGER.error("Error disconnecting from MQTT broker: %s", err)

    def get_temperature(self, mac: str, profile: str = "A1") -> float | None:
        """Get stored temperature for device.
        
        Args:
            mac: Device MAC address
            profile: Temperature profile (A1=current, A0=target)
            
        Returns:
            Temperature in Celsius or None if not available.
        """
        return self._temperatures.get(mac, {}).get(profile)

    def get_device_data(self, mac: str) -> dict[str, Any]:
        """Get all stored MQTT data for device.
        
        Args:
            mac: Device MAC address
            
        Returns:
            Dictionary with device data (signal_strength, ventilation_status, etc.)
        """
        return self._device_data.get(mac, {})

    @property
    def is_connected(self) -> bool:
        """Return whether MQTT client is connected."""
        return self._connected
