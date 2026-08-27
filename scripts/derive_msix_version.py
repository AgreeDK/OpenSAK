#!/usr/bin/env python3
"""
scripts/derive_msix_version.py

Derive the 4-part numeric MSIX Package/Identity/@Version from OpenSAK's
__version__ string in src/opensak/__init__.py.

Why this exists: MSIX requires a strict Major.Minor.Build.Revision numeric
version and rejects the "-beta.N" suffix OpenSAK otherwise uses everywhere
else (git tags, CHANGELOG, __version__). packaging/msix/README.md flagged
this conversion as something CI integration (#786 step 3) would need once
MSIX moved past the local-prototype stage — this is that script.

Mapping:
    1.18.0            -> 1.18.0.0      (stable release, revision 0)
    1.18.0-beta.1     -> 1.18.0.1      (beta N becomes the revision)
    1.18.0-beta.12    -> 1.18.0.12
    1.18.0-rc.1       -> 1.18.0.1      (any -word.N suffix works the same way)

This only derives a version number for packaging. It does NOT read or write
__init__.py — that stays scripts/bump_version.py's job.

Usage:
    python scripts/derive_msix_version.py                # reads __init__.py
    python scripts/derive_msix_version.py 1.18.0-beta.3   # explicit version
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_PY = ROOT / "src" / "opensak" / "__init__.py"

# Same shape bump_version.py accepts: "1.14.0" or "1.14.0-beta.18" etc.
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-[a-zA-Z]+\.(\d+))?$")

_INIT_VERSION_RE = re.compile(r'__version__ = "([^"]+)"')


def get_init_version() -> str:
    """Return the version currently set in src/opensak/__init__.py."""
    text = INIT_PY.read_text(encoding="utf-8")
    match = _INIT_VERSION_RE.search(text)
    if not match:
        raise RuntimeError(f"Could not find __version__ in {INIT_PY}")
    return match.group(1)


def derive_msix_version(version: str) -> str:
    """Convert an OpenSAK version string to a 4-part numeric MSIX version.

    Raises ValueError if `version` doesn't match OpenSAK's expected shape.
    """
    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(
            f"'{version}' doesn't look like an OpenSAK version "
            "(expected e.g. '1.18.0' or '1.18.0-beta.3')"
        )
    major, minor, build, suffix_n = match.groups()
    revision = suffix_n if suffix_n is not None else "0"
    return f"{major}.{minor}.{build}.{revision}"


def main() -> None:
    if len(sys.argv) > 2:
        print("Usage: python scripts/derive_msix_version.py [version]", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) == 2:
        source_version = sys.argv[1].lstrip("v")
    else:
        source_version = get_init_version()

    try:
        msix_version = derive_msix_version(source_version)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(msix_version)


if __name__ == "__main__":
    main()
