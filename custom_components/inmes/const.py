"""Constants for the INMES integration."""
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass

DOMAIN = "inmes"

BASE_URL = "https://app.inmes.cz"
API_BASE = BASE_URL + "/ng/api/up"
API_V2 = API_BASE + "/v2"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

UPDATE_INTERVAL = timedelta(hours=3)

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# typeOfUse → sensor metadata
TYPE_OF_USE = {
    1: {
        "name": "Cold Water",
        "unit": "m³",
        "device_class": SensorDeviceClass.WATER,
    },
    2: {
        "name": "Hot Water",
        "unit": "m³",
        "device_class": SensorDeviceClass.WATER,
    },
    3: {
        "name": "Heat",
        "unit": None,
        "device_class": None,
    },
}
