# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Comprehensive test suite (`tests/test_sorting.py`) covering module-level functions,
  class methods, decorators, cycles, and edge cases
- Support for detecting method calls (`self.method()`) within classes
- Support for class references in type annotations (classes now sorted before
  functions using them)
- Support for generic type annotations (`list[T]`, `dict[K, V]`, etc.)
- Support for type hints in class bodies (class attributes with type annotations)
- Support for class instantiations in class body assignments (e.g. `device = DummyDevice()`)

### Changed

- Function ordering now puts definitions before usages (callees before callers)
- Module rewrite order: docstring → imports → constants → functions/classes → `__main__` blocks
- Classes are now sorted along with functions based on type hint dependencies
- Constants now always appear before functions (after imports)

### Fixed

- Call graph extraction now properly traverses function bodies (was blocking on first
  `FunctionDef`)
- Decorator dependencies now correctly ordered (decorator definitions before usages)
- Constants that call functions now correctly placed after their dependencies
- Cycle handling in topological sort (mutual recursion)
- Import and docstring detection in module rewriting

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
