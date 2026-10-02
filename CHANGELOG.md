# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1] - 2026-10-02

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
