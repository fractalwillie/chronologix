# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.5.0] - 2025-05-13
### Added

- Time-based log deletion via new cleanup.py module and `retain` config option

    - Automatically removes old log folders based on defined retention interval

    - Supports minutes (m), hours (h), days (d), and weeks (w)

    - Configurable like `retain="1h"` or `retain="2d"`

    - New derived field: `retain_timedelta`

    - Cleanup runs after every rollover

- Safeguard: `retain` must be equal to or longer than rollover `interval`

    - Prevents accidental deletion of active log folders

    - Raises a LogConfigError on misconfiguration

### Changed

- Updated README with full documentation of `retain`

    - Added to Features list, Usage example, Time-based log deletion section, and Default config

---

## [0.4.0] - 2025-05-12
### Added

- Terminal output support via `cli_echo`

    - Supports both simple and advanced formats

    - Simple: `{"enabled": True, "min_level": "INFO"}`

    - Advanced: `{"stdout": {"min_level": ...}, "stderr": {"min_level": ...}}`

    - Routes messages to `stdout` or `stderr` based on severity

    - Clean fallback: `stderr` takes precedence if message qualifies for both

- Validation for misconfigured or incomplete `cli_echo` configs

- Early skip optimization to avoid unnecessary CLI checks when disabled

### Changed

- README updated with new usage examples, explanation of terminal output, and default config changes

- Added inline comments for clarity around new config and routing logic

---

## [0.3.0] - 2025-05-10
### Changed

- Major refactor of core architecture

    - Replaced old `log_streams`, `mirror_map`, and `min_log_levels` config structure

    - Introduced new unified `sinks` and `mirror` config interface

    - `logger.log()` no longer requires target sink, routing is now based entirely on log level and thresholds

- Improved log level support

    - Explicit and implicit logging now fully normalized (`.log(level=...)`, `.error(...)`, or no level at all)

    - `NOTSET` is retained as the default for untyped logs

### Added

- Expanded README with new usage patterns and configuration examples

### Removed

- Legacy `log_streams`, `mirror_map`, and `min_log_levels` arguments

- Multi-mirror logic (replaced by a single global `mirror` with level threshold)

---

## [0.2.1] - 2025-05-08
### Changed

- Expanded README with usage examples and config updates for log level support

- Added log level filtering to default config section

- Added log levels to feature list

---

## [0.2.0] - 2025-05-08
### Added

- Per-stream log level filtering via min_log_levels

- Support for log levels: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL

- Logs without levels are still supported and excluded from filtering

- Flat mirroring logic now respects the threshold of both source and mirror streams

- Added internal validation to prevent logs from being mirrored when not accepted by their source

### Changed

- Replaced NOTSET with TRACE as the lowest log level

- Updated README with log level documentation and examples

---

## [0.1.1] - 2025-05-07
### Changed

- Clarified support for single-stream logging in README.

- Clarified that `mirror_map` is optional for single-stream setups.


