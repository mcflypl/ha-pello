"""On/off settings and power outputs of the Pello integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PelloConfigEntry
from .entity import PelloEntity, to_number

VALUE_ON = "1"
VALUE_OFF = "0"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PelloConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create a switch for every on/off setting and power output the account may change."""
    coordinator = entry.runtime_data
    async_add_entities(
        PelloSwitch(coordinator, spec) for spec in coordinator.specs_for(Platform.SWITCH)
    )


class PelloSwitch(PelloEntity, SwitchEntity):
    """An on/off register; power outputs are available only in manual mode."""

    @property
    def is_on(self) -> bool | None:
        """Return True for any non-zero value; burner cleaning reports two active states."""
        value = to_number(self.raw)
        return None if value is None else value != 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Write the on value."""
        await self.coordinator.async_write(self._vid, self._register.tid, VALUE_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Write the off value."""
        await self.coordinator.async_write(self._vid, self._register.tid, VALUE_OFF)
