"""Climate platform for Eurotronic Comet WIFI."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
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
    """Set up Eurotronic Comet WIFI climate entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    mqtt_client = hass.data[DOMAIN][entry.entry_id].get("mqtt_client")
    
    # Wait for initial data
    if not coordinator.data:
        _LOGGER.warning("No devices found during setup")
        return
    
    entities = []
    for mac, device_data in coordinator.data.items():
        entities.append(EurotronicThermostat(coordinator, api, mqtt_client, mac))
    
    async_add_entities(entities)


class EurotronicThermostat(CoordinatorEntity, ClimateEntity):
    """Representation of an Eurotronic Comet WIFI thermostat."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_min_temp = 5.0
    _attr_max_temp = 30.0
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator, api, mqtt_client, mac: str) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator)
        self._api = api
        self._mqtt_client = mqtt_client
        self._mac = mac
        self._attr_unique_id = f"{DOMAIN}_{mac}"

    @property
    def device_info(self):
        """Return device information."""
        device_data = self.coordinator.data.get(self._mac, {})
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": device_data.get("name", f"Thermostat {self._mac}"),
            "manufacturer": "Eurotronic",
            "model": "Comet WIFI",
            "sw_version": device_data.get("profiles", {}).get("B2", "Unknown"),
        }

    @property
    def name(self):
        """Return the name of the thermostat."""
        device_data = self.coordinator.data.get(self._mac, {})
        return device_data.get("name", f"Thermostat {self._mac}")

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature.
        """
        if self._mqtt_client and self._mqtt_client.is_connected:
            mqtt_temp = self._mqtt_client.get_temperature(self._mac, profile="A1")
            if mqtt_temp is not None:
                _LOGGER.debug(
                    "Using MQTT temperature for %s: %.1f°C", self._mac, mqtt_temp
                )
                return mqtt_temp

        # No MQTT value available -> report unavailable
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        device_data = self.coordinator.data.get(self._mac, {})
        room_profiles = device_data.get("room_profiles", {})
        
        # Profile A0 contains target temperature from REST API
        profile_a0 = room_profiles.get("A0", {})
        temp_value = profile_a0.get("value")
        
        if temp_value and temp_value != "#":
            try:
                # Value is in hex, need to convert and divide by 2
                temp = int(temp_value, 16) / 2
                return float(temp)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current operation mode."""
        # Device has no explicit mode flag; treat as heating-capable whenever available.
        target_temp = self.target_temperature
        if target_temp is None:
            return HVACMode.HEAT
        return HVACMode.HEAT if target_temp > self._attr_min_temp else HVACMode.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        device_data = self.coordinator.data.get(self._mac, {})
        room_profiles = device_data.get("room_profiles", {})
        profile_a0 = room_profiles.get("A0", {})
        
        room_public_id = profile_a0.get("room_public_id")
        group_id = device_data.get("group_id")
        
        if not room_public_id or not group_id:
            _LOGGER.error("Missing room_public_id or group_id for device %s", self._mac)
            return

        # Convert temperature to hex format (multiply by 2, convert to hex)
        temp_hex = f"{int(temperature * 2):02X}"
        
        _LOGGER.debug(
            "Setting temperature for %s to %.1f°C (hex: %s)",
            self._mac,
            temperature,
            temp_hex,
        )

        # Call API to update room profile
        success = await self._api.update_room_profile(
            room_public_id=room_public_id,
            group_id=group_id,
            profile_id="A0",
            profile_value=temp_hex,
            device_type_id=device_data.get("device_type_id", "0012"),
        )

        if success:
            # Request immediate data refresh
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set temperature for %s", self._mac)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            # Set to minimum temperature to turn off
            await self.async_set_temperature(temperature=self._attr_min_temp)
        elif hvac_mode == HVACMode.HEAT:
            # Set to a reasonable default temperature
            await self.async_set_temperature(temperature=20.0)
