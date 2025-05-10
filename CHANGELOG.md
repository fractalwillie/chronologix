# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

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


