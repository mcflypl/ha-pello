"""Binary sensors of the Pello integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.translation import async_get_cached_translations
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalog import TYPE_ALARM, EntitySpec
from .const import DOMAIN, MAIN_VID
from .coordinator import PelloConfigEntry, PelloCoordinator
from .entity import PelloEntity, to_number
from .models import RegisterDef, RegisterOption

ALARM_SUMMARY_KEY = "alarm"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PelloConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create binary sensors for outputs, inputs and alarms."""
    coordinator = entry.runtime_data
    specs = coordinator.specs_for(Platform.BINARY_SENSOR)
    alarms = [spec for spec in specs if spec.register.type == TYPE_ALARM]
    describer = AlarmDescriber(hass, coordinator)
    entities: list[BinarySensorEntity] = [
        PelloAlarm(coordinator, spec, describer)
        if spec.register.type == TYPE_ALARM
        else PelloBinarySensor(coordinator, spec)
        for spec in specs
    ]
    entities.append(PelloAlarmSummary(coordinator, alarms, describer))
    async_add_entities(entities)


def alarm_messages(
    register: RegisterDef, raw: str | None, label: Callable[[RegisterOption], str]
) -> list[str]:
    """Decode an alarm bit mask into the messages of the bits that are set."""
    mask = to_number(raw)
    if not isinstance(mask, int) or mask == 0:
        return []
    messages = [
        label(option)
        for option in register.options
        if option.id.isdigit() and mask & int(option.id)
    ]
    return messages or [str(mask)]


def alarm_attributes(coordinator: PelloCoordinator, spec: EntitySpec) -> dict[str, Any]:
    """Read the registers a curated alarm shows next to its messages."""
    if spec.curated is None or not spec.curated.attributes:
        return {}
    return {
        name: to_number(coordinator.data.value(spec.vid, tid))
        for name, tid in spec.curated.attributes.items()
    }


class AlarmDescriber:
    """Names and messages of alarms, from the translations when the alarm is curated."""

    def __init__(self, hass: HomeAssistant, coordinator: PelloCoordinator) -> None:
        self._coordinator = coordinator
        self._language = coordinator.language
        # The entity platform loads them before it sets up the platform.
        self._translations = async_get_cached_translations(hass, self._language, "entity", DOMAIN)

    def _translation(self, key: str, path: str) -> str | None:
        return self._translations.get(
            f"component.{DOMAIN}.entity.{Platform.BINARY_SENSOR}.{key}.{path}"
        )

    def name(self, spec: EntitySpec) -> str:
        """Return the alarm name for the summary."""
        if spec.curated is not None and (name := self._translation(spec.curated.key, "name")):
            return name
        return spec.register.name(self._language)

    def messages(self, spec: EntitySpec) -> list[str]:
        """Return the messages of the active conditions of an alarm."""
        raw = self._coordinator.data.value(spec.vid, spec.register.tid)
        curated = spec.curated
        if curated is None or not curated.options:
            return alarm_messages(spec.register, raw, lambda option: option.label(self._language))
        options = curated.options

        def label(option: RegisterOption) -> str:
            state = options.get(option.id)
            path = f"state_attributes.messages.state.{state}"
            if state is None or (message := self._translation(curated.key, path)) is None:
                return option.label(self._language)
            return message

        return alarm_messages(spec.register, raw, label)


class PelloBinarySensor(PelloEntity, BinarySensorEntity):
    """An on/off register: a power output or a binary input."""

    def __init__(self, coordinator: PelloCoordinator, spec: EntitySpec) -> None:
        super().__init__(coordinator, spec)
        if spec.curated is not None:
            self._attr_device_class = spec.curated.device_class

    @property
    def is_on(self) -> bool | None:
        """Return True for any non-zero value; some outputs report several active states."""
        value = to_number(self.raw)
        return None if value is None else value != 0


class PelloAlarm(PelloEntity, BinarySensorEntity):
    """An alarm register: a bit mask of active alarm conditions."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, coordinator: PelloCoordinator, spec: EntitySpec, describer: AlarmDescriber
    ) -> None:
        super().__init__(coordinator, spec)
        self._describer = describer

    @property
    def is_on(self) -> bool | None:
        """Return True when any alarm bit is set."""
        value = to_number(self.raw)
        return None if value is None else value != 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Describe the alarm conditions that are active."""
        return {
            "messages": self._describer.messages(self._spec),
            **alarm_attributes(self.coordinator, self._spec),
        }


class PelloAlarmSummary(CoordinatorEntity[PelloCoordinator], BinarySensorEntity):
    """Tells whether any alarm of the controller or its radio nodes is active."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = ALARM_SUMMARY_KEY

    def __init__(
        self, coordinator: PelloCoordinator, alarms: list[EntitySpec], describer: AlarmDescriber
    ) -> None:
        super().__init__(coordinator)
        self._alarms = alarms
        self._describer = describer
        self._attr_unique_id = coordinator.unique_id(MAIN_VID, ALARM_SUMMARY_KEY)
        self._attr_device_info = coordinator.device_info(MAIN_VID)

    @property
    def suggested_object_id(self) -> str | None:
        """Keep the entity id in English."""
        return ALARM_SUMMARY_KEY

    def _active(self) -> list[str]:
        active: list[str] = []
        for spec in self._alarms:
            name = self._describer.name(spec)
            active.extend(f"{name}: {message}" for message in self._describer.messages(spec))
        return active

    @property
    def is_on(self) -> bool:
        """Return True when at least one alarm is active."""
        return bool(self._active())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List the active alarms."""
        return {"active": self._active()}
