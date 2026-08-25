# MSIX packaging prototype (issue #786)

> **Status (25 Aug 2026): prototype validation complete.** A private/
> unlisted Partner Center submission of the OpenSAK MSIX package
> (product `9P4NBMM84H2D`) **passed Store certification**, and was
> confirmed installable end-to-end via the Microsoft Store app (not just
> sideload). This clears the core #786 risk: QtWebEngine/Chromium inside
> the MSIX sandbox is not a Store-certification blocker. Remaining work
> is production integration (CI/CD build automation, public listing),
> not further feasibility testing. See "Where each step runs" below for
> what's Windows-only going forward.

This directory is the **prototype** work for #786's step 1–2: package
OpenSAK as MSIX and confirm Microsoft Store certification doesn't reject
it because of the bundled QtWebEngine/Chromium runtime, before investing
in CI integration (step 3) or the full Store listing (step 4).

Nothing here changes the existing Windows `.exe`/ZIP build — `opensak.spec`
and `build.yml` are untouched. This wraps the same PyInstaller output in an
MSIX container as a side channel.

## Where each step runs

MSIX packaging tools (`makeappx.exe`, `signtool.exe`, `Add-AppxPackage`)
only exist on Windows — there's no practical Linux/macOS equivalent, so
this split is permanent, not just a prototype-stage limitation:

| Step | Where | Why |
|---|---|---|
| Editing this README / the manifest template / the PowerShell script | **Linux or Windows** | Plain text editing, no MSIX tooling involved |
| Building, signing, sideload-installing the `.msix` | **Windows only** | `build_msix_local.ps1` calls `makeappx.exe`/`signtool.exe`/`Add-AppxPackage` — Windows SDK tools with no Linux port |
| Testing the installed app (map/DB/GPX/update-checker) | **Windows only** | Needs the actual sandboxed install to test against |
| Partner Center submission (Properties, Store listings, Submit for certification) | **Linux or Windows, browser only** | Confirmed working from a Linux browser session during the 25 Aug submission |
| Installing/testing via the real Store (private link) | **Windows only** (for now) | Needs a Windows machine signed into the Store app with the right Microsoft account; not yet tested on other platforms |
| Once CI integration (step 3) lands | **Neither — automated** | A `windows-latest` GitHub Actions runner will do the build/sign on tag/release, same pattern as the existing Windows/Linux/macOS artifact pipelines. Until then, every new build needs the Windows machine. |

**Bottom line for now:** keep the Windows machine in the loop for every
build/sign/sideload-test cycle. Partner Center's browser-based submission
step can be done from either machine — Linux is fine for that part.

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
       -PublisherDisplayName "<value from Partner Center>" `
       -Version "1.17.2.0"
   ```
   Note: `-PublisherDisplayName` must match the `PublisherDisplayName` shown
   on Partner Center's Product identity page exactly - the Store validates
   it against your account's registered publisher display name and rejects
   submissions where it doesn't match (even though the package installs
   fine locally either way).
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
  cert) can likely stay on hold. **This is the outcome we got on
  25 Aug 2026** — confirmed pass, and confirmed installable via the
  Store app itself (not just sideload): open
  `https://apps.microsoft.com/detail/restricted/<product ID>` while
  signed into the Store app with a Microsoft account that's a member
  of the private audience group, click Get/Install, launch normally.
- **Fail, specifically citing the embedded Chromium/WebView component**
  → this is the risk #786 called out. Options: request a manual review
  exception from Microsoft, investigate `WebView2` as a lighter-weight
  alternative to QtWebEngine for the Store build specifically, or fall
  back to reactivating #564.
- **Fail, for unrelated reasons** (manifest issues, missing listing
  fields, icon requirements) → fix and resubmit; not a signal to
  abandon MSIX.

## Known Partner Center quirks (from the 25 Aug 2026 submission)

Partner Center's UI has several silent-failure modes — no error shown,
just a section that won't turn "Complete" until you happen to fix the
right thing. Worth checking these first if a submission gets stuck:

- **Switching identity regenerates the signing cert.** If you rebuild
  with a different `-PublisherCN` than a previous run, the script
  creates a **new**, separate self-signed certificate in
  `Cert:\CurrentUser\My` — it does not reuse or rename the old one.
  Trusting an old cert (e.g. a leftover dev-test one) does nothing for
  a package signed with the new one. Check `Get-ChildItem
  Cert:\CurrentUser\My` for multiple certs and make sure you're
  trusting the one whose Subject matches your **current**
  `-PublisherCN`.
