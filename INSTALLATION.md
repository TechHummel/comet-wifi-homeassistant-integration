# Installation Guide

## Prerequisites

- Home Assistant 2023.1 or newer
- Eurotronic Comet WIFI thermostat(s)
- Eurotronic account (created via the official app)

## Method 1: HACS (Recommended)

### Step 1: Add Custom Repository

1. Open HACS in your Home Assistant UI
2. Click on **Integrations**
3. Click the three dots (⋮) in the top right corner
4. Select **Custom repositories**
5. Enter the repository URL: `https://github.com/YOUR_USERNAME/eurotronic-comet-wifi`
6. Select **Integration** as the category
7. Click **ADD**

### Step 2: Install the Integration

1. In HACS, search for "Eurotronic Comet WIFI"
2. Click on the integration
3. Click **DOWNLOAD**
4. Restart Home Assistant

### Step 3: Configure the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for "Eurotronic Comet WIFI"
4. Enter your credentials:
   - **Email**: Your Eurotronic account email
   - **Password**: Your Eurotronic account password
5. Click **SUBMIT**

Your thermostats will be discovered automatically!

## Method 2: Manual Installation

### Step 1: Download Files

Download the latest release from GitHub or clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/eurotronic-comet-wifi.git
```

### Step 2: Copy Files

Copy the integration folder to your Home Assistant configuration directory:

```bash
cp -r eurotronic-comet-wifi/custom_components/eurotronic_comet_wifi \
    /config/custom_components/
```

Your directory structure should look like:

```
config/
└── custom_components/
    └── eurotronic_comet_wifi/
        ├── __init__.py
        ├── api.py
        ├── climate.py
        ├── config_flow.py
        ├── const.py
        ├── manifest.json
        └── strings.json
```

### Step 3: Restart Home Assistant

Restart Home Assistant to load the new integration.

### Step 4: Configure

Follow Step 3 from Method 1 above to configure the integration.

## Verification

After installation and configuration, you should see:

1. **In Integrations**: "Eurotronic Comet WIFI" integration with your email
2. **In Devices**: One device per thermostat with:
   - Device name (e.g., "Schlafzimmer")
   - MAC address
   - Firmware version
3. **In Entities**: Climate entities for each thermostat

## Troubleshooting

### Integration Not Found

- Ensure files are in the correct directory: `config/custom_components/eurotronic_comet_wifi/`
- Check file permissions
- Restart Home Assistant completely (not just reload)

### Login Failed

- Verify credentials in the official Eurotronic app
- Check internet connection
- Try resetting your password in the app

### No Devices Discovered

- Ensure thermostats are set up in the official app
- Check that devices are online and connected to WiFi
- Verify location is set to "10" (default)

For more help, see [README.md](README.md#troubleshooting).
