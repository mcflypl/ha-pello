"""Tests for the actions of the integration."""

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pello.const import CONF_READ_ONLY, DOMAIN

from . import write_response
from .conftest import BASE

NEW_REFUEL = "1790950000"


async def add_fuel(hass, entry_id, amount):
    await hass.services.async_call(
        DOMAIN,
        "add_fuel",
        {"config_entry_id": entry_id, "amount": amount},
        blocking=True,
    )


async def test_refuel_writes_the_amount_in_kilograms(hass, controller, loaded):
    controller.set("add_fuel_time", NEW_REFUEL)
    controller.expect_write("device=0&add_fuel=45", write_response("add_fuel"))

    await add_fuel(hass, loaded.entry_id, 45)

    assert controller.writes == ["device=0&add_fuel=45"]


async def test_refuel_with_the_previous_amount_is_written_again(hass, controller, loaded):
    controller.set("add_fuel_time", NEW_REFUEL)
    controller.expect_write("device=0&add_fuel=60", write_response("add_fuel"))

    await add_fuel(hass, loaded.entry_id, 60)

    assert controller.writes == ["device=0&add_fuel=60"]


async def test_refuel_not_recorded_by_the_controller_is_reported(hass, controller, loaded):
    controller.expect_write("device=0&add_fuel=60", write_response("add_fuel"))

    with pytest.raises(HomeAssistantError, match="did not record"):
        await add_fuel(hass, loaded.entry_id, 60)


async def test_amount_outside_the_controller_range_is_rejected_locally(hass, controller, loaded):
    with pytest.raises(ServiceValidationError, match="1-200"):
        await add_fuel(hass, loaded.entry_id, 201)

    assert controller.writes == []


async def test_refused_refuel_is_reported(hass, controller, loaded):
    controller.expect_write("device=0&add_fuel=60", write_response("add_fuel", "access_denied"))

    with pytest.raises(HomeAssistantError, match="access_denied"):
        await add_fuel(hass, loaded.entry_id, 60)


async def test_refuel_needs_write_access(hass, controller, entry):
    controller.set("accesslevel", "2")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(ServiceValidationError, match="not allowed"):
        await add_fuel(hass, entry.entry_id, 60)

    assert controller.writes == []


async def test_refuel_is_refused_in_read_only_mode(hass, controller, entry):
    hass.config_entries.async_update_entry(entry, options={CONF_READ_ONLY: True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError, match="read-only"):
        await add_fuel(hass, entry.entry_id, 60)

    assert controller.writes == []


async def test_refuel_of_an_unloaded_controller_is_rejected(hass, controller, loaded):
    await hass.config_entries.async_unload(loaded.entry_id)

    with pytest.raises(ServiceValidationError, match="not loaded"):
        await add_fuel(hass, loaded.entry_id, 60)


async def test_refuel_of_another_integration_is_rejected(hass, loaded):
    other = MockConfigEntry(domain="other")
    other.add_to_hass(hass)

    with pytest.raises(ServiceValidationError, match="not loaded"):
        await add_fuel(hass, other.entry_id, 60)


async def test_refuel_that_cannot_be_read_back_is_reported(hass, aioclient_mock, loaded):
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{BASE}/setregister.cgi?device=0&add_fuel=60", text=write_response("add_fuel")
    )
    aioclient_mock.get(f"{BASE}/syncvalues.cgi", status=500)

    with pytest.raises(HomeAssistantError, match="read back"):
        await add_fuel(hass, loaded.entry_id, 60)
