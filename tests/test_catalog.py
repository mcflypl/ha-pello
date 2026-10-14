"""Tests for the rules turning registers into entities."""

import pytest
from homeassistant.const import EntityCategory, Platform

from custom_components.pello.catalog import (
    CONTROL_PLATFORMS,
    CURATED,
    active_nodes,
    build_specs,
)
from custom_components.pello.models import DeviceValues, Snapshot
from custom_components.pello.parser import parse_dictionary, parse_snapshot

from . import load_fixture

ROOT = 0
USER = 2


@pytest.fixture(scope="module")
def dictionary():
    return parse_dictionary(load_fixture("hardware.xml"))


@pytest.fixture(scope="module")
def snapshot():
    return parse_snapshot(load_fixture("syncvalues.txt"))


def specs_by_tid(dictionary, snapshot, access_level=ROOT, read_only=False, vid=0):
    """Entities of one slot by register, leaving out the manual controls of power outputs."""
    specs = build_specs(dictionary, snapshot, access_level, read_only)
    return {
        spec.register.tid: spec
        for spec in specs
        if spec.vid == vid and not (spec.curated and spec.curated.manual_only)
    }


def manual_controls(dictionary, snapshot, access_level=ROOT, read_only=False):
    specs = build_specs(dictionary, snapshot, access_level, read_only)
    return {spec.register.tid: spec for spec in specs if spec.curated and spec.curated.manual_only}


def with_values(snapshot, vid, **values):
    device = snapshot.devices.get(vid, DeviceValues(vid=vid, timestamp=1, values={}))
    changed = DeviceValues(vid, device.timestamp, {**device.values, **values})
    return Snapshot(devices={**snapshot.devices, vid: changed})


