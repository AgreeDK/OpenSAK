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

The Store additionally rejects any package whose manifest Version has a
non-zero Revision (4th) component — confirmed by a real Partner Center
"Package acceptance validation error" on 27 Aug 2026 when an earlier
version of this script put the beta number there. Revision is therefore
always 0; the patch number and beta number are both folded into Build
(3rd component) instead:

    Build = patch * 1000 + (beta_number, or 999 for a non-beta/stable
    version)

The *999 for stable* choice is deliberate: it guarantees a patch's final
stable release sorts higher than every beta of that same patch (e.g.
1.18.0-beta.1 → build 1, 1.18.0-beta.12 → build 12, 1.18.0 stable →
build 999 — all higher than any realistic beta count). Different patch
numbers never collide since each gets its own reserved block of 1000.

Mapping:
    1.18.0            -> 1.18.999.0    (stable release; patch 0, "999" marks final)
    1.18.0-beta.1     -> 1.18.1.0      (patch 0, beta 1)
    1.18.0-beta.12    -> 1.18.12.0     (patch 0, beta 12)
    1.17.2-beta.3     -> 1.17.2003.0   (patch 2 → block 2000-2998, beta 3)
    1.17.2            -> 1.17.2999.0   (patch 2, stable marker)

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

# Reserved marker for "this patch's stable/final release" within its
# 1000-wide block — must be higher than any realistic beta count.
_STABLE_MARKER = 999
_PATCH_BLOCK_SIZE = 1000


def get_init_version() -> str:
    """Return the version currently set in src/opensak/__init__.py."""
    text = INIT_PY.read_text(encoding="utf-8")
    match = _INIT_VERSION_RE.search(text)
    if not match:
        raise RuntimeError(f"Could not find __version__ in {INIT_PY}")
    return match.group(1)


def derive_msix_version(version: str) -> str:
    """Convert an OpenSAK version string to a 4-part numeric MSIX version.

    Revision (4th component) is always 0 — the Store rejects non-zero
    revisions. Patch and beta number are folded into Build (3rd
    component) instead; see module docstring for the exact scheme.

    Raises ValueError if `version` doesn't match OpenSAK's expected shape,
    or if the beta number is too large to fit in its reserved block.
    """
    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(
            f"'{version}' doesn't look like an OpenSAK version "
            "(expected e.g. '1.18.0' or '1.18.0-beta.3')"
        )
    major, minor, patch, suffix_n = match.groups()
    patch_i = int(patch)

    if suffix_n is not None:
        beta_i = int(suffix_n)
        if beta_i >= _STABLE_MARKER:
            raise ValueError(
                f"beta number {beta_i} is too large — must be < {_STABLE_MARKER} "
                "to fit in its reserved block alongside the stable marker"
            )
        offset = beta_i
    else:
        offset = _STABLE_MARKER

    build = patch_i * _PATCH_BLOCK_SIZE + offset
    return f"{major}.{minor}.{build}.0"


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
