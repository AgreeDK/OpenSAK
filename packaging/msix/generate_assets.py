"""Generate the PNG image assets an MSIX package/AppxManifest.xml needs.

Source image: assets/icons/opensak_512.png (already in the repo, used for
the macOS .icns / other high-res needs). This script does NOT touch that
file — it only reads it and writes resized copies into
packaging/msix/assets/.

This is prototype tooling for issue #786 (step 1: prototype MSIX
packaging). It intentionally generates only the *mandatory* unscaled (1x)
assets needed for a private/unlisted Partner Center test submission and a
local sideload install:

    Square44x44Logo.png    44x44   (app list / taskbar icon)
    Square150x150Logo.png  150x150 (medium tile, shown in Start)
    Square71x71Logo.png    71x71   (small tile — optional but cheap to add)
    Wide310x150Logo.png    310x150 (wide tile — optional, letterboxed)
    StoreLogo.png          50x50   (Store listing / app list fallback)

Once real Store certification work begins (issue #786 step 4), this
should be extended to generate the full scale-factor set (100/125/150/
200/400) declared as <Resources> in the manifest — deliberately skipped
here since a private test submission doesn't need scaled variants.

Usage (from repo root):
    python packaging/msix/generate_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ICON = REPO_ROOT / "assets" / "icons" / "opensak_512.png"
OUTPUT_DIR = Path(__file__).resolve().parent / "assets"

# name -> (width, height, padding_fraction)
# padding_fraction leaves empty margin around the icon, matching Windows'
# tile design guidance (square logos ~ 2/12 padding, wide logo needs the
# icon centered in a much wider canvas).
TARGETS: dict[str, tuple[int, int, float]] = {
    "Square44x44Logo.png": (44, 44, 0.10),
    "Square71x71Logo.png": (71, 71, 0.15),
    "Square150x150Logo.png": (150, 150, 0.15),
    "Wide310x150Logo.png": (310, 150, 0.18),
    "StoreLogo.png": (50, 50, 0.10),
}


def make_asset(source: Image.Image, width: int, height: int, padding_fraction: float) -> Image.Image:
    """Return a WxH RGBA canvas with `source` scaled and centered on it."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Fit the icon inside the smaller dimension, minus padding.
    usable = min(width, height) * (1 - 2 * padding_fraction)
    scale = usable / max(source.width, source.height)
    new_size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    icon = source.resize(new_size, Image.LANCZOS)

    offset = ((width - icon.width) // 2, (height - icon.height) // 2)
    canvas.paste(icon, offset, icon)
    return canvas


def main() -> None:
    if not SOURCE_ICON.exists():
        raise SystemExit(f"Source icon not found: {SOURCE_ICON}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE_ICON).convert("RGBA")

    for filename, (w, h, pad) in TARGETS.items():
        asset = make_asset(source, w, h, pad)
        out_path = OUTPUT_DIR / filename
        asset.save(out_path)
        print(f"wrote {out_path.relative_to(REPO_ROOT)} ({w}x{h})")


if __name__ == "__main__":
    main()
