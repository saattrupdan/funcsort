# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Comprehensive test suite with 72 tests covering:
  - Module-level functions and call hierarchy
  - Class methods and `__init__` ordering
  - Decorator definitions before usage
  - Cycles and edge cases
  - Regression tests for all reported bugs
  - Full real-world script test (hun-sum-mini)
- Support for detecting method calls (`self.method()`) within classes
- Support for class references in type annotations
- Support for generic type annotations (`list[T]`, `dict[K, V]`, etc.)
- Support for type hints in class bodies
- Support for class instantiations in class body assignments

### Changed

- **Constants are no longer sorted** - they preserve their original positions
- Only functions and classes are sorted by call hierarchy
- Module structure: docstring → imports → constants (original order) → sorted
  functions/classes → `__main__` blocks
- Function ordering puts definitions before usages (callees before callers)
- Entry point (`main`) comes first among functions
- Classes referenced in type hints come before functions that use them
- Decorator definitions come before decorated functions

### Fixed

- Comments on constant definitions now preserved during sorting
- Assert statements now sorted after their dependencies
- Constants preserve their original blank-line separation between blocks; spacing is
  only normalised when reordering brings two constants together
- Assert statements don't get extra blank lines before them (stick to previous item)
- Proper PEP 8 spacing: 1 blank line after imports before constants/module-level
  calls, 2 blank lines before functions/classes
- Unused constants maintain their original positions
- Logger/module variables remain before functions that reference them

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
