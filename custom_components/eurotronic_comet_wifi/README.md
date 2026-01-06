# Eurotronic Comet WIFI Home Assistant Integration

Custom integration for controlling Eurotronic Comet WIFI thermostats. Built from reverse engineering the Eurotronic Smart Living 2.0 Android app (v1.5.1). Commands are sent via MQTT; state is polled from the cloud API.

## Reverse engineering highlights
- APK decompiled with jadx; endpoints and MQTT usage extracted from `libapp.so`
- Base API: `https://accounts-v5.eurotronic.io/`
- Communication: REST (inventory + polling) + MQTT (commands)
- Auth: JWT access/refresh tokens

## Features
- Auto device discovery from Eurotronic cloud
- Target temperature control (5–30 °C, 0.5 °C)
- Battery level sensor
- HVAC modes: heat / auto / off
- Preset modes: manual / auto / holiday
- MQTT command publishing (temperature, HVAC, preset)

## Installation
- HACS (recommended): add this repo as a custom *Integration*, install, restart HA
- Manual: copy `custom_components/eurotronic_comet_wifi` into `<config>/custom_components/`, restart, then add the integration

## Configuration
1. Add integration **Eurotronic Comet WIFI** in Home Assistant
2. Enter Eurotronic account email and password
3. Devices are discovered automatically

## Usage
- Climate entity per thermostat (current temp, target temp, HVAC & preset modes)
- Battery sensor per device

## MQTT behavior
- Broker details are fetched from `/api/mqtt/config`
- Commands publish to MQTT; state is still polled every 60 s (no MQTT subscribe yet)

## Limitations
- No schedule/profile management; use the official app
- No live push updates until MQTT state topics are fully mapped

## Debug logging
```yaml
logger:
  default: info
  logs:
    custom_components.eurotronic_comet_wifi: debug
```

## License & disclaimer
- MIT License
- Unofficial community project; not affiliated with Eurotronic Technology GmbH
