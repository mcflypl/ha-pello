"""Actions of the Pello integration."""

from __future__ import annotations

from typing import Final

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, MAIN_VID
from .coordinator import PelloConfigEntry
from .models import ACCESS_WRITE

SERVICE_ADD_FUEL: Final = "add_fuel"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_AMOUNT: Final = "amount"

# The controller treats a write of the refuel amount as a full hopper and stamps the time.
REGISTER_ADD_FUEL: Final = "add_fuel"
REGISTER_LAST_REFUEL: Final = "add_fuel_time"

ADD_FUEL_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_AMOUNT): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)


def _loaded_entry(hass: HomeAssistant, entry_id: str) -> PelloConfigEntry:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(f"Pello controller {entry_id} is not loaded")
    return entry


async def _async_add_fuel(call: ServiceCall) -> None:
    coordinator = _loaded_entry(call.hass, call.data[ATTR_CONFIG_ENTRY_ID]).runtime_data
    amount: int = call.data[ATTR_AMOUNT]

    register = coordinator.dictionary.registers_for(MAIN_VID).get(REGISTER_ADD_FUEL)
    if register is None or register.access(coordinator.access_level) != ACCESS_WRITE:
        raise ServiceValidationError("Refuelling is not allowed for this controller account")
    minimum, maximum = register.minimum, register.maximum
    if minimum is not None and maximum is not None and not minimum <= amount <= maximum:
        raise ServiceValidationError(
            f"Refuel amount {amount} kg is outside {minimum:g}-{maximum:g} kg"
        )

    last_refuel = coordinator.data.value(MAIN_VID, REGISTER_LAST_REFUEL)
    await coordinator.async_write(MAIN_VID, REGISTER_ADD_FUEL, str(amount))
    if not coordinator.last_update_success:
        raise HomeAssistantError("Could not read back whether the controller recorded the refuel")
    # An accepted write only proves the amount was stored; a new timestamp proves the refuel.
    if coordinator.data.value(MAIN_VID, REGISTER_LAST_REFUEL) == last_refuel:
        raise HomeAssistantError("The controller did not record the refuel")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions of the integration."""
    hass.services.async_register(DOMAIN, SERVICE_ADD_FUEL, _async_add_fuel, ADD_FUEL_SCHEMA)
