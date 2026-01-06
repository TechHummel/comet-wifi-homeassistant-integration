# Eurotronic Comet WIFI Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant integration for Eurotronic Comet WIFI thermostats using the official REST API.

## Features

- **Automatic Device Discovery**: All your Eurotronic thermostats are automatically discovered after login
- **Temperature Control**: Set and monitor target temperatures
- **Current Temperature**: Display current room temperatures
- **HVAC Modes**: Support for Heat and Off modes
- **Native Home Assistant Climate Entity**: Full integration with Home Assistant's thermostat interface

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/eurotronic_comet_wifi` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Via UI

1. Go to Settings → Devices & Services
2. Click "+ ADD INTEGRATION"
3. Search for "Eurotronic Comet WIFI"
4. Enter your Eurotronic account credentials:
   - Email address
   - Password
5. Click "Submit"

Your thermostats will be automatically discovered and added as climate entities.

## Supported Devices

- Eurotronic Comet WIFI (device_type_id: 0012)

## API Information

This integration uses the official Eurotronic REST API:
- Base URL: `https://accounts-v5.eurotronic.io`
- Authentication: JWT tokens via Basic Auth
- Endpoints:
  - `/login_flutter_android` - Login and get JWT token
  - `/get_self` - Get user information
  - `/get_all_entries_by_location` - Get all devices and their states
  - `/update_room_profile` - Update device settings (e.g., temperature)

### Network Traffic Analysis

The integration was developed by analyzing the network traffic of the official Eurotronic Smart Living 2.0 Android app (v1.5.1). All captured API requests and responses are documented in the `captured_network_traffic/` directory.

## Temperature Values

Temperature values are encoded in hexadecimal format in the API:
- **Conversion**: `temp_celsius = hex_value / 2`
- **Example**: `0x28` (40 decimal) = 20.0°C
- **Range**: 5.0°C - 30.0°C
- **Step**: 0.5°C

## Profile IDs

The API uses profile IDs to identify different device parameters:
- **A0**: Target temperature (room profile)
- **A6**: Current room temperature (device profile)
- **B1**: Battery voltage
- **B2**: Firmware version
- **B3**: RSSI (WiFi signal strength)

## Development

### Testing

The integration includes comprehensive tests:

```bash
# Run standalone API tests
python test_api_standalone.py
```

Test credentials can be configured in `.env.test`:

```bash
EUROTRONIC_EMAIL=your-email@example.com
EUROTRONIC_PASSWORD=your-password
```

### Project Structure

```
custom_components/eurotronic_comet_wifi/
├── __init__.py          # Integration setup and data coordinator
├── api.py               # REST API client
├── climate.py           # Climate entity implementation
├── config_flow.py       # Configuration flow (UI setup)
├── const.py             # Constants
├── manifest.json        # Integration metadata
└── strings.json         # UI strings
```

## Troubleshooting

### Login Fails

- Verify your email and password are correct
- Check that you can login to the official Eurotronic app
- Ensure your internet connection is working

### No Devices Found

- Make sure your thermostats are properly set up in the Eurotronic app
- Check that devices are assigned to location "10" (default location)
- Restart Home Assistant after adding devices in the app

### Temperature Updates Slow

- The integration polls the API every 30 seconds
- Temperature changes may take 1-2 minutes to sync
- Check your thermostat's WiFi connection

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial integration developed by reverse-engineering the official Eurotronic Smart Living 2.0 Android app. It is not affiliated with, endorsed by, or connected to Eurotronic Technology GmbH.

Use at your own risk. The author is not responsible for any damage to your devices or Home Assistant installation.

## Acknowledgments

- Thanks to Eurotronic for creating the Comet WIFI thermostat
- Inspired by the Home Assistant community and their excellent documentation
- Network traffic analysis performed with Android Debug Bridge (ADB) and HTTP Toolkit

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Note**: This integration requires an active Eurotronic account and internet connection to function.
