# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Comprehensive test suite (`tests/test_sorting.py`) with 47 tests covering:
  - Module-level functions and call hierarchy
  - Class methods and `__init__` ordering
  - Decorator definitions before usage
  - Cycles and edge cases
  - Regression tests for all reported bugs (default args, unions, lambdas, etc.)
- Support for detecting method calls (`self.method()`) within classes
- Support for class references in type annotations
- Support for generic type annotations (`list[T]`, `dict[K, V]`, etc.)
- Support for type hints in class bodies
- Support for class instantiations in class body assignments
- Constants as sortable units with dependency tracking

### Changed

- Function ordering now puts definitions before usages (callees before callers)
- Module rewrite order: docstring → imports → sorted units → `__main__` blocks
- Constants, functions and classes now sorted together by dependencies:
  - Constants calling functions come after those functions
  - Classes referenced in type hints come before dependents
  - Decorator definitions come before decorated functions
- Entry points (`main`, `__init__`) moved to front of their category

- Call graph extraction now properly traverses function bodies (was blocking on first
  `FunctionDef`)
- Decorator dependencies now correctly ordered (decorator definitions before usages)
- Constant dependencies on functions and classes now detected and sorted correctly
- Type hints in function signatures handled (class before function using it)
- Type hints in class body attributes handled
- Class instantiations in class body (`device = DummyDevice()`) detected
- Generic type annotations (`list[Item]`) correctly unwrapped
- Union type annotations (`Input \| Config`) parsed correctly
- Default argument values scanned for dependencies
- Lambda expressions in constants scanned for dependencies
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
