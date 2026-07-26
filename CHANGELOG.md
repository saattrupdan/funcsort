# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- CLI with `--fix` option to sort Python files in place
- Pre-commit hook for automatic sorting
- `.gitignore` support to skip ignored files/directories
- Verbose mode (`-v`/`--verbose`) for detailed output

### Changed

- Functions sorted with `main` first, then by call graph (callers before callees)
- Methods sorted with `__init__` first, same call hierarchy rules within each class
- Exit code 0 when `--fix` is applied successfully
- Exit code 1 in check mode when files need sorting

### Fixed

- Type alias comment format (no colon, no trailing period)
- Consolidated `_Statement` type alias to single location
- Fixed `ty` compatibility for libcst visitor pattern

## v0.0.0 - 2025-01-24

### Added

- Initial release of funcsort
