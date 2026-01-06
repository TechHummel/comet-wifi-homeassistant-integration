"""Sensor platform for Eurotronic Comet WIFI."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eurotronic Comet WIFI sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    mqtt_client = hass.data[DOMAIN][entry.entry_id]["mqtt_client"]
    
    if not coordinator.data:
        _LOGGER.warning("No devices found during sensor setup")
        return
    
    entities = []
    for mac, device_data in coordinator.data.items():
        # WiFi Signal Strength sensor
        entities.append(
            EurotronicSignalStrengthSensor(coordinator, mqtt_client, mac)
        )
    
    async_add_entities(entities)


class EurotronicSignalStrengthSensor(CoordinatorEntity, SensorEntity):
    """WiFi Signal Strength (RSSI) sensor."""

    _attr_has_entity_name = True
    _attr_name = "WiFi Signal Strength"
    _attr_unique_id_suffix = "signal_strength"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_icon = "mdi:wifi-strength-3"

    def __init__(self, coordinator, mqtt_client, mac: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._mqtt_client = mqtt_client
        self._mac = mac
        self._attr_unique_id = f"{DOMAIN}_{mac}_signal_strength"

    @property
    def device_info(self):
        """Return device information."""
        device_data = self.coordinator.data.get(self._mac, {})
        
        # Get firmware versions from device profiles
        profiles = device_data.get("profiles", {})
        wifi_fw = profiles.get("B2", "Unknown")
        
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": device_data.get("name", f"Thermostat {self._mac}"),
            "manufacturer": "Eurotronic",
            "model": "Comet WIFI",
            "hw_version": self._mac,
            "sw_version": f"WiFi: {wifi_fw}",
        }

    @property
    def native_value(self) -> int | None:
        """Return the WiFi signal strength in dBm."""
        device_data = self.coordinator.data.get(self._mac, {})
        
        # Try to get from REST API profiles first
        profiles = device_data.get("profiles", {})
        if "B3" in profiles:
            try:
                rssi = int(profiles.get("B3", 0))
                return rssi
            except (ValueError, TypeError):
                pass
        
        # Fall back to MQTT data
        mqtt_data = device_data.get("mqtt_data", {})
        return mqtt_data.get("signal_strength")

