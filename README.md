# home-assistant-inmes

Home Assistant custom integration for [INMES](https://app.inmes.cz) smart utility meters.

## Features

- Reads cold water, hot water, and heat meter readings from the INMES cloud
- Creates one sensor per active meter in your unit
- Updates every 3 hours (cloud polling)
- Supports re-authentication when credentials expire

## Sensors

| Type | Unit | Device Class |
|------|------|--------------|
| Cold Water | m³ | `water` |
| Hot Water | m³ | `water` |
| Heat | — | — |

Each sensor also exposes the following attributes: `serial_number`, `room`, `last_seen_ms`.

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS.
2. Install **INMES** from the HACS integrations list.
3. Restart Home Assistant.

### Manual

1. Copy `custom_components/inmes` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **INMES**.
3. Enter your INMES account email and password.

## Requirements

- Home Assistant 2023.x or newer
- An active INMES account (https://app.inmes.cz)
