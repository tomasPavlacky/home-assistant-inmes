"""INMES sensor entities — one per active meter."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TYPE_OF_USE
from .coordinator import InmesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InmesCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        InmesSensor(coordinator, meter_guid, meter)
        for meter_guid, meter in coordinator.data.items()
    )


class InmesSensor(CoordinatorEntity[InmesCoordinator], SensorEntity):
    """Represents a single INMES meter as a Home Assistant sensor."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: InmesCoordinator,
        meter_guid: str,
        meter: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._meter_guid = meter_guid
        self._serial = meter["serialNumber"]

        type_info = TYPE_OF_USE.get(meter.get("typeOfUse", 0), {})
        type_name = type_info.get("name", "Meter")

        self._attr_unique_id = f"inmes_{self._serial}"
        self._attr_name = f"INMES {type_name} {self._serial}"
        self._attr_native_unit_of_measurement = type_info.get("unit")
        self._attr_device_class = type_info.get("device_class")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.unit_guid)},
            name=coordinator.unit_name,
            manufacturer="INMES",
            model="Smart Meter",
        )

    @property
    def _meter(self) -> dict[str, Any] | None:
        return self.coordinator.data.get(self._meter_guid)

    @property
    def native_value(self) -> float | None:
        meter = self._meter
        if not meter:
            return None
        states = meter.get("states", [])
        if not states:
            return None
        return states[0].get("value")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._meter is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meter = self._meter or {}
        last_seen = meter.get("lastSeen")
        return {
            "serial_number": self._serial,
            "room": meter.get("roomName"),
            "last_seen_ms": last_seen,
        }
