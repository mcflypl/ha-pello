# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
