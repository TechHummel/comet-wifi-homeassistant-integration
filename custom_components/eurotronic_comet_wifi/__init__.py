"""The Eurotronic Comet WIFI integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EurotronicAPI
from .const import DOMAIN
from .mqtt import EurotronicMQTTClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eurotronic Comet WIFI from a config entry."""
    
    # Handle migration from old config format
    email = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)
    
    api = EurotronicAPI(email, password)
    mqtt_client = None
    
    try:
        # Login and get user info
        if not await api.login():
            raise ConfigEntryNotReady("Failed to login to Eurotronic API")
        
        # Get user info to verify connection and get MQTT credentials
        user_info = await api.get_user_info()
        if not user_info:
            raise ConfigEntryNotReady("Failed to get user info from API")
        
        # Try to set up MQTT for real-time temperature updates
        mqtt_username = user_info.get("mqtt_username")
        mqtt_password = user_info.get("mqtt_password")
        
        if mqtt_username and mqtt_password:
            mqtt_client = EurotronicMQTTClient(
                broker="mqtt.eurotronic.io",
                port=1883,
                username=mqtt_username,
                password=mqtt_password,
            )
            
            if await mqtt_client.async_connect():
                _LOGGER.info("MQTT client connected for real-time updates")
            else:
                _LOGGER.warning("Failed to connect MQTT client, continuing with REST API only")
                mqtt_client = None
        else:
            _LOGGER.warning("MQTT credentials not available from API")
            
    except Exception as err:
        _LOGGER.error("Failed to setup API client: %s", err)
        raise ConfigEntryNotReady from err

    coordinator = EurotronicDataUpdateCoordinator(hass, api, mqtt_client)
    
    # Wait for initial data refresh
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "mqtt_client": mqtt_client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN][entry.entry_id]
        api = data["api"]
        mqtt_client = data.get("mqtt_client")
        
        await api.close()
        
        if mqtt_client:
            await mqtt_client.async_disconnect()
        
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class EurotronicDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: EurotronicAPI, mqtt_client: EurotronicMQTTClient | None = None) -> None:
        """Initialize."""
        self.api = api
        self.mqtt_client = mqtt_client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            # Get all devices and parse them into a usable format
            data = await self.api.get_all_devices()
            if not data:
                raise UpdateFailed("Failed to fetch device data")
            
            devices = {}
            items = data.get("items", [])
            
            # Extract device information
            device_managements = next((item.get("device_managements", []) for item in items if "device_managements" in item), [])
            device_profiles = next((item.get("device_profiles", []) for item in items if "device_profiles" in item), [])
            device_groups = next((item.get("device_groups", []) for item in items if "device_groups" in item), [])
            room_profiles = next((item.get("room_profiles", []) for item in items if "room_profiles" in item), [])
            
            # Build device dictionary
            for device in device_managements:
                mac = device.get("mac")
                if not mac:
                    continue
                    
                devices[mac] = {
                    "name": device.get("device_name", f"Thermostat {mac}"),
                    "mac": mac,
                    "device_type_id": device.get("device_type_id"),
                    "ssid_name": device.get("ssid_name"),
                    "profiles": {},
                }
                
                # Add device profiles
                for profile in device_profiles:
                    if profile.get("mac") == mac:
                        profile_id = profile.get("profile_id")
                        devices[mac]["profiles"][profile_id] = profile.get("profile_value")
                
                # Add group information
                for dg in device_groups:
                    if dg.get("mac") == mac:
                        devices[mac]["group_id"] = dg.get("group_id")
                        
                        # Find room profiles for this group
                        for rp in room_profiles:
                            if rp.get("group_id") == dg.get("group_id"):
                                devices[mac]["room_profiles"] = devices[mac].get("room_profiles", {})
                                devices[mac]["room_profiles"][rp.get("profile_id")] = {
                                    "value": rp.get("profile_value"),
                                    "room_public_id": rp.get("room_public_id"),
                                }
                
                # Add MQTT data if available
                if self.mqtt_client:
                    devices[mac]["mqtt_data"] = self.mqtt_client.get_device_data(mac)
            
            return devices
            
        except Exception as exception:
            _LOGGER.error("Error updating data: %s", exception)
            raise UpdateFailed() from exception
