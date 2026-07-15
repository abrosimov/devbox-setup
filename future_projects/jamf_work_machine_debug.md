# JAMF work-machine debug — running devbox-setup on a Jamf-enrolled Mac

Status: NOT STARTED — planned hands-on session on the work laptop "in a few days".
Origin: risk analysis performed 2026-07-16 (this repo, `work` profile). The work
machine is reportedly *not* strictly locked down, so most items below will pass —
this file is the triage list for the ones that might not.

## Goal

Run `make work` on the Jamf-enrolled machine and catalogue what actually breaks
vs. what the analysis predicted. Confirm or refute each hypothesis empirically,
then decide per item: leave as-is / add a Jamf-detect skip / coordinate with IT.

## Step 0 — probe the actual MDM posture first (before running anything)

Run these read-only checks and record the output; every downstream expectation
depends on them.

```bash
# Am I a local admin? (governs the entire privileged path)
id -Gn | tr ' ' '\n' | grep -q '^admin$' && echo "ADMIN" || echo "STANDARD"

# Is the Mac MDM-enrolled, and by whom? User-Approved?
profiles status -type enrollment
sudo profiles show -type enrollment    # needs admin; shows MDM server URL

# What configuration profiles are installed? (look for Security, Energy Saver,
# PPPC, System Extensions, Restricted Software, WARP)
sudo profiles show                     # full payload dump
ls -la /Library/Managed\ Preferences/  # forced-preference plists land here
ls -la /Library/Managed\ Preferences/$USER/ 2>/dev/null

# Gatekeeper state (is it pinned by a profile?)
spctl --status
spctl --assess -vv /System/Applications/Calculator.app 2>&1 | head

# Existing system/network extensions + login items (BTM)
systemextensionsctl list
sfltool dumpbtm 2>/dev/null | head -50

# Is a corporate VPN / WARP already deployed?
ls -la /Library/Managed\ Preferences/com.cloudflare.warp.plist 2>/dev/null
scutil --nwi
networksetup -listallnetworkservices

# DDM-managed PAM/sudo overlay present? (macOS 14+)
ls -la /private/var/db/ManagedConfigurationFiles/ 2>/dev/null

# Egress: can we even reach the tool mirrors (or is there an inspecting proxy)?
for h in dl.k8s.io proxy.golang.org sum.golang.org registry.npmjs.org pypi.org \
         github.com tuf-repo-cdn.sigstore.dev; do
  echo -n "$h: "; curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' \
    --max-time 6 "https://$h" 2>&1 || echo FAIL
done
```

If Step 0 says STANDARD (no admin), stop and expect the whole `become` path to
fail at the sudo boundary — that is the single biggest gate.

## Triage checklist (ordered by predicted severity)

Each item: hypothesis → quick test → likely mitigation. Full citations live in
the 2026-07-16 analysis session; only the load-bearing facts are repeated here.

### 1. Cloudflare WARP — do NOT install blind (HIGH)
- Hypothesis: a managed `com.cloudflare.warp.plist` (if IT deploys WARP) silently
  forces our client into the corporate org; or it collides with the sanctioned
  ZTNA (DNS/route tug-of-war). Managed plist wins over local settings by design.
- Test: Step 0 WARP-plist check; `scutil --nwi` before/after; check for an
  existing VPN/content-filter network extension in `systemextensionsctl list`.
- Mitigation: drop `cloudflare-warp` from the `work` cask list unless IT confirms
  it is unmanaged and no other ZTNA is present. Candidate: move it out of the
  base `no_binaries` list into a personal-only overlay.

### 2. Docker Desktop / OrbStack licensing (HIGH, licensing not technical)
- Hypothesis: both require a paid seat for commercial use (Docker: >250 employees
  OR >$10M revenue; OrbStack: any business use). `work` profile currently pulls
  `orbstack`.
- Test: confirm company size + whether IT already holds Docker/OrbStack seats.
- Mitigation: swap the `work` container runtime to Podman + Lima (already in the
  package list, Apache-2.0, no seat). Edit `profiles/work.yml` → drop `orbstack`.

### 3. Karabiner-Elements DriverKit extension (HIGH)
- Hypothesis: DEXT team `G43BCU2T37` must be on a System-Extensions allowlist; a
  restrictive allowlist with `AllowUserOverrides=false` blocks it silently and
  remapping is dead. Apple silicon also needs an escrowed bootstrap token.
- Test: `systemextensionsctl list` after install — look for `org.pqrs...` reaching
  `[activated enabled]`; watch for a "driver not activated" alert.
- Mitigation: ask IT to allowlist `G43BCU2T37`, or accept built-in-keyboard remap
  loss on the work machine (Kinesis has its own ZMK anyway).

### 4. sudo password + SSH passphrase in login keychain (MED–HIGH)
- Hypothesis: caching a sudo-usable credential at rest may trip a corporate
  credential-hygiene baseline; Platform-SSO / MDM password rotation can silently
  invalidate the stored item and break `become`/ssh-add.
