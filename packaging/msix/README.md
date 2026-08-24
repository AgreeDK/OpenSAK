# MSIX packaging prototype (issue #786)

This directory is the **prototype** work for #786's step 1–2: package
OpenSAK as MSIX and confirm Microsoft Store certification doesn't reject
it because of the bundled QtWebEngine/Chromium runtime, before investing
in CI integration (step 3) or the full Store listing (step 4).

Nothing here changes the existing Windows `.exe`/ZIP build — `opensak.spec`
and `build.yml` are untouched. This wraps the same PyInstaller output in an
MSIX container as a side channel.

**Everything below runs on Windows** (your Windows VM) — MSIX packaging
tools (`makeappx.exe`, `signtool.exe`) don't exist on Linux/macOS, and
Partner Center submission is a browser step. This branch was prepared on
Linux, so nothing has been built or tested yet — that's the point of
step 1.

## Prerequisites (one-time, on the Windows VM)

1. Install the **Windows 10/11 SDK** (or the standalone "MSIX Packaging
   Tool" from the Microsoft Store) — this provides `makeappx.exe` and
   `signtool.exe`. SDK: https://developer.microsoft.com/windows/downloads/windows-sdk/
2. Make sure `dist\OpenSAK\opensak.exe` can be built the normal way first
   (i.e. your existing local Windows build setup already works).
3. Pull this branch:
   ```powershell
   git fetch origin feature/msix-packaging
   git checkout feature/msix-packaging
   ```

## Step 1 — local packaging + sideload test

Run from the repo root in PowerShell:

```powershell
.\packaging\msix\build_msix_local.ps1 -InstallAfterBuild
```

What it does:

1. Builds `dist\OpenSAK\` via PyInstaller (same as CI) — skip with
   `-SkipBuild` if you already have a fresh build.
2. Generates the MSIX tile/logo images from `assets/icons/opensak_512.png`
   (`packaging/msix/assets/*.png` — gitignored output, regenerated each
   run, same pattern as the boundary baseline data).
3. Fills in `AppxManifest.xml.template` with **dev-test placeholder**
   values (`OpenSAKDevTest.OpenSAK` identity, self-signed cert) — these
   are NOT the real Store identity, see step 2.
4. Packages it with `makeappx.exe` into
   `dist\OpenSAK-<version>-prototype.msix`.
5. Signs it with a local self-signed certificate (created automatically
   on first run).
6. With `-InstallAfterBuild`: installs it via `Add-AppxPackage`.

### 1c. Trusting the self-signed test certificate

`Add-AppxPackage` will refuse to install an MSIX unless the signing
certificate is trusted locally. After the script creates the test cert
the first time:

```powershell
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq "CN=OpenSAK Dev Test" }
Export-Certificate -Cert $cert -FilePath "$env:TEMP\opensak-dev-test.cer"
Import-Certificate -FilePath "$env:TEMP\opensak-dev-test.cer" -CertStoreLocation Cert:\LocalMachine\TrustedPeople
```
(Needs an elevated/Admin PowerShell for the `Import-Certificate` line.)

### What to actually check once it's installed

This is the point of the whole prototype — don't just confirm it installs:

- [ ] OpenSAK launches from the Start Menu tile
- [ ] **Map tab loads** (Leaflet/OSM via QtWebEngine) — this is the specific
      risk #786 flags; if QtWebEngine fails inside the MSIX sandbox this is
      where it'll show up
- [ ] Database create/open works, import a small GPX to sanity-check file
      I/O
- [ ] Update checker doesn't error out (outbound HTTPS — confirms the
      `internetClient` capability is sufficient)
- [ ] Uninstall cleanly via Settings → Apps

If any of those fail in ways that look sandbox-related (not ordinary
bugs), that's the signal to stop and reconsider — see "If this doesn't
work" below.

## Step 2 — Partner Center test submission

This step needs a Microsoft Partner Center **individual developer
account** (free as of the 2026 fee removal — see #786's step 4, but the
account itself needs to exist before you can submit anything, even a
private test). If you don't have one yet:

1. https://partner.microsoft.com/dashboard/registration — register as
   Individual.
2. Once approved, **App name reservation**: reserve "OpenSAK" (or
   whatever's available) under your account. This is where the *real*
   `Identity Name` and `Publisher` (CN) values come from — Partner Center
   shows them on the app's **Product identity** page after reservation.
3. Re-run the local build with the real identity values instead of the
   dev-test placeholders:
   ```powershell
   .\packaging\msix\build_msix_local.ps1 `
       -IdentityName "<value from Partner Center>" `
       -PublisherCN  "<value from Partner Center>" `
       -Version "1.17.2.0"
   ```
   Note: for an actual Store submission the package must be signed with
   your Partner Center-associated certificate flow, not the local
   self-signed one — Partner Center will tell you what's needed
   (typically it accepts an unsigned or dev-signed package for
   submission and re-signs it during certification).
4. In Partner Center: **Submissions → new submission**, mark it as
   private/unlisted (not public), upload the `.msix`, fill the minimum
   required Store listing fields (can be placeholder text — this is a
   certification test, not a real launch).
5. Submit and wait for certification results (per #786: can take hours
   to days).

### Reading the certification result

- **Pass** → QtWebEngine risk is cleared. Move to #786 step 3 (CI
  integration) and step 4 (real Store listing). #564 (paid Windows
  cert) can likely stay on hold.
- **Fail, specifically citing the embedded Chromium/WebView component**
  → this is the risk #786 called out. Options: request a manual review
  exception from Microsoft, investigate `WebView2` as a lighter-weight
  alternative to QtWebEngine for the Store build specifically, or fall
  back to reactivating #564.
- **Fail, for unrelated reasons** (manifest issues, missing listing
  fields, icon requirements) → fix and resubmit; not a signal to
  abandon MSIX.

## Version numbering

MSIX requires a strict 4-part numeric `Package/Identity/@Version`
(`Major.Minor.Build.Revision`) — it does **not** accept OpenSAK's
`-beta.N` suffix. For this prototype, `build_msix_local.ps1` takes an
explicit `-Version` (default `1.17.2.0`, i.e. the beta suffix dropped and
`.0` appended). If MSIX moves past the prototype stage, step 3 (CI
integration) will need a small script to derive this automatically from
`src/opensak/__init__.py`'s `__version__` — deliberately not built yet
since it's premature before we know MSIX is viable at all.

## Files in this directory

| File | Purpose |
|---|---|
| `AppxManifest.xml.template` | Manifest template — see comments inside for each placeholder |
| `build_msix_local.ps1` | One-shot local build → package → sign → (optionally) install |
| `generate_assets.py` | Generates the required tile/logo PNGs from `assets/icons/opensak_512.png` |
| `assets/` | Generated image output (gitignored — regenerated by `generate_assets.py`) |
