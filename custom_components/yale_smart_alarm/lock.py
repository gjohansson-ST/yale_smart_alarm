"""Support for Yale Lock."""
from __future__ import annotations

from homeassistant.components.lock import LockEntity
from homeassistant.const import (
    ATTR_CODE,
    CONF_CODE,
    STATE_LOCKED,
    STATE_UNAVAILABLE,
    STATE_UNLOCKED,
)
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .coordinator import YaleDataUpdateCoordinator


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the lock platform."""

    return True


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the lock entry."""
    coordinator: YaleDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    async_add_entities(
        YaleDoorlock(coordinator, key) for key in coordinator.data["locks"]
    )

    return True


class YaleDoorlock(CoordinatorEntity, LockEntity):
    """Representation of a Yale doorlock."""

    def __init__(self, coordinator: YaleDataUpdateCoordinator, key: dict):
        """Initialize the Yale Alarm Device."""
        self._state = STATE_UNAVAILABLE
        self.coordinator = coordinator
        self._name = key["name"]
        self._address = key["address"].replace(":", "")
        self._state = STATE_UNAVAILABLE
        self._key = key
        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return self._address

    @property
    def device_info(self) -> Mapping[str, Any] | None:
        """Return device information about this entity."""
        return {
            "name": self._name,
            "manufacturer": "Yale",
            "model": "main",
            "identifiers": {(DOMAIN, self._address)},
            "via_device": (DOMAIN, "yale_smart_living"),
        }

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def is_locked(self):
        """Return if locked."""
        return self._state == STATE_LOCKED

    @property
    def code_format(self) -> str:
        """Return the required six digit code."""
        return "^\\d{6}$"

    async def async_unlock(self, **kwargs) -> None:
        """Send unlock command."""
        code = kwargs.get(ATTR_CODE, self.coordinator._entry.data.get(CONF_CODE))  # type: ignore[attr-defined]
        if code is None:
            LOGGER.error("Code required but none provided")
            return

        await self.async_set_lock_state(code, "unlock")

    async def async_lock(self, **kwargs) -> None:
        """Send lock command."""
        code = ""
        await self.async_set_lock_state(code, "lock")

    async def async_set_lock_state(self, code: str, state: str) -> None:
        """Send set lock state command."""
        get_lock = await self.hass.async_add_executor_job(
            self.coordinator._yale.lock_api.get, self._name  # type: ignore[attr-defined]
        )
        if state == "lock":

            lock_state = await self.hass.async_add_executor_job(
                self.coordinator._yale.lock_api.close_lock,  # type: ignore[attr-defined]
                get_lock,
            )
        elif state == "unlock":
            lock_state = await self.hass.async_add_executor_job(
                self.coordinator._yale.lock_api.open_lock,  # type: ignore[attr-defined]
                get_lock,
                code,
            )

        LOGGER.debug("Yale doorlock %s", state)

        if lock_state:
            if state == "lock":
                self._state = STATE_LOCKED
            elif state == "unlock":
                self._state = STATE_UNLOCKED

        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for lock in self.coordinator.data["locks"]:
            if lock["address"].replace(":", "") == self._address:
                self._state = lock["_state"]
        super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
