"""Support for Yale Lock."""
from __future__ import annotations

import asyncio

from homeassistant.components.lock import LockEntity
from homeassistant.const import (
    ATTR_CODE,
    CONF_CODE,
    STATE_LOCKED,
    STATE_UNAVAILABLE,
    STATE_UNLOCKED,
)
from homeassistant.helpers.entity import DeviceInfo
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
        self._state = self.check_lock(key["status1"], key["minigw_lock_status"])
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
            expected = 1
        elif state == "unlock":
            lock_state = await self.hass.async_add_executor_job(
                self.coordinator._yale.lock_api.open_lock,  # type: ignore[attr-defined]
                get_lock,
                code,
            )
            expected = 2

        LOGGER.debug("Yale doorlock %s", state)
        transaction = None
        attempts = 0
        while lock_state is not True and transaction != expected:
            transaction = await self.hass.async_add_executor_job(
                self.coordinator._yale.lock_api.get(self._name).state._value_  # type: ignore[attr-defined]
            )
            attempts += 1
            if attempts == 30:
                break
            if attempts > 1:
                await asyncio.sleep(0.5)
        if state == transaction:
            self._state = state

    def check_lock(self, status1, status2):
        """Get state for locks."""
        state = status1
        lock_status_str = status2
        if lock_status_str != "":
            lock_status = int(lock_status_str, 16)
            closed = (lock_status & 16) == 16
            locked = (lock_status & 1) == 1
            if closed is True and locked is True:
                state = STATE_LOCKED
            elif closed is True and locked is False:
                state = STATE_UNLOCKED
            elif not closed:
                state = STATE_UNLOCKED
        elif "device_status.lock" in state:
            state = STATE_LOCKED
        elif "device_status.unlock" in state:
            state = STATE_UNLOCKED
        else:
            state = STATE_UNAVAILABLE
        return state