def test_curated_temperature_is_an_enabled_sensor(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["tkot_value"]

    assert spec.platform is Platform.SENSOR
    assert spec.key == "water_temperature"
    assert spec.enabled
    assert spec.category is None


def test_every_curated_register_exists_on_the_controller(dictionary, snapshot):
    specs = specs_by_tid(dictionary, snapshot)

    assert set(CURATED) - set(specs) == set()


def test_curated_keys_are_unique_within_a_platform():
    keys = [(curated.platform, curated.key) for curated in CURATED.values()]

    assert len(keys) == len(set(keys))


def test_setpoint_is_a_number_for_root(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["kot_tzad"]

    assert spec.platform is Platform.NUMBER
    assert spec.key == "setpoint"
    assert spec.enabled


def test_only_reviewed_registers_can_change_the_controller(dictionary, snapshot):
    """Adding a control means extending this list on purpose."""
    controls = {
        spec.register.tid: spec.platform
        for spec in build_specs(dictionary, snapshot, ROOT, read_only=False)
        if spec.platform in CONTROL_PLATFORMS
    }

    assert controls == {
        "kot_tzad": Platform.NUMBER,
        "cwu_tzad": Platform.NUMBER,
        "tank_tzad": Platform.NUMBER,
        "ob1_tzad": Platform.NUMBER,
        "ob1_pok_lo": Platform.NUMBER,
        "ob1_pok_norm": Platform.NUMBER,
        "ob1_pok_hi": Platform.NUMBER,
        "kot_tobn": Platform.NUMBER,
        "pog_en": Platform.SWITCH,
        "pog_krzyw1": Platform.NUMBER,
        "pog_krzyw2": Platform.NUMBER,
        "cwu_tobn": Platform.NUMBER,
        "cwu_hist1": Platform.NUMBER,
        "cwu_hist2": Platform.NUMBER,
        "tank_hist": Platform.NUMBER,
        "ob1_tobn": Platform.NUMBER,
        "ob1_pog_en": Platform.SWITCH,
        "ob1_pog_krzyw1": Platform.NUMBER,
        "ob1_pog_krzyw2": Platform.NUMBER,
        "ob1_pok_hist": Platform.NUMBER,
        "autolato_tzew": Platform.NUMBER,
        "autolato_hist": Platform.NUMBER,
        "pomp_co_ton": Platform.NUMBER,
        "tryb_auto": Platform.SELECT,
        "zima_lato": Platform.SELECT,
        "cwu_state": Platform.SELECT,
        "cmd_ackalarm": Platform.BUTTON,
        "cmd_reset": Platform.BUTTON,
        "out_pomp1": Platform.SWITCH,
        "out_pomp2": Platform.SWITCH,
        "out_cwu": Platform.SWITCH,
        "out_miesz": Platform.SWITCH,
        "out_tank": Platform.SWITCH,
        "out_pod": Platform.SWITCH,
        "out_dm": Platform.SWITCH,
        "out_aux": Platform.SWITCH,
        "out_clean_wym": Platform.SWITCH,
        "mpl_feed": Platform.SWITCH,
        "mpl_heat": Platform.SWITCH,
        "mpl_clean": Platform.SWITCH,
        "out_zaw4d": Platform.SELECT,
    }


def test_setpoint_stays_visible_when_access_level_cannot_write(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot, access_level=USER)["kot_tzad"]

    assert spec.platform is Platform.SENSOR
    assert spec.key == "setpoint"
    assert spec.enabled
    assert spec.curated.device_class == "temperature"


def test_mode_stays_visible_as_enum_sensor_in_read_only_mode(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot, read_only=True)["zima_lato"]

    assert spec.platform is Platform.SENSOR
    assert spec.key == "season_mode"
    assert spec.curated.device_class == "enum"
    assert spec.curated.options["2"] == "auto_summer"


def test_read_only_mode_creates_no_controls(dictionary, snapshot):
    specs = build_specs(dictionary, snapshot, ROOT, read_only=True)

    assert {spec.platform for spec in specs} == {Platform.SENSOR, Platform.BINARY_SENSOR}


@pytest.mark.parametrize(
    "tid",
    [
        "kot_hist",
        "zaw4d_hist",
        "exh_fan_mode",
        "exh_fan_speed",
        "en_ext_out",
        "pomp_ext_func",
        "typ_kotla",
        "tryb_auto_state",
        "time_to_empty",
        "out_pomp1",
        "out_pod",
        "mpl_feed",
        "mpl_heat",
        "pl_flame_b",
    ],
)
def test_writable_register_outside_the_reviewed_set_is_read_only(dictionary, snapshot, tid):
    register = dictionary.registers_for(0)[tid]
    spec = specs_by_tid(dictionary, snapshot)[tid]

    assert register.access(ROOT) == "w"
    assert spec.platform in (Platform.SENSOR, Platform.BINARY_SENSOR)


def test_uncurated_register_is_a_disabled_diagnostic_sensor(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["kot_hist"]

    assert spec.key == "kot_hist"
    assert not spec.enabled
    assert spec.category is EntityCategory.DIAGNOSTIC


def test_curated_entry_is_ignored_when_the_dictionary_redefines_the_register(snapshot):
    redefined = parse_dictionary(
        load_fixture("hardware.xml").replace(
            '<register tid="kot_tzad" priv="wwrww" type="float"',
            '<register tid="kot_tzad" priv="wwrww" type="enum"',
        )
    )

    spec = specs_by_tid(redefined, snapshot)["kot_tzad"]

    assert spec.platform is Platform.SENSOR
    assert spec.curated is None


def test_power_output_is_a_running_binary_sensor(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["out_pomp1"]

    assert spec.platform is Platform.BINARY_SENSOR
    assert spec.curated.device_class == "running"


def test_alarm_is_an_enabled_diagnostic_binary_sensor(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["alarm_stb"]

    assert spec.platform is Platform.BINARY_SENSOR
    assert spec.enabled
    assert spec.category is EntityCategory.DIAGNOSTIC


def test_credentials_identity_and_network_never_become_entities(dictionary, snapshot):
    tids = set(specs_by_tid(dictionary, snapshot))

    assert not [tid for tid in tids if tid.startswith(("auth_", "eth_", "device_"))]
    assert "datetime" not in tids


def test_schedules_and_strings_are_skipped(dictionary, snapshot):
    tids = set(specs_by_tid(dictionary, snapshot))

    assert "kot_prog" not in tids
    assert "pod_run_time_str" not in tids


def test_registers_of_unused_heating_circuits_are_skipped(dictionary, snapshot):
    tids = set(specs_by_tid(dictionary, snapshot))

    assert "ob1_pok_lo" in tids
    assert not [tid for tid in tids if tid.startswith(("ob2_", "ob3_", "ob6_"))]


def test_registers_of_a_configured_heating_circuit_appear(dictionary, snapshot):
    tids = set(specs_by_tid(dictionary, with_values(snapshot, 0, ob2_typ="1")))

    assert "ob2_tzad" in tids
    assert "ob3_tzad" not in tids


def test_hopper_calibration_is_not_presented_as_a_countdown(dictionary, snapshot):
    """time_to_empty is the feeder runtime that empties a full hopper, a setting."""
    spec = specs_by_tid(dictionary, snapshot)["time_to_empty"]

    assert spec.curated is None
    assert not spec.enabled


def test_register_missing_from_the_values_is_skipped(dictionary, snapshot):
    assert "cwu_hist1" in specs_by_tid(dictionary, snapshot)

    device = snapshot.devices[0]
    values = {tid: value for tid, value in device.values.items() if tid != "cwu_hist1"}
    missing = Snapshot(devices={**snapshot.devices, 0: DeviceValues(0, device.timestamp, values)})

    assert "cwu_hist1" not in specs_by_tid(dictionary, missing)


def test_temperature_difference_is_not_converted_like_a_temperature(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["tank_hist"]

    assert spec.platform is Platform.NUMBER
    assert spec.key == "buffer_hysteresis"
    assert spec.curated.device_class is None
    assert spec.curated.unit == "°C"
    assert spec.category is EntityCategory.CONFIG


def test_settings_that_cannot_be_written_keep_their_kind(dictionary, snapshot):
    specs = specs_by_tid(dictionary, snapshot, read_only=True)

    assert specs["pog_en"].platform is Platform.BINARY_SENSOR
    assert specs["pog_en"].key == "boiler_weather_control"
    assert specs["tank_hist"].platform is Platform.SENSOR
    assert specs["tank_hist"].curated.device_class is None
    assert specs["pog_krzyw1"].curated.device_class == "temperature"


def test_operating_mode_is_written_to_one_register_and_read_from_another(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["tryb_auto"]

    assert "tryb_auto" not in snapshot.devices[0].values
    assert spec.platform is Platform.SELECT
    assert spec.key == "operating_mode"
    assert spec.state_tid == "tryb_auto_state"
    assert spec.curated.options == {"0": "manual", "1": "automatic"}


def test_operating_mode_control_disappears_when_it_cannot_be_written(dictionary, snapshot):
    specs = specs_by_tid(dictionary, snapshot, read_only=True)

    assert "tryb_auto" not in specs
    assert specs["tryb_auto_state"].key == "operating_mode"


def test_power_outputs_get_manual_controls_beside_their_sensors(dictionary, snapshot):
    controls = manual_controls(dictionary, snapshot)
    sensors = specs_by_tid(dictionary, snapshot)

    assert controls["out_pomp1"].platform is Platform.SWITCH
    assert controls["out_pomp1"].key == sensors["out_pomp1"].key == "pump_1"
    assert sensors["out_pomp1"].platform is Platform.BINARY_SENSOR
    assert controls["out_zaw4d"].platform is Platform.SELECT
    assert sensors["out_zaw4d"].platform is Platform.SENSOR


def test_power_outputs_have_no_controls_in_read_only_mode(dictionary, snapshot):
    assert manual_controls(dictionary, snapshot, read_only=True) == {}
    assert manual_controls(dictionary, snapshot, access_level=USER) == {}


def test_undocumented_register_gets_a_handwritten_definition(dictionary, snapshot):
    spec = specs_by_tid(dictionary, snapshot)["clean_act_kg"]

    assert spec.key == "pellets_since_cleaning"
    assert spec.register.unit == "kg"


def test_acknowledge_button_needs_execute_access(dictionary, snapshot):
    assert specs_by_tid(dictionary, snapshot)["cmd_ackalarm"].platform is Platform.BUTTON
    assert "cmd_ackalarm" not in specs_by_tid(dictionary, snapshot, access_level=USER)
    assert "cmd_ackalarm" not in specs_by_tid(dictionary, snapshot, read_only=True)


def test_destructive_commands_are_not_offered(dictionary, snapshot):
    assert "cmd_formatsdcard" not in specs_by_tid(dictionary, snapshot)


def test_only_paired_radio_nodes_are_active(dictionary, snapshot):
    assert active_nodes(dictionary, snapshot) == [85]


def test_radio_sensor_exposes_measurements_but_not_its_identity(dictionary, snapshot):
    specs = specs_by_tid(dictionary, snapshot, vid=85)

    assert set(specs) == {"temp", "rh", "bat", "sig", "alarm"}
    assert specs["temp"].key == "temperature"
    assert specs["bat"].category is EntityCategory.DIAGNOSTIC


def test_room_becomes_active_once_it_is_named(dictionary, snapshot):
    named = with_values(snapshot, 100, name="Salon")

    assert active_nodes(dictionary, named) == [85, 100]
    assert specs_by_tid(dictionary, named, vid=100)["t_norm"].platform is Platform.SENSOR
