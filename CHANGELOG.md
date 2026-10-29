# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.4.0] - 2026-10-29

### Added

- Exchanger cleaning interval setting (`clean_exch_kg`, kilograms of pellets between cleanings).

### Changed

- The exchanger cleaning alarm (`alarm_clean_exch`) is named "Exchanger cleaning due", shows the
  pellets burnt since cleaning and the interval as attributes, and its message, translated instead
  of the controller's Polish-only label, says that acknowledging the alarms resets the counter.
  New installations get the entity id `binary_sensor.<device>_exchanger_cleaning_due`; existing
  ones keep theirs.
- The cleaning mechanism alarm (`alarm_clwym`) is named "Exchanger cleaning mechanism lock"
  instead of sharing the name of the exchanger cleaning output.

## [1.3.0] - 2026-10-15

### Added

- Operating mode select (manual, automatic). It writes `tryb_auto`, which the controller never
  reports, and shows the state from `tryb_auto_state`; during an alarm the select is unknown.
- Switches for every power output (pumps, feeder, stoker, fan, igniter, auxiliary output, burner
  and exchanger cleaning) and a mixing valve action select, available only in manual mode. The
  binary sensors of the outputs stay as they were.
- Regulation settings as configuration entities: boiler, hot water and mixing valve reductions,
  hot water, buffer and room hysteresis, boiler and mixing valve weather control with their
  heating curves, auto summer threshold and hysteresis, heating pumps start temperature. They
  replace the disabled read-only sensors of the same registers.

## [1.2.0] - 2026-10-13

### Added

- `pello.add_fuel` action recording a hopper refill (`add_fuel`, in kilograms). It fails when the
  controller does not stamp a new last refuel time, so automations can rely on its success.

## [1.1.0] - 2026-10-09

### Added

- Room heating demand binary sensor for circuit 1 (`ob1_pok_heat`, missing from the controller's
  register dictionary). While it is off, the controller lowers the mixing valve setpoint by its
  reduction setting.

## [1.0.2] - 2026-10-04

### Changed

- `defusedxml` is required as `>=0.7.1` instead of an exact pin, so it follows the version
  Home Assistant ships.
- HACS and hassfest validation run on every push, pull request and daily.

## [1.0.1] - 2026-10-04

### Fixed

- The burner power register (`pl_power`) is shown as a power stage (off, minimum, intermediate,
  maximum, as named in the controller manual) instead of a percentage of 0–3%. Existing
  installations keep the old entity ID `…_burner_power_level`; its percentage statistics stop.

## [1.0.0] - 2026-10-02

### Added

- Config flow with reauthentication, reconfiguration and options (polling interval, read-only
  mode).
- Sensors and binary sensors built from the controller's register dictionary; a curated set
  enabled by default with English and Polish translations.
- Numbers, selects and buttons for a reviewed list of settings; every other register is read-only.
- Alarm summary binary sensor listing all active alarms.
- Devices for the controller and for each paired radio node.
- Diagnostics with credentials and identifiers redacted.
- Brand icon and an example dashboard.