- Test: after an IdP password change, re-run and see if keychain lookups fail;
  check whether the account is Platform-SSO (`app-sso platform -s`).
- Mitigation: acceptable if lenient; otherwise switch sudo to interactive prompt
  for the work profile and skip `configure_ssh_keychain` persistence.

### 5. `DevToolsSecurity --enable` (MED — most likely EDR/compliance trigger)
- Hypothesis: enabling unprompted debugger/task-port attach is exactly what a
  hardened EDR baseline watches for.
- Test: run it, then check whether a compliance/EDR alert fires (ask IT / watch
  the Jamf inventory). `DevToolsSecurity --status` to confirm state.
- Mitigation: gate this task behind a `work`-profile opt-out var; coordinate with
  IT before enabling.

### 6. `xattr -rd com.apple.quarantine` de-quarantine (MED)
- Hypothesis: only fires if `devbox_trusted_unsigned_casks` is non-empty (it is
  `[]` by default). Bypasses a Gatekeeper prompt — FIM/EDR may flag as tampering.
  SIP + notarization-revocation + XProtect Remediator remain active regardless.
- Test: keep the list empty on work; if a cask needs it, vet with IT first.
- Mitigation: leave `devbox_trusted_unsigned_casks: []` on the work profile.

### 7. osascript → System Events login items (MED)
- Hypothesis: fails with AppleScript error -1743 under a deny-PPPC or when run
  headless/as root; needs a source-app + System-Events PPPC pair to pre-approve.
- Test: run `configure_login_items` interactively; grant the one-time TCC prompt;
  if it errors -1743, PPPC is blocking Apple Events for the terminal.
- Mitigation: task already tolerates failure (`failed_when: false`); accept that
  autostart registration may no-op, register apps' own "launch at login" instead.

### 8. Direct binary pulls — kubectl / go / npm / pypi (MED)
- Hypothesis: a corporate egress proxy / TLS-inspection breaks checksum
  verification (`sum.golang.org`, kubectl SHA256) or blocks the hosts outright.
- Test: Step 0 egress loop; watch for non-200 or `ssl_verify_result != 0`.
- Mitigation: point Go/npm/pip at the corporate artifact proxy; if TLS-inspected,
  import the corporate root CA or use the proxy's trust store.

### 9. `/etc/pam.d/sudo_local` + `/etc/sudoers.d/*` edits (MED)
- Hypothesis: a DDM-managed PAM/sudo overlay (macOS 14+) at
  `/private/var/db/ManagedConfigurationFiles/…` takes precedence and is
  tamper-resistant, so our local edit may be silently ignored (not reverted).
- Test: Step 0 ManagedConfigurationFiles check; after edit, `sudo -v` behaviour.
- Mitigation: if a managed overlay exists, our pam edit is a no-op — harmless;
  leave as-is. Only a concern if it errors.

### 10. `pmset -a disablesleep 1` (LOW–MED)
- Hypothesis: a Jamf Energy Saver profile reverts pmset values after reboot /
  check-in. (Whether the `disablesleep` clamshell bit specifically is profile-
  managed is UNVERIFIED — documented keys are Sleep/DiskSleep/DisplaySleep.)
- Test: set it, reboot, re-check `pmset -g | grep disablesleep`.
- Mitigation: if reverted, accept clamshell sleep on the work machine or ask IT.

### 11. macOS defaults — Dock/Finder/NSGlobal/etc. (LOW)
- Hypothesis: mechanically overridable by a custom profile but rarely managed;
  a forced key wins silently (write persists on disk, app reads managed value).
  No hard error either way.
- Test: after run, spot-check a couple of keys actually took effect in the UI.
- Mitigation: none needed; silent-override is benign.

### 12. Hammerspoon / Raycast Accessibility (LOW–MED)
- Hypothesis: Accessibility CAN be pre-granted via MDM PPPC but only if IT listed
  the app; otherwise interactive-only (fails headless). Deny-PPPC locks it off.
- Test: launch each, confirm the Accessibility toggle can be granted.
- Mitigation: request PPPC Accessibility for both bundle IDs, or grant manually.

### 13. login shell → fish (LOW)
- Hypothesis: on a mobile/AD account the directory `UserShell` attribute
  overwrites the local change on login/sync; PSSO-local accounts usually persist.
- Test: change shell, log out/in, `dscl . -read /Users/$USER UserShell`.
- Mitigation: if it reverts, set the shell via the directory / `dsconfigad -shell`
  or just launch fish from the login shell rc.

## How to resume

1. Read this file.
2. Run Step 0 on the work machine, paste the output back into the session.
3. Walk the triage list top-down, ticking each item PASS / FAIL / N-A.
4. For every FAIL, apply the mitigation and record whether it needs an IT ask or
   a `work`-profile code change (most map to `profiles/work.yml` or a new
   `devbox_extra_*` skip var).
