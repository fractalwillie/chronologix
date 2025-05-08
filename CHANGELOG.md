# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

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