- **`Add-AppxPackage` needs the cert trusted in *two* stores.**
  `Cert:\LocalMachine\TrustedPeople` alone gave error `0x800B0109`
  ("root certificate not trusted") — it also needs importing into
  `Cert:\LocalMachine\Root`:
  ```powershell
  Import-Certificate -FilePath "$env:TEMP\<cert>.cer" -CertStoreLocation Cert:\LocalMachine\TrustedPeople
  Import-Certificate -FilePath "$env:TEMP\<cert>.cer" -CertStoreLocation Cert:\LocalMachine\Root
  ```
- **Free-text fields have undocumented character limits.** The
  "Why do you need runFullTrust" justification on the Submission
  options page silently truncated/rejected a ~700-character answer
  with no visible error — the field just wouldn't validate. Keep any
  Partner Center free-text field under roughly 300 characters to be
  safe. Same failure pattern is reported elsewhere in Partner Center
  (e.g. a documented 200-char limit on the Copyright field).
- **An empty *optional* section can block the whole page.** Store
  listings stayed stuck on "Incomplete" with every required field
  (Product name, Description, at least one correctly-sized screenshot)
  filled in correctly — confirmed not a cache issue across hard
  refresh, full logout/login, a different browser, and a different OS.
  The actual cause was the **Store logos** section (9:16 Poster art /
  1:1 Box art / Store display images) — all marked optional in the UI,
  but something in a partial/stale upload state there was silently
  blocking the section status. Fix: clear/delete anything in Store
  logos and save; Store defaults to the icon baked into the MSIX
  package itself. General lesson: if a section won't go "Complete" and
  every visibly-required field is right, systematically clear the
  *optional* fields/uploads one at a time — that's where this bug
  tends to hide.
- **`build_msix_local.ps1` downloaded via browser needs unblocking.**
  If PowerShell refuses to run the script with "not digitally signed",
  it's Windows' Mark-of-the-Web flag from the download, not an actual
  execution-policy problem:
  ```powershell
  Unblock-File -Path .\packaging\msix\build_msix_local.ps1
  ```

## Version numbering

MSIX requires a strict 4-part numeric `Package/Identity/@Version`
(`Major.Minor.Build.Revision`) — it does **not** accept OpenSAK's
`-beta.N` suffix. For this prototype, `build_msix_local.ps1` takes an
explicit `-Version` (default `1.17.2.0`, i.e. the beta suffix dropped and
`.0` appended). If MSIX moves past the prototype stage, step 3 (CI
integration) will need a small script to derive this automatically from
`src/opensak/__init__.py`'s `__version__` — deliberately not built yet
since it's premature before we know MSIX is viable at all.

## Runbook: publishing a new version (post-prototype)

Until CI integration (step 3) lands, every new build follows this
manual sequence on the Windows machine + browser:

1. **On Windows:** pull the latest branch/tag, then rebuild with the
   real (not dev-test) identity values:
   ```powershell
   git fetch origin <branch>
   git checkout <branch>
   git pull
   .\packaging\msix\build_msix_local.ps1 `
       -IdentityName "AgreeDK.OpenSAK" `
       -PublisherCN  "CN=12DE14F4-8896-42D3-BB58-EA4A95758F5C" `
       -PublisherDisplayName "AgreeDK" `
       -Version "<new 4-part version>"
   ```
   (Don't add `-InstallAfterBuild` unless you specifically want to
   sideload-test this build — the file you need for Partner Center is
   the same either way.)
2. **Optional but recommended:** sideload-install and re-run the
   checklist from "What to actually check once it's installed" above,
   especially after any change touching packaging, dependencies, or
   the Qt/QtWebEngine setup.
3. **In Partner Center (Linux or Windows browser):** open the OpenSAK
   product → Packages → remove the old `.msix` → upload the new one →
   confirm it shows "Validated"/"Complete".
4. Review the other submission sections in case anything needs
   updating for this release (e.g. "What's new in this version" release
   notes) — most sections should carry over unchanged from the last
   submission.
5. **Submit for certification.** Wait for the pass/fail email.
6. Once CI integration (step 3) exists, steps 1–2 become automatic on
   tag/release; steps 3–5 (Partner Center) stay manual until/unless the
   Store Submission API is worth adopting — no plan to do that yet.

## Files in this directory

| File | Purpose |
|---|---|
| `AppxManifest.xml.template` | Manifest template — see comments inside for each placeholder |
| `build_msix_local.ps1` | One-shot local build → package → sign → (optionally) install |
| `generate_assets.py` | Generates the required tile/logo PNGs from `assets/icons/opensak_512.png` |
| `assets/` | Generated image output (gitignored — regenerated by `generate_assets.py`) |
