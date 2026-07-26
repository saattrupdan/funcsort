# Funcsort

Automatically sort Python functions and methods by call hierarchy.

## Installation

```bash
uv add funcsort
```

## CLI Usage

```bash
# Check if files are sorted (default)
uv run funcsort [PATH]

# Automatically fix sorting
uv run funcsort --fix [PATH]

# Verbose output
uv run funcsort -v [PATH]
```

The `PATH` argument can be a file or directory (defaults to current directory).

**Exit codes:**

- `0`: Success (files are sorted or were fixed with `--fix`)
- `1`: Files need sorting (in check mode without `--fix`)

## Sorting Rules

### Functions

Functions are sorted by top-down call hierarchy:

1. `main` function is always first
2. Functions that call other functions appear before their callees
3. Ties (including circular dependencies) are broken alphabetically

### Methods

Methods within a class follow the same rules:

1. `__init__` is always first
2. Callers appear before callees
3. Ties are broken alphabetically

### What's Not Sorted

- Top-level code (imports, constants, class definitions) remains in place
- Nested functions are left untouched
- Cross-module function calls are ignored
- Cross-class method calls are ignored

Decorators are preserved when functions are moved.

## Pre-commit Hook

Add to your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/saattrupdan/funcsort
  rev: v0.0.0  # Use the latest tag
  hooks:
    - id: funcsort
      args: [--fix]  # Automatically fix sorting
```

Or use locally with `uv`:

```yaml
- repo: local
  hooks:
    - id: funcsort
      name: Sort Python functions by call hierarchy
      language: python
      entry: uv run funcsort --fix
      pass_filenames: false
      types: [python]
```

### Configuration

The hook supports `pass_filenames`:

- **Default (`false`):** Runs on all `.py` files in the repository
- **Set to `true`:** Runs only on staged files

```yaml
- repo: local
  hooks:
    - id: funcsort
      language: python
      entry: uv run funcsort --fix
      pass_filenames: true
      types: [python]
```

## Example

Before:

```python
def helper():
    return 42


def main():
    return helper()
```

After `funcsort --fix`:

```python
def main():
    return helper()


def helper():
    return 42
```

## Limitations

- Only sorts top-level functions and class methods
- Does not handle complex cross-module dependency analysis
- Nested functions remain in their original positions
