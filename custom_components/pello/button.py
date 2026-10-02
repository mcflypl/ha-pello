"""Commands of the Pello integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PelloConfigEntry
from .entity import PelloEntity

COMMAND_RUN = "1"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PelloConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create a button for every supported command."""
    coordinator = entry.runtime_data
    async_add_entities(
        PelloButton(coordinator, spec) for spec in coordinator.specs_for(Platform.BUTTON)
    )


class PelloButton(PelloEntity, ButtonEntity):
    """A command register of the controller."""

    async def async_press(self) -> None:
        """Run the command."""
        await self.coordinator.async_write(self._vid, self._register.tid, COMMAND_RUN)
