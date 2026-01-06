"""Standalone tests for Eurotronic Comet WIFI API client.

This test file can run independently without Home Assistant.
"""
import asyncio
import base64
import os
import sys
from pathlib import Path

import aiohttp


API_BASE_URL = "https://accounts-v5.eurotronic.io"


class EurotronicAPITest:
    """Test API client."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize."""
        self.email = email
        self.password = password
        self._access_token = None
        self._session = None

    async def _get_session(self):
        """Get or create session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def login(self):
        """Login."""
        try:
            session = await self._get_session()
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
                        return True
                else:
                    error_text = await response.text()
                    print(f"Login failed: {error_text}")
                    return False
        except Exception as e:
            print(f"Login error: {e}")
            return False

    async def get_user_info(self):
        """Get user info."""
        if not self._access_token:
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
                    if user_list:
                        return user_list[0]
                return None
        except Exception as e:
            print(f"Get user info error: {e}")
            return None

    async def get_all_devices(self):
        """Get all devices."""
        if not self._access_token:
            if not await self.login():
                return None
        
        try:
            session = await self._get_session()
            headers = {
                "x-access-token": self._access_token,
                "User-Agent": "Dart/3.4 (dart:io)",
                "Content-Type": "application/json; charset=UTF-8",
            }
            
            payload = {"location": "10"}
            
            async with session.post(
                f"{API_BASE_URL}/get_all_entries_by_location",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Get devices error: {e}")
            return None

    async def update_room_profile(self, room_public_id, group_id, profile_id, profile_value):
        """Update room profile."""
        if not self._access_token:
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
                "device_type_id": "0012",
            }
            
            async with session.put(
                f"{API_BASE_URL}/update_room_profile",
                headers=headers,
                json=payload,
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"Update error: {e}")
            return False


async def test_login():
    """Test login."""
    email = os.getenv("TEST_EMAIL") or os.getenv("EUROTRONIC_EMAIL")
    password = os.getenv("TEST_PASSWORD") or os.getenv("EUROTRONIC_PASSWORD")
    
    if not email or not password:
        print("❌ Error: TEST_EMAIL and TEST_PASSWORD (or EUROTRONIC_EMAIL/EUROTRONIC_PASSWORD) required")
        return False
    
    print(f"Testing login with: {email}")
    
    api = EurotronicAPITest(email, password)
    
    try:
        success = await api.login()
        if success:
            print("✅ Login successful")
            print(f"   Token: {api._access_token[:30]}...")
            return True
        else:
            print("❌ Login failed")
            return False
    finally:
        await api.close()


async def test_user_info():
    """Test get user info."""
    email = os.getenv("TEST_EMAIL") or os.getenv("EUROTRONIC_EMAIL")
    password = os.getenv("TEST_PASSWORD") or os.getenv("EUROTRONIC_PASSWORD")
    
    print("\nTesting get_user_info...")
    
    api = EurotronicAPITest(email, password)
    
    try:
        user_info = await api.get_user_info()
        if user_info:
            print("✅ User info retrieved")
            print(f"   Email: {user_info.get('mail')}")
            print(f"   MQTT Username: {user_info.get('mqtt_username')}")
            print(f"   MQTT Password: {user_info.get('mqtt_password')}")
            print(f"   Broker: {user_info.get('broker')}")
            return True
        else:
            print("❌ Failed to get user info")
            return False
    finally:
        await api.close()


async def test_devices():
    """Test get devices."""
    email = os.getenv("TEST_EMAIL") or os.getenv("EUROTRONIC_EMAIL")
    password = os.getenv("TEST_PASSWORD") or os.getenv("EUROTRONIC_PASSWORD")
    
    print("\nTesting get_all_devices...")
    
    api = EurotronicAPITest(email, password)
    
    try:
        devices = await api.get_all_devices()
        if devices:
            print("✅ Devices retrieved")
            items = devices.get("items", [])
            
            for item in items:
                if "device_managements" in item:
                    for device in item["device_managements"]:
                        print(f"\n   Device: {device.get('device_name')}")
                        print(f"   MAC: {device.get('mac')}")
                        print(f"   SSID: {device.get('ssid_name')}")
                
                if "device_profiles" in item:
                    print("   Profiles:")
                    profiles = item["device_profiles"]
                    for profile in profiles[:5]:
                        pid = profile.get('profile_id')
                        pval = profile.get('profile_value')
                        print(f"     {pid}: {pval}")
            
            return True
        else:
            print("❌ Failed to get devices")
            return False
    finally:
        await api.close()


async def main():
    """Run tests."""
    print("=" * 60)
    print("Eurotronic Comet WIFI API Tests")
    print("=" * 60)
    
    # Load .env.test
    env_file = Path(__file__).parent / ".env.test"
    if env_file.exists():
        print(f"\nLoading: {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    
    results = []
    results.append(("Login", await test_login()))
    results.append(("Get User Info", await test_user_info()))
    results.append(("Get Devices", await test_devices()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:.<40} {status}")
    
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{len(results)} passed")
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
