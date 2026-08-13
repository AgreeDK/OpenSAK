# Feature Flags

Feature flags let you merge in-progress work without shipping it to end-users.
A **new** flag defaults to **off** in release builds and **on** in developer
builds, with no code changes required at release time. Once a feature has
graduated (proven stable in beta), its default in `_RELEASE_DEFAULTS` is
flipped to **on** — see [Current flags](#current-flags) below — until the
flag guard is removed entirely.

---

## How it works

Priority order (highest wins):

```
CLI --feature arg  >  features.json  >  release defaults (per-flag, see below)
```

| Context | Features file present? | Result |
|---|---|---|
| Developer running from source | Yes (`features.json` in repo root) | Flags from file |
| PyInstaller release bundle | No (file is never bundled) | All flags off |
| Any context with `--feature` | Either | CLI overrides win |

---

## features.json

`features.json` lives at the project root. It is **committed to git** with
developer-friendly values (`true`) and is **never included** in the PyInstaller
bundle, so it is invisible to release users.

```json
{
  "reverse-geocoding": true,
  "map-popout": true
}
```

To disable a flag locally without touching the file, use the CLI override (see below).

---

## CLI override

Pass `--feature name=value` when launching the app. Repeat the flag for
multiple overrides. This is the highest-priority source and overrides anything
in `features.json`.

```bash
# Enable a flag that is off in features.json
opensak --feature reverse-geocoding=true
# or
python run.py --feature reverse-geocoding=true

# Disable a flag that is on in features.json
opensak --feature reverse-geocoding=false

# Override multiple flags at once
opensak --feature reverse-geocoding=true --feature other-flag=false
```

Accepted truthy values: `1`, `true`, `yes`, `on` (case-insensitive).  
Accepted falsy values: `0`, `false`, `no` (case-insensitive).

> **Note:** unrecognised flag names are silently ignored — they will not be
> added to the flag registry automatically.

---

## Adding a new flag

**1. Register it** in `src/opensak/utils/flags.py`:

```python
_RELEASE_DEFAULTS: dict[str, bool] = {
    "reverse-geocoding": False,
    "my-new-flag":       False,   # ← add here
}
```

Add the public attribute at the bottom of the same file:

```python
my_new_flag: bool = _flags["my-new-flag"]
```

**2. Enable it** for development in `features.json`:

```json
{
  "reverse-geocoding": true,
  "my-new-flag":       true
}
```

**3. Use it** anywhere in the codebase:

```python
from opensak.utils import flags

if flags.my_new_flag:
    ...  # new feature path
```

**4. Ship it** by removing the flag guard and deleting the entry from both
`_RELEASE_DEFAULTS` and `features.json` once the feature is stable.

---

## Current flags

Both flags below have **graduated**: their features are done and confirmed
stable in beta, so `_RELEASE_DEFAULTS` now has them **on** for everyone. The
flag guards are kept in place (rather than removed) mainly so they can still
be switched off via `--feature name=false` if a regression turns up. They are
candidates for full removal per step 4 of [Adding a new flag](#adding-a-new-flag).

| Flag | Default | Description |
|---|---|---|
| `reverse-geocoding` | `true` | Offline boundary engine for County / State / Country (issue #60) — gates the Update Location menu action, its right-click context-menu entry, auto-geocode on GPX import, the boundary-packs download/update actions, and the related Settings section |
| `map-popout` | `true` | Full-screen / pop-out map window (issue #696) — gates the "Pop out map" menu action and toolbar button (both main menu and toolbar), and the corresponding JS hook in the Leaflet map HTML that enables pop-out mode |
