# /// script
# requires-python = ">=3.12,<4.0"
# dependencies = []
# ///

"""Scripts related to updating of version."""

import datetime as dt
import re
import subprocess
from pathlib import Path


def bump_major() -> None:
    """Add one to the major version."""
    major, _, _ = get_current_version()
    set_new_version(major + 1, 0, 0)


def bump_minor() -> None:
    """Add one to the minor version."""
    _, minor, _ = get_current_version()
    set_new_version(0, minor + 1, 0)


def bump_patch() -> None:
    """Add one to the patch version."""
    _, _, patch = get_current_version()
    set_new_version(0, 0, patch + 1)


def get_current_version() -> tuple[int, int, int]:
    """Fetch the current version of the package.

    Returns:
        A tuple of (major, minor, patch).

    Raises:
        RuntimeError:
            If no version can be found in the `pyproject.toml` file.
    """
    pyproject_path = Path("pyproject.toml")
    pyproject = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'version = "(\d+)\.(\d+)\.(\d+)"', pyproject)
    if not match:
        raise RuntimeError("Could not find version in pyproject.toml.")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def set_new_version(major: int, minor: int, patch: int) -> None:
    """Sets a new version.

    Args:
        major:
            The major version. This only changes when the code stops being backwards
            compatible.
        minor:
            The minor version. This changes when a backwards compatible change
            happened.
        patch:
            The patch version. This changes when the only new changes are bug fixes.

    Raises:
        RuntimeError:
            If no version can be found in the `pyproject.toml` file.
    """
    version = f"{major}.{minor}.{patch}"

    # Get current changelog and ensure that it has an [Unreleased] entry
    changelog_path = Path("CHANGELOG.md")
    changelog = changelog_path.read_text(encoding="utf-8")
    if "[Unreleased]" not in changelog:
        raise RuntimeError("No [Unreleased] entry in CHANGELOG.md.")

    # Add version to CHANGELOG
    today = dt.date.today().strftime("%Y-%m-%d")
    new_changelog = re.sub(
        r"\[Unreleased\].*", f"[Unreleased]\n\n## [v{version}] - {today}", changelog
    )
    changelog_path.write_text(new_changelog, encoding="utf-8")

    # Update the version in the `pyproject.toml` file
    pyproject_path = Path("pyproject.toml")
    pyproject = pyproject_path.read_text(encoding="utf-8")
    pyproject = re.sub(
        r'version = "[^"]+"', f'version = "{version}"', pyproject, count=1
    )
    pyproject_path.write_text(pyproject, encoding="utf-8")

    # Install newest project
    subprocess.run(["uv", "run", "pip", "install", "-e", "."], check=True)

    # Add to version control
    subprocess.run(["git", "add", "CHANGELOG.md"], check=True)
    subprocess.run(["git", "add", "pyproject.toml"], check=True)
    subprocess.run(["git", "add", "uv.lock"], check=True)
    subprocess.run(["git", "commit", "-m", f"feat: v{version}"], check=True)
    subprocess.run(["git", "tag", f"v{version}"], check=True)
    subprocess.run(["git", "push"], check=True)
    subprocess.run(["git", "push", "--tags"], check=True)

    print(f"✓ Released v{version}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: uv run versioning.py <major|minor|patch>")
        sys.exit(1)

    bump_type = sys.argv[1].lower()
    if bump_type == "major":
        bump_major()
    elif bump_type == "minor":
        bump_minor()
    elif bump_type == "patch":
        bump_patch()
    else:
        print(f"Unknown bump type: {bump_type}")
        print("Use 'major', 'minor', or 'patch'")
        sys.exit(1)
