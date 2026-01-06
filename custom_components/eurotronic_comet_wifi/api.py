"""Eurotronic Comet WIFI REST API Client."""
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class EurotronicAPI:
    """API client for Eurotronic Comet WIFI."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize the API client."""
        self.email = email
        self.password = password
        self._access_token: str | None = None
        self._token_timestamp: datetime | None = None
        self._mqtt_username: str | None = None
        self._mqtt_password: str | None = None
        self._user_data: dict[str, Any] | None = None
        self._session: aiohttp.ClientSession | None = None

    def _token_is_valid(self) -> bool:
        """Check if current token is still valid (not expired)."""
        if not self._access_token or not self._token_timestamp:
            return False
        # Token is valid for 30 minutes, refresh if less than 5 minutes remain
        elapsed = datetime.now() - self._token_timestamp
        remaining = timedelta(minutes=30) - elapsed
        if remaining.total_seconds() < 300:  # Less than 5 minutes
            _LOGGER.debug("Token expiring soon, will refresh")
            return False
        return True

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the API session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def login(self) -> bool:
        """Login and get JWT access token."""
        try:
            session = await self._get_session()
            
            # Create Basic Auth header
            credentials = f"{self.email}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "User-Agent": "Dart/3.4 (dart:io)",
                "Content-Type": "application/json; charset=UTF-8",
            }
            
            async with session.get(
                f"{API_BASE_URL}/login_flutter_android",
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    token_state = data.get("token_state", [])
                    if token_state and len(token_state) > 0:
                        self._access_token = token_state[0].get("x-access-token")
                        self._token_timestamp = datetime.now()
                        _LOGGER.info("Successfully logged in to Eurotronic API")
                        return True
                else:
                    error_text = await response.text()
                    _LOGGER.error("Login failed with status %s: %s", response.status, error_text)
                    return False
                    
        except Exception as err:
            _LOGGER.error("Login error: %s", err)
            return False

    async def get_user_info(self) -> dict[str, Any] | None:
        """Get user information including MQTT credentials."""
        if not self._token_is_valid():
            if not await self.login():
                return None
        
        try:
            session = await self._get_session()
            
            headers = {
                "x-access-token": self._access_token,
                "User-Agent": "Dart/3.4 (dart:io)",
                "Content-Type": "application/json; charset=UTF-8",
            }
            
            async with session.get(
                f"{API_BASE_URL}/get_self",
                headers=headers,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    user_list = data.get("user", [])
                    if user_list and len(user_list) > 0:
                        self._user_data = user_list[0]
                        self._mqtt_username = self._user_data.get("mqtt_username")
                        self._mqtt_password = self._user_data.get("mqtt_password")
                        _LOGGER.info(
                            "Retrieved user info, MQTT username: %s",
                            self._mqtt_username
                        )
                        return self._user_data
                else:
                    error_text = await response.text()
                    _LOGGER.error("Get user info failed: %s", error_text)
                    return None
                    
        except Exception as err:
            _LOGGER.error("Get user info error: %s", err)
            return None

    async def get_all_devices(self, location: str = "10") -> dict[str, Any] | None:
        """Get all devices and entities by location."""
        if not self._token_is_valid():
            if not await self.login():
                return None
        
        try:
            session = await self._get_session()
            
            headers = {
                "x-access-token": self._access_token,
                "User-Agent": "Dart/3.4 (dart:io)",
                "Content-Type": "application/json; charset=UTF-8",
            }
            
            payload = {"location": location}
            
            async with session.post(
                f"{API_BASE_URL}/get_all_entries_by_location",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.info("Retrieved devices data")
                    return data
                else:
                    error_text = await response.text()
                    _LOGGER.error("Get devices failed: %s", error_text)
                    return None
                    
        except Exception as err:
            _LOGGER.error("Get devices error: %s", err)
            return None

    async def update_room_profile(
        self,
        room_public_id: str,
        group_id: str,
        profile_id: str,
        profile_value: str,
        device_type_id: str = "0012",
    ) -> bool:
        """Update room profile (e.g., set temperature)."""
        if not self._token_is_valid():
            if not await self.login():
                return False
        
        try:
            session = await self._get_session()
            
            headers = {
                "x-access-token": self._access_token,
                "User-Agent": "Dart/3.4 (dart:io)",
                "Content-Type": "application/json; charset=UTF-8",
            }
            
            payload = {
                "room_public_id": room_public_id,
                "group_id": group_id,
                "profile_id": profile_id,
                "profile_value": profile_value,
                "device_type_id": device_type_id,
            }
            
            async with session.put(
                f"{API_BASE_URL}/update_room_profile",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    _LOGGER.info("Successfully updated room profile")
                    return True
                else:
                    error_text = await response.text()
                    _LOGGER.error("Update room profile failed: %s", error_text)
                    return False
                    
        except Exception as err:
            _LOGGER.error("Update room profile error: %s", err)
            return False

    @property
    def mqtt_username(self) -> str | None:
        """Get MQTT username from user data."""
        return self._mqtt_username

    @property
    def mqtt_password(self) -> str | None:
        """Get MQTT password from user data."""
        return self._mqtt_password

    @property
    def user_data(self) -> dict[str, Any] | None:
        """Get full user data."""
        return self._user_data
