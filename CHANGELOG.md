# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.10.0] - 2025-05-23
### Added

- **Timezone Support**  
    - New `timezone` config option allows users to align all timestamps and folder names to a specific timezone  
    - Defaults to `"UTC"` if not provided  
    - Powered by Python 3.9+ `zoneinfo` module  
    - Raises a clear error on invalid timezone names

- **Internal Sink Logging**  
    - Chronologix now writes internal diagnostic logs to `chronologix_internal.log` inside each chunk folder  
    - Useful for debugging rollover, compression, and cleanup behavior  
    - Automatically created and updated

- **Drift-Resistant Rollover Loop**  
    - Rollover is now based on monotonic time with tolerance for wakeup drift  
    - Fixes rare rollover timing bugs when the system is under load, VM suspends etc.

### Changed

- **Rollover Module Refactor**  
    - Time math now respects `zoneinfo` fully  
    - Compression and cleanup are aware of timezones as well

- **Error Surfacing Improvements**  
    - All config-related errors now raise **on startup only**  
    - Chronologix will never crash your app at runtime due to misconfigurations

- **Minimum Python Requirement**  
    - Raised to `>=3.9` due to new timezone handling (`zoneinfo` support)

- **README** updated with timezone config section, including examples

---

## [0.9.0] - 2025-05-17
### Added

- **Async Log Hooks** — optional user-defined functions triggered on every log event

    - Supports coroutine-based handlers with optional `min_level` filtering

    - Handlers receive the structured log object: `{timestamp, level, message}`

    - Configured via new `hooks` parameter in `LogConfig`

    - Multiple handlers can be registered

    - Hooks are isolated, timeout-protected, and won't crash your app

    - Some use cases: alerts, chatbots, real-time DB insertion, metrics 

- Full validation for malformed or non-async hook functions

- Timeout protection for long-running hooks (default: 5 seconds)

### Changed

- README updated with async log hooks documentation, including examples

---

## [0.8.1] - 2025-05-16
### Fixed

- Fixed `retain` feature which was unable to delete subfolders after the I/O overhaul

    - `flush()` function in io.py module now properly closes file handles, frees them from memory and allows `run_cleanup()` to delete them

---

## [0.8.0] - 2025-05-15
### Added

- Complete I/O subsystem overhaul

    - Replaced open-write-close model with long-lived async buffered writer

    - Messages are now queued and written in batches using a background task

    - Buffered writer handles write(), flush(), fsync(), and close() with per-file exception handling

    - Flush is enforced before rollover to prevent cross-chunk log overlap

    - Handles missing or broken paths, future rollovers recover automatically

    - atexit hook ensures flush on shutdown or crashes

- Performance optimization

    - Introduced coroutine memoization for logger.debug/info/warning/... methods

    - Avoids rebuilding coroutines for each call

### Performance Boost

| Metric                   | v0.7.0       | v0.8.0         |
| ------------------------ | ------------ | -------------- |
| Single-thread throughput | \~5 msg/s    | \~9300 msg/s   |
| Avg latency              | \~200–900 ms | \~0.10–0.45 ms |
| Max latency              | >4 sec       | <1 sec         |


---

## [0.7.0] - 2025-05-14
### Added

- New optional log compression system

    - Compresses the *previous* time chunk subdir on every rollover

    - Supports `"zip"` and `"tar.gz"` formats

    - Configurable via new `compression` parameter in `LogConfig`

    - Internal mutex added to prevent compression and cleanup from colliding

- Validation in config module:
    - Incompatible `compress_format` 
    - Misconfigured `enabled` boolean

### Changed

- README updated with full documentation of compression feature

---

## [0.6.1] - 2025-05-13
### Changed

- Refactored `__post_init__()` in `config.py` into dedicated validation functions to satisfy my OCD
    
    - Improves code readability, structure, and navigation

    - No changes to functionality or behavior

    - The config module is now 50 lines longer and 500% more beautiful

---

## [0.6.0] - 2025-05-13
### Added

- New optional `format` key for both sinks and mirror

    - Supports `"text"` (default) and `"json"`

    - Per-sink granularity, some sinks can be `text`, others `json`

    - `cli_echo` remains in plain text regardless of sink/mirror `format`

    - `file` type extension (.log, .txt, .json, .jsonl) doesn't need to match `format`

- Validation in config module:
    - Unsupported `format` (e.g. `"csv"`)
    - Incompatible file extensions
    - Missing or misconfigured sink/mirror `format`

### Changed

- `cli_echo` logic adjusted to force formatting as `"text"` and to not be affected by sink or mirror config

- Updated README to reflect the new format support

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


