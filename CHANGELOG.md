# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.1.1] - 2026-07-27

### Added

- Comprehensive test suite with 78 tests covering module-level and class-method
  ordering, decorators, cycles, real-world scripts, and conservative-safety
  regressions.
- Support for detecting method calls (`self.method()`) within classes
- Support for class references in type annotations and class bodies

### Changed

- **Conservative, safety-preserving sorting.** funcsort now only reorders
  top-level functions/classes and methods within classes, and only within *runs*
  of consecutive definitions. Constants, imports and all other module-level
  statements are anchors that keep their exact original positions. Files with no
  functions or classes are left completely untouched.
- Reordering is constrained so it can never break definition-time name
  resolution: a name used in a decorator, base class, annotation, parameter
  default or class-body statement is always kept before the definition that uses
  it. Property getters stay before their setters. Cycles fall back to the
  original order.
- Within a run, definitions are ordered by call hierarchy - the entry point
  (`main`/`__init__`) first, then the functions it calls (top-down) - with
  alphabetical tie-breaks.

### Fixed

- No longer hoists imports across intervening module-level code (e.g. staged
  imports separated by setup statements).
- No longer moves a variable away from module-level code that uses it (e.g. a
  `fmt` value used by `logging.basicConfig`).
- No longer moves a function/class after code that needs it at definition time
  (e.g. a function used as a class-attribute default, or a class used in another
  class's method signature).
- Property/setter pairs keep getter-before-setter order.
- Comments stay attached to their definitions; PEP 8 spacing (2 blank lines
  before top-level defs, 1 between methods) is applied without trailing
  whitespace.
- No longer strips the trailing newline from uv-script files (those with a
  `# /// script ... # ///` header), which previously made the end-of-file-fixer
  pre-commit hook re-add it on every run.

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
