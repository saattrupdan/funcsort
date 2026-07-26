# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.1.0] - 2026-07-26

### Added

- CLI with `--fix` option to sort Python files in place
- Pre-commit hook for automatic sorting
- `.gitignore` support to skip ignored files/directories
- Verbose mode (`-v`/`--verbose`) for detailed output
- `make check` requirement before version bumping

### Changed

- Scripts moved to `src/scripts/` directory
- Moved source code to `src/funcsort/` structure

### Fixed

- Decorator definitions now correctly placed before their usages when both
  are defined in the same module
- Added `click` as a runtime dependency
- Markdown line length violations in changelog
