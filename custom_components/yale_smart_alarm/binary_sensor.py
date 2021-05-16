"""Support for Yale binary sensors."""
from __future__ import annotations

from homeassistant.components.binary_sensor import DEVICE_CLASS_DOOR, BinarySensorEntity
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YaleDataUpdateCoordinator


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the binary_sensor platform."""

    return True


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the binary sensor entry."""
    coordinator: YaleDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    async_add_entities(
        YaleDoorWindowSensor(coordinator, key)
        for key in coordinator.data["door_windows"]
    )

    return True


class YaleDoorWindowSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Yale door window sensor."""

    def __init__(self, coordinator: YaleDataUpdateCoordinator, key: dict):
        """Initialize Yale door window sensor."""
        self._name = key["name"]
        self._address = key["address"].replace(":", "")
        self._state = STATE_UNAVAILABLE
        self._key = key
        self.coordinator = coordinator
        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return f"{self._address}_door_window"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return {
            "name": self._name,
            "manufacturer": "Yale",
            "model": "main",
            "identifiers": {(DOMAIN, self._address)},
            "via_device": (DOMAIN, "yale_smart_living"),
        }

    @property
    def device_class(self) -> str:
        """Return the class of this entity."""
        return DEVICE_CLASS_DOOR

    @property
    def is_on(self) -> bool:
        """Return the state of the sensor."""
        return self._state == "open"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for door_window in self.coordinator.data["door_windows"]:
            if door_window["address"].replace(":", "") == self._address:
                self._state = door_window["_state"]
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
