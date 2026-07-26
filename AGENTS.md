# Funcsort

CLI tool and pre-commit hook that automatically sorts Python functions and
methods by call hierarchy. Published at
<https://github.com/saattrupdan/funcsort>.

## Stack

- Python 3.12+
- Package manager: `uv`
- Code formatter/linter: `ruff`
- Type checker: `ty`
- AST parser: `libcst` (preserves formatting during rewrites)
- Gitignore parsing: `pathspec`

## Layout

```text
funcsort/
├── AGENTS.md              # Agent/contributor orientation (this file)
├── CHANGELOG.md           # Version history
├── README.md              # User documentation
├── pyproject.toml         # Project config, dependencies, tool settings
├── uv.lock                # Locked dependencies
├── .gitignore             # Git ignore patterns
├── .pre-commit-hooks.yaml # Hook definition for external use
├── .pre-commit-config.yaml # Local pre-commit configuration
├── Makefile               # Convenience commands
├── src/
│   ├── funcsort/          # Package source code
│   │   ├── __init__.py
│   │   ├── call_graph.py  # Build call graphs from function bodies
│   │   ├── cli.py         # Click-based CLI entry point
│   │   ├── core.py        # Main sorting orchestration (libcst visitor)
│   │   ├── models.py      # Data models (SortableUnit, type aliases)
│   │   ├── ordering.py    # Topological sort by call hierarchy
│   │   ├── parsing.py     # Extract functions/methods using libcst
│   │   └── rewrite.py     # Reassemble sorted code
│   └── scripts/           # Executable scripts
│       ├── funcsort.py    # Script wrapper (uv run entry point)
│       └── versioning.py  # Version bumping and release automation
└── tests/                 # Test files (currently none per requirement)
```

## Running it

```bash
# Check if files are sorted
uv run funcsort [PATH]

# Automatically fix sorting
uv run funcsort --fix [PATH]

# Verbose output
uv run funcsort -v [PATH]

# Run quality checks
make check

# Run versioning script
uv run src/scripts/versioning.py <major|minor|patch>
```

## Testing

No tests (explicit requirement #5).

## Conventions

### Code style

- British English in code and docs
- 88-character line width (enforced by ruff format)
- f-strings only (no %-style formatting)
- Imports at top of file
- Use `import typing as t` and `import collections.abc as c`
- Type aliases use `# Type alias for...` format (no colon, no trailing period)
- Inline comments: two spaces before `#` (PEP 8 E261)

### Type hints

- Full type annotations on all functions
- Python 3.12+ syntax (`list[T]`, `dict[K, V]`, `X | Y`, `X | None`)
- Avoid `Any` — use `t.TypeVar` with meaningful names instead
- Use `None` return type for void functions (never `NoReturn`)

### Function ordering

- Module order: docstring → imports → constants → functions/classes → `__main__` blocks
- Constants always appear before functions (after imports)
- `main` functions and `__init__` methods first within their scope (entry points)
- Classes and functions sorted by dependencies: callees before callers (definitions before usages)
- Class references in type annotations: class before function using it
- Decorator definitions before their usages
- Ties broken alphabetically

### Commit messages

Conventional Commits format:

```text
<type>: <description>
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `chore`: Tooling, dependencies, configuration
- `style`: Formatting, code style (no logic changes)

### Release process

1. Update `CHANGELOG.md` with changes under `[Unreleased]`
2. Run `uv run src/scripts/versioning.py <major|minor|patch>`
   - This updates version in `pyproject.toml`
   - Moves `[Unreleased]` to versioned section in `CHANGELOG.md`
   - Commits, tags, and pushes to GitHub

## Gotchas

- **libcst required**: Standard `ast` module doesn't preserve
  comments/decorators. All parsing uses `libcst`.
- **No cross-module analysis**: funcsort only sorts within a single
  file. Cross-file dependencies are ignored.
- **Nested functions ignored**: Only top-level functions and class methods are sorted.
- **Exit codes**:
  - `0`: Success (files sorted or already correct)
  - `1`: Files need sorting (check mode without `--fix`)
  - `0`: After `--fix` is applied (even if changes were made)
- **`.gitignore` support**: Files/directories in `.gitignore` are automatically skipped.
- **`original_node` parameter**: Required by libcst's visitor pattern
  — keep the name even if unused (rename breaks `ty`'s override checking).
  Suppress with `# noqa: ARG002`.
- **Type alias location**: `_Statement` defined in `models.py` only —
  import from there, don't redefine.
- **Pre-commit hook**: Default `pass_filenames: false` runs on all
  `.py` files. Set to `true` for staged files only.
- **Unicode symbols in output**:
  - `✓` for success
  - `✗` for check failures
