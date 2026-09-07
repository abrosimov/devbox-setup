# Pub mode hardening — design study

Status: **historical pre-implementation analysis snapshot (2026-09-06)**. Nothing in this
document had been implemented when it was written, and no file under
`roles/devbox/files/.local/bin/`, `roles/devbox/tasks/darwin/`, `roles/devbox/templates/`,
`roles/devbox/files/.config/fish/` or `tests/` was modified while producing it. The repository has
since changed: references below to "current" behaviour, the six-hour lease, recommendations and
open questions describe that earlier baseline, not the present implementation. Use the README,
code and tests as the current specification; this document is retained as a research record.

Goal being served, in the user's words: *pub mode must not get in the way when I am not at the
pub, and must not be globally permanent.*

Evidence convention: every factual claim carries its source inline — `verified: <command>` for a
command actually run on this machine on 2026‑09‑06, `man <page>` for a manual page read,
`path:line` for a repository file, or an explicit **UNVERIFIED** label. Nothing is asserted from
memory.

---

## 0. Executive summary

| # | Topic | Recommendation | Impact on the stated goal |
|---|-------|----------------|---------------------------|
| 1 | Auto-renew on network identity | **Renew on a gateway-derived network signature, not SSID.** SSID and BSSID are unobtainable (redacted) on macOS 26.5.2. Drop `LEASE_SECONDS` to 30 min, auto-renew while the signature matches, hard-cap total lease at 12 h. Do **not** condition on "bad internet". | **Decisive.** Converts "up to 6 h of tunnel after leaving" into "closes ~2 min after leaving". |
| 2 | Visibility | **Notification on state transitions + one `fish_greeting` line.** No tide item (right prompt already carries 11 items), no sketchybar (not configured, not running). | High — but mostly *because* item 1 removes the "still on at home" case. |
| 3 | Policy-lock trap | **Make it legible, do not engineer around it.** Replace the misleading `already OFF` with an explicit stuck-mode message; switch the probe to `warp-cli settings mode-switch-allowed`. | Low on this laptop (`managed: false`, free account), potentially real on a Zero Trust work laptop. |
| 4 | `pub on` refuses `Connecting` / `Unable to connect` | **Classify statuses into stable / transient / degraded.** Settle transient states for ≤10 s; store the settled status instead of the lossy `previous_connected` boolean and restore a degraded pre-state best-effort with a bounded, non-fatal wait; refuse on `Registration Missing` **and on any status outside the known set**. | High — this is the failure at the pub itself. |
| 5 | 2-minute blocking waits | **Split the budget: 25 s activate, 20 s interactive restore, 60 s reconciler restore.** Emit progress. The reconciler already retries, so a long blocking restore is waste. | Medium — usability, not correctness. |
| 6 | One runtime across laptops | **Deferred to a separate design pass.** The finding stands — `/usr/bin/python3` is the `xcode-select` shim (same inode as `/usr/bin/git`), not a real interpreter, and the plist and the shebang can resolve differently on one machine. The remedy is entangled with packaging (§B) and is out of scope here. | Medium — reliability across machines. |
| 7 | Leftover candidate plist | **Stage the candidate outside `/Library/LaunchDaemons/` and delete it after a successful bootstrap.** Keep the marker protocol — it is deliberate crash safety. | Low — hygiene. |
| 8 | `StartInterval` 60 → 300 | **Revisit: keep 60 s.** `man launchd.plist` states a sleeping system *misses* the interval, so the interval is also the post-wake detection latency. With item 1, 300 s means up to 5 min of tunnel at home. Idle cost is ~1 min CPU/day. | Medium — 300 s would partially undo item 1. |

Items 1 and 4 are the ones worth doing here. Items 3, 5, 7 are small corrections. Item 8 is a
recommendation to *not* make a change that was provisionally agreed. **Item 6 and §B are carved
out of this pass entirely** — the runtime problem and the packaging question are one decision, and
it is being taken separately.

Three research findings changed the design materially and are called out where they land:
SSID redaction (§1), the `/usr/bin/python3` inode identity (§6), and the `StartInterval`
sleep semantics (§8).

Baseline fact for sequencing: **pub mode is not deployed on this laptop.** There is
no `/Library/LaunchDaemons/local.pub-lease.plist`, no `~/.local/bin/pub-lease`, no
`~/.local/state/pub-lease/` and no `~/Library/Logs/pub-lease.log`
(verified: `ls /Library/LaunchDaemons/ | grep -i pub` → exit 1; `ls ~/.local/bin/pub-lease` →
No such file; `ls ~/.local/state/pub-lease` → No such file; `ls -la ~/Library/Logs/pub-lease.log`
→ No such file).

That is an observation about **this one machine at this moment**, not a repository invariant, and
it does not license changes that break upgrade paths. The code deliberately carries compatibility
surface for state it expects to meet in the field: v1 lease and recovery handling
(`pub-lease.py:70-112`, with `v1-*` and `bash-*` fixtures under
`tests/scripts/fixtures/pub_lease/`), teardown of a legacy GUI LaunchAgent
(`configure_pub_mode.yml:257-268`, `:339-350`), and a disabled-profile teardown that **depends on
an already-installed controller being executable** and refuses to proceed without one when
recovery metadata exists (`:298-317`). Any change to the on-disk lease shape or to the controller's
invocation contract has to keep those working.

Platform under test: macOS 26.5.2, build 25F84 (verified: `sw_vers`);
`warp-cli 2026.7.1376.0` at `/usr/local/bin/warp-cli` (verified: `warp-cli --version`).

---

## 1. Auto-renew conditioned on network identity

### 1.1 The SSID half of the request is not achievable as stated

The user asked for renewal conditioned on "a specific SSID". On this macOS version the SSID is
not readable by an unprivileged process through any of the usual channels. Every candidate was
tested:

| Source | Command run | Result |
|---|---|---|
| `networksetup` | `networksetup -getairportnetwork en0` | `You are not associated with an AirPort network.` — and **exit code 0** — while `en0` simultaneously holds `192.168.1.11` (verified) |
| `ipconfig` | `ipconfig getsummary en0` | `BSSID : <redacted>` (verified) |
| `system_profiler` | `system_profiler SPAirPortDataType` | `Current Network Information:` → `<redacted>:`, and every entry under `Other Local Wi-Fi Networks:` is `<redacted>` (verified) |
| `ioreg` | `ioreg -r -c IO80211Interface \| grep IO80211SSID` | `"IO80211SSID" = "<SSID Redacted>"` (verified) |
| `wdutil` | `wdutil info` | `usage: sudo wdutil info` — requires root (verified) |

Two consequences worth stating plainly:

* The redaction is applied at the data-source level, not by one tool. `ioreg` returning the
  literal string `<SSID Redacted>` shows the kernel-facing property itself is scrubbed for
  unauthorised callers.
* `networksetup -getairportnetwork` **returns exit status 0 while lying**. Any implementation
  that branched on its exit code would silently mis-detect. This is a trap worth recording even
  though we are not going to use the command.

What survives redaction, from the same `ipconfig getsummary en0` run (verified):

* `Router : 192.168.1.1`
* DHCP `server_identifier (ip): 192.168.1.1`
* `subnet_mask (ip): 255.255.255.0`
* DHCP `option_125` vendor payload containing `ETISALAT-HG6244B` and `K2411G03044`
  — router model and serial
* `network_time_protocol_servers (ip_mult): {213.42.2.60}`
* IPv6 RA `source link-address option (1), length 8 (1): c4:0f:a6:64:be:10`

And from adjacent commands (verified):

* `arp -n 192.168.1.1` → `? (192.168.1.1) at c4:f:a6:64:be:10 on en0 ifscope [ethernet]`
  — the gateway MAC, **not** redacted
* `echo 'show State:/Network/Global/IPv4' | scutil` → `PrimaryInterface : en0`,
  `PrimaryService : 2262B572-5785-46BF-AE88-7C003BE61B46`, `Router : 192.168.1.1`
* `system_profiler SPAirPortDataType` still leaks non-identifying radio facts even when the SSID
  is redacted: `Channel: 8 (2GHz, 20MHz)`, `Security: WPA2 Personal`, `PHY Mode: 802.11n`,
  `Country Code: AE`

So a gateway-derived signature is not merely a fallback — it is strictly better than SSID here,
because it needs no Location Services authorisation, no root, and no GUI session. That was the
hypothesis in the brief and it is confirmed.

The parent review's assumption that the machine sits on Ethernet at a desk is wrong, incidentally:
`scutil --nwi` reports `Network interfaces: en0` only, and `ipconfig getsummary en16` reports
`Active : FALSE` / `LastFailureStatus : media inactive` (verified). The Thunderbolt Ethernet port
exists but is unused. The signature design must not assume Wi-Fi *or* Ethernet.

### 1.2 `warp-cli trusted` cannot do this job

Full help read (verified: `warp-cli trusted --help`, `warp-cli trusted ssid --help`):

```
Configure trusted networks where the client will be automatically disabled (Consumer only)
Commands:
  ssid      Configure trusted Wi-Fi networks for which the client will be automatically disconnected
  ethernet  Automatically disconnect on all ethernet networks (Consumer only)
  wifi      Automatically disconnect on all Wi-Fi networks (Consumer only)
```

`warp-cli trusted ssid` has `list / add / remove / reset`. Three reasons it does not serve:

1. **Wrong polarity.** It names networks where WARP is *disabled*. Pub mode needs the inverse —
   a network where a tunnel is *wanted*. Encoding "everywhere except the pub is trusted" would
   require enumerating every network the laptop will ever join.
2. **Wrong action.** It "automatically disconnects" the client. Pub mode's contract is to restore
   a *captured previous mode and connection state* — `proxy` + disconnected on this machine
   (verified: `warp-cli -j settings` → `"operation_mode": "proxy"`; `warp-cli -j status` →
   `"status": "Disconnected", "reason": "Manual"`). A blanket disconnect discards the mode half
   of that contract entirely.
3. **It takes an SSID as input.** Given §1.1, the user cannot reliably read back what to type,
   and the controller cannot verify it. It also mutates WARP settings, which the ownership model
   in `pub-lease.py:541-561` treats as an external actor.

It is however evidence that WARP itself has privileged SSID access — a managed path exists that
we do not. Not usable, but worth knowing.

### 1.3 "Bad internet" is the wrong renewal trigger

Reason codes exist in the daemon binary (verified: `strings /usr/local/bin/warp-cli` — the enum
blob contains `Manual`, `DisabledForWiFi`, `DisabledForEthernet`, `DisabledForNetwork`,
`DisabledByOverride`, `Paused`, `InternalDNSError`, `InternalTunnelError`, `InternalmTLSError`,
`SettingsChanged`, `RegistrationChanged`, `EmergencyDisconnect`, `TLSInterceptionDetected`,
`HostUnreachable`, `DNSLookupFailed`, `Unknown`, `NoNetwork`, `RegistrationMissing`,
`FailedToSetMtls`, `ConnectivityCheckFailed`, `Port53Bound`, `ProxyAddressBound`,
`TLSInterceptionBlockingDOH`, `HappyEyeballsFailed`, `LocalPolicyFileFailedToParse`,
`CaptivePortalTimedOut`, `InsufficientSystemResource`, `ConflictingNetwork`,
`PacketTunnelUnavailable`, `FailedToExcludeLan`). The live JSON exposes one:
`warp-cli -j status` → `{"status": "Disconnected", "reason": "Manual"}` (verified).

They are the wrong signal for renewal, for a structural reason: **once the lease is active WARP is
connected, so the reason codes that describe "the local network is hostile" stop firing.** The
tunnel is precisely what hides the hostility. Conditioning renewal on observing bad internet
would mean the lease decays as soon as it starts working.

There is a second reason: false-positive cost is asymmetric. Dropping the tunnel mid-upload
because a probe blipped is far worse than keeping it three minutes too long.

**Decision: renewal is conditioned on network identity only.** "Bad internet" is what makes the
human type `pub on`; the machine does not need to re-derive it. The reason codes are still useful
— but at *activation* time, for the diagnostics and status classification in §4.

### 1.4 Options

| # | Mechanism | Evidence it works | Cost | Failure modes | Reversibility |
|---|---|---|---|---|---|
| A | Status quo — fixed 6 h, manual `off` | `pub-lease.py:563-587` closes only on expiry or boot change | zero | up to 6 h of tunnel after leaving the pub | n/a |
| B | Shorten `LEASE_SECONDS` to 30–60 min, no auto-renew | one-constant change | trivial | forces `pub on` every half hour during a long session; annoying enough to be worked around | trivial |
| C | **Gateway-derived network signature; renew while it matches, hard cap total** | §1.1 — all components read without root/GUI (verified) | one `scutil` + one `arp` per reconcile | signature unobtainable while asleep or link-down; NAT-less/roaming networks | trivial — signature is an optional validated lease field, absent ⇒ old behaviour |
| D | Signature + a live connectivity probe | probe adds an outbound request per minute from a background daemon | high | probe traffic through the tunnel; false positives; privacy surface | medium |
| E | Resident daemon watching `com.apple.system.config.network_change` | notify key exists; `notifyutil` present at `/usr/bin/notifyutil` (verified). `LaunchEvents` needs `xpc_set_event_stream_handler(3)` — a Python script cannot supply it (`man launchd.plist`) | high — turns a one-shot into a long-running daemon | resident process lifecycle, leak risk, harder to test | poor |

Option E deserves an explicit kill note: `man launchd.plist` on `LaunchEvents` says the job
"promises to use the `xpc_set_event_stream_handler(3)` API to consume events". A stdlib Python
process cannot. `KeepAlive`/`NetworkState` is documented as "no longer implemented as it never
acted how most users expected". `WatchPaths` is documented as "highly discouraged, as filesystem
event monitoring is highly race-prone". Every launchd-native event route is closed for this
program shape.

**Recommendation: C.**

Reason: it is the only option that closes the actual gap (leaving the pub) without inventing a
new process model, and every input it needs was verified readable in the exact privilege context
the daemon runs in — no root, no GUI session, no Location Services.

### 1.5 Proposed state machine

Signature definition — a hash over an ordered tuple, so it is opaque in the lease file and does
not leak the home network layout into a file that might be quoted in a bug report:

```
signature = sha256(
    router_ip                # scutil: State:/Network/Global/IPv4 → Router
  + gateway_mac_normalised   # arp -n <router_ip>, zero-padded octets
)
```

Two components, both verified obtainable above. The primary interface
(`scutil: State:/Network/Global/IPv4 → PrimaryInterface`) is still read, but only as the *means*
of locating the default route and its ARP entry — it is deliberately **not** hashed. Hashing it
would make the attachment method part of the network's identity, so moving from Wi-Fi to a
Thunderbolt dock behind the same router (`en0` → `en16`) would read as a different network and
close the lease. With the interface excluded, `en0` → `en16` on the same gateway is the same
network, which is what "network identity" should mean.

`arp -n` output must be normalised: the observed form is `c4:f:a6:64:be:10` — **octets are not
zero-padded**, whereas the IPv6 RA in the same machine's state renders the same address as
`c4:0f:a6:64:be:10` (both verified). An implementation that compared the two raw strings would see
a spurious mismatch. Normalise to zero-padded lower case before hashing.

DHCP `option_125` (`ETISALAT-HG6244B`) was considered as a third component and rejected: it is
present on this network but is vendor-optional, so its absence elsewhere would make the signature
non-comparable across networks. Router IP + gateway MAC is sufficient to distinguish a pub from
home; a collision requires two networks with the same private router IP *and* the same gateway
MAC, which does not happen outside deliberate spoofing.

Lease additions — **promoted to validated first-class fields, not left in `extras`**:

* `network_signature: str | None` — captured at activation
* `network_misses: int` — consecutive reconciles that saw a different signature
* `hard_expires_at: float | None` — `started_at + MAX_LEASE_SECONDS`, never extended

The obvious cheap route — drop them into the existing `extras` dict and rely on the round-trip
preservation already tested at `tests/scripts/test_pub_lease.py:405` — is wrong, and this is the
single most important correctness point in §1. `LeaseState.from_object` collects every
unrecognised key into `extras` with **no validation whatsoever**:

```python
extras={key: item for key, item in fields.items() if key not in _STATE_FIELDS},
```
(`pub-lease.py:111`)

That test proves round-tripping, not fitness for driving behaviour. A lease carrying
`"network_misses": "1"` loads cleanly, and the first `network_misses + 1` in the reconciler raises
`TypeError`. Nothing catches it: `_run_locked` catches only `OSError` (`:890`) and `main`
(`:897-918`) catches nothing. The result is a traceback in `~/Library/Logs/pub-lease.log` every
60 s and a lease that can never close — the exact failure mode this whole section exists to
prevent. A negative `network_misses` would never reach the miss limit; a non-finite or absurd
`hard_expires_at` would silently defeat the cap.

Validation rules, applied in `from_object` alongside the existing field checks and raising
`StateError` on violation, so a bad file is quarantined and recovered through the paths that
already exist:

| Field | Rule |
|---|---|
| `network_signature` | absent/`null`, or a string matching `^[0-9a-f]{64}$` (the SHA-256 hex digest, nothing else) |
| `network_misses` | `type(v) is int` — explicitly **not** `bool`, matching the `previous_connected` treatment at `:99` — and `0 <= v <= NETWORK_MISS_LIMIT` |
| `hard_expires_at` | absent/`null`, or finite per the existing `_is_number` helper (`:132-133`), and `>= started_at` |

Absent is legal for all three and means "pre-upgrade lease": the reconciler then behaves exactly as
today. Present-but-invalid is rejected, never coerced.

**Version strategy: the file stays `version: 1`.** The three fields are optional additions to the
v1 schema, so an old lease loads unchanged and a new lease is still read by anything that only
knows v1. `from_object` continues to reject `version != 1` (`:85-86`), and the parametrised
rejection of `("version", 2)` at `tests/scripts/test_pub_lease.py:380` stays as it is. A version
bump would buy nothing here and would invalidate a pinned test for no gain — reserve `version: 2`
for a change that actually breaks the v1 shape.

Constants:

* `LEASE_SECONDS = 1_800` (30 min) — the renewal window, not the session length
* `MAX_LEASE_SECONDS = 43_200` (12 h) — the hard ceiling that satisfies "must not be globally
  permanent"
* `NETWORK_MISS_LIMIT = 2` — anti-flap

Reconcile logic, inserted after the existing ownership check and before `_close_if_needed`.

**Control flow, stated explicitly, because leaving it implicit is the failure mode.** The renewal
step has exactly two exits:

* **Renew or do nothing ⇒ fall through.** It updates `expires_at` and `network_misses` in the
  lease, or it leaves the lease untouched, and control proceeds into `_close_if_needed`
  (`pub-lease.py:563-587`) exactly as today.
* **Close ⇒ perform the restore and return that outcome.** The two closing rows below
  (`hard_expires_at` reached, and `NETWORK_MISS_LIMIT` reached) call `_restore_previous_state` and
  return `RESTORED` or `FAILED` like the existing closure paths, rather than falling through into
  `_close_if_needed` with metadata that has just been deleted.

There is no path on which renewal both extends a lease and suppresses an existing closure, because
none of `_close_if_needed`'s closures depend on `expires_at` having been left alone:

* The phase branch (`:564-572`) fires for `activating` and `restoring` and is **unconditional with
  respect to `expires_at`** — moving the expiry cannot suppress it, so an interrupted transition or
  a previously failed restore is still completed on the next tick.
* The boot check (`:580`) closes on `boot_id != state.boot_session` regardless of how often
  `expires_at` has advanced.

Renewal is nevertheless **guarded**, so that it never touches a lease that the existing path is
about to close for another reason. Renewal is considered only when both hold:

* `state.phase == "active"` — `activating` and `restoring` are transitions, not live leases, and
  belong to `_close_if_needed`;
* `now < state.expires_at` — a lease whose expiry has already elapsed is dead and is not
  resurrected. Renewal extends a live lease; it never revives an expired one.

If either guard fails, the renewal step does nothing at all — no signature read, no `expires_at`
write, no miss counted — and `_close_if_needed` handles the lease on its existing terms.

| Observation (all rows presuppose `phase == "active"` and `now < expires_at`) | Action |
|---|---|
| signature == stored, and `now < hard_expires_at` | renew: `expires_at = min(now + LEASE_SECONDS, hard_expires_at)`; `network_misses = 0` |
| signature == stored, and `now >= hard_expires_at` | close and restore — reason "maximum lease duration reached" |
| signature != stored | `network_misses += 1`; close and restore when it reaches `NETWORK_MISS_LIMIT`, reason "network changed" |
| signature unobtainable (no primary service, no ARP entry) | **neither renew nor count a miss** — the lease decays on its own `expires_at` clock |
| no `network_signature` in the lease (pre-upgrade file) | behave exactly as today |

The "unobtainable" row is the important one. Asleep, link-down, and mid-DHCP all look the same
from the reconciler, and all three are transient. Not renewing is the safe response: the lease
simply ages out through the existing expiry path.

**What the lid-closed-in-a-bag case actually does**, since it has two outcomes and only one of them
is the reassuring one:

* *Bag left at the pub* — you close the lid on network A and reopen it on network A hours later.
  The lease will normally have expired while asleep (`StartInterval` firings are missed during
  sleep, §8), so the guard `now < expires_at` fails, renewal is skipped entirely, and
  `_close_if_needed` closes the lease on expiry. If instead the lid is opened within the 30 min
  window, the signature still matches and the lease renews — which is correct and is the whole
  point of signature-based renewal: you are still at the pub.
* *Bag taken home* — you reopen on network B. Either the lease already expired during the sleep and
  is closed on expiry, or it is still live and the signature mismatch closes it after
  `NETWORK_MISS_LIMIT` reconciles, ~2 min.

Both paths end with the tunnel down and WARP restored, but by different mechanisms, and it is worth
being precise about which: "the lease dies of old age within 30 minutes" holds for the taken-home
variant and for a long sleep, **not** as a general property. A lid reopened at the pub inside the
window renews, by design. The bound that always holds is `hard_expires_at`, not the renewal window.

Anti-flap rationale for `NETWORK_MISS_LIMIT = 2`: at a 60 s interval that is a ~2 min close
latency after genuinely leaving, and it absorbs a single reconcile landing during a DHCP renewal
or a Wi-Fi roam. Combined with the "unobtainable ⇒ no miss" rule, a roam that briefly drops the
primary service does not count against the lease at all.

Interaction with `pub on`: `_renew` (`pub-lease.py:398-419`) must refresh `network_signature`
from the live network, so that a deliberate `pub on` at a *new* pub re-homes the lease rather
than immediately failing the signature check. It must **not** move `hard_expires_at`.

---

## 2. Making an active lease visible — without the tide prompt

### 2.1 The user's objection is grounded

Read from `roles/devbox/files/.config/fish/conf.d/tide_items.fish:6-9`:

```
set -g tide_left_prompt_items vi_mode os proj_pwd git
set -g tide_right_prompt_items status cmd_duration context jobs fpf_drift narrative_drift node python go kubectl time
```

Fifteen items across both sides, rendered with
`--powerline_prompt_style='One line' --prompt_spacing=Compact`
(`roles/devbox/defaults/main/shell.yml:74-85`). On a laptop display without an external monitor
this is already at the limit. A sixteenth item is the wrong answer and the option is dropped.

### 2.2 What is actually available on this machine

| Component | State | Evidence |
|---|---|---|
| `sketchybar` | installed as a formula, **no config in the repo, no `~/.config/sketchybar/`, not running** | `packages.yml:111`; `find … -ipath "*sketchybar*"` under `roles/devbox` → no hits; `ls ~/.config/sketchybar/` → No such file; `ps -Ao comm=` shows no sketchybar (all verified) |
| `borders` (JankyBorders) | **running**, started as a user LaunchAgent | `ps -Ao comm=` → `/opt/homebrew/opt/borders/bin/borders`; `ls ~/Library/LaunchAgents/` → `homebrew.mxcl.borders.plist` (verified) |
| AeroSpace | **running** | `ps -Ao comm=` → `/Applications/AeroSpace.app/Contents/MacOS/AeroSpace` (verified) |
| kitty | running, **remote control enabled** | `kitty.conf:90` → `allow_remote_control yes` (verified) |
| WARP menu-bar icon | present by definition of the cask | — |

The sketchybar option therefore costs a whole new subsystem — config tree, LaunchAgent, event
plumbing — not "add an item". That reframes it from cheap to expensive and it drops to last place.

`borders` is genuinely cheap: `bordersrc` ends with `borders "${options[@]}"` and the file's own
comment states "borders execs this file on startup and **pushes the options to the running
daemon**" (`roles/devbox/files/.config/borders/bordersrc:16-22`). So
`borders active_color=0xffXXXXXX` at runtime is a supported reconfiguration path.

### 2.3 Can the daemon reach the GUI at all?

`man launchctl` on `asuser`: *"This executes the given command in as similar an execution context
as possible to that of the target user's bootstrap. Adopted attributes include the Mach bootstrap
namespace, exception server and security audit session."* That is the documented bridge from the
system domain into the user's GUI session.

`launchctl asuser $(id -u) /usr/bin/true` returned exit 0 when run **as the ordinary user
targeting their own uid** (verified). So the controller — which runs as the user via `UserName` in
`local.pub-lease.plist.j2:8-9`, not as root — can invoke `asuser` against itself without
privilege escalation.

**UNVERIFIED:** whether a notification posted this way is actually *delivered* by Notification
Centre. Proving that requires running `osascript -e 'display notification …'` from a
system-domain job, which means installing the daemon — outside the analysis-only remit. It is
listed as a live test in §A.

Same caveat for `borders`: the `borders` CLI talks to the running borders daemon, which lives in
the user's GUI session. Whether that IPC succeeds from the system bootstrap namespace without
`asuser` is **UNVERIFIED**.

### 2.4 Options

| # | Mechanism | Evidence | Cost | Failure modes | Reversibility |
|---|---|---|---|---|---|
| A | Notification on state transitions (activate / auto-restore / ownership lost) | `launchctl asuser` bridge verified to execute; delivery UNVERIFIED | small — one subprocess on transitions only | silent no-op if delivery fails; Focus modes suppress it | trivial |
| B | `fish_greeting` line reporting the lease's actual phase and validity, parsed from `lease.json` | phase and `expires_at` are already in the file (`pub-lease.py:114-129`) | small — one JSON read, **no subprocess** | only visible on a new shell | trivial |
| C | `borders active_color` while a lease is active | runtime push documented in `bordersrc:16-22` | small | IPC from system domain UNVERIFIED; fights any future borders config; invisible when no window is focused | needs a restore-colour path — a crash leaves the wrong colour |
| D | sketchybar item | nothing exists yet | **high** — new subsystem | a whole config surface to own | poor |
| E | Rely on the WARP menu-bar icon alone | already present | zero | cannot distinguish "pub lease" from "I enabled WARP myself" — which is exactly the distinction that matters | n/a |

**Recommendation: A + B.**

Reason: the user named two needs — knowing the tunnel is still on when they get home, and knowing
when it auto-restored. **Item 1 removes the first need almost entirely**: with signature-based
closing, the lease is gone ~2 min after leaving the pub, so "still on at home" stops being a
recurring state. What remains is the *event* — "it just closed itself" — and an event is what a
notification is for. `fish_greeting` is a free backstop for the residual case (lease still open
because you are still on the pub network and you opened a shell).

C is attractive and cheap but carries a real hazard: a crashed controller leaves the border
colour wrong with no owner to reset it, and the IPC path is unverified. Worth revisiting after
A is proven, not before. D is rejected on cost. E is rejected because it cannot express the
distinction the user needs.

**Two constraints on B, both load-bearing.**

*It must read the phase, not merely the file's existence.* `test -f lease.json` does not mean
"pub mode is active". `lease.json` is also present while `phase == "restoring"` — written by
`_restore_previous_state` **before** WARP is touched (`pub-lease.py:608`) — after a restore that
failed and left the phase behind, while `phase == "activating"` mid-transition, when the contents
are corrupt (which is why `load_lease` returns `None` rather than raising, `:227-235`), and during
the whole window between `expires_at` elapsing and the next reconcile closing the lease. A greeting
keyed on existence would assert "tunnel on" in at least four states where it is not. It must parse
`phase` and `expires_at` and say what is actually true: active with time remaining, restoring,
expired and awaiting the reconciler, or metadata present but unreadable.

*It must not invoke `pub-lease status` or `warp-cli`.* The obvious implementation — shell out to
`pub-lease status` — costs two `warp-cli` subprocesses on **every new shell**, because `status`
calls `_mode_or_unknown` and `_status_or_unknown` before it looks at the lease at all (`:477-481`).
That is the wrong trade for a greeting line. Read and parse the JSON directly; the file is the
lease's own external-reader contract and is already tested as such
(`tests/scripts/test_pub_lease.py`, `TestPubLeaseStateCompatibility` at `:330`).

---

## 3. The policy-lock trap, in detail

### 3.1 The code path

1. `_reconcile_locked` (`pub-lease.py:505-520`) reads the policy lock before inspecting mode
   ownership: `policy_lock = self._policy_lock()`, then `if policy_lock != "unlocked": return
   self._drop_policy_controlled_lease(policy_lock)`.
2. `_drop_policy_controlled_lease` (`:674-681`) calls `self.store.delete_metadata()` and prints
   `pub: lease ownership lost to WARP policy (...); WARP left unchanged`. It **deletes the lease
   and the recovery snapshot** while leaving WARP in `tunnel_only`.
3. A subsequent `pub off` reaches `off()` (`:460-462`):
   `if not self.store.metadata_exists(): print("pub mode is already OFF"); return 0`.

So after the drop, the machine is in `tunnel_only`, the record of the previous mode is destroyed,
and the tool reports success while doing nothing. There is no supported route back to the prior
mode — `pub off --force` does not help either, because `_handle_failed_reconcile` (`:714-724`) is
only reached when reconcile *fails*, and this path returns `OWNERSHIP_LOST`, not `FAILED`.

The behaviour is deliberate and defensible — the design refuses to fight a policy — but the exit
is silent and lossy.

### 3.2 What `switch_locked` actually is, on this machine

* Current value and provenance: `warp-cli -j settings` →
  `"switch_locked": false` under `settings`, and `"switch_locked": "override"` under `sources`
  (verified). The `override` source is the layering slot, not an active lock — see below.
* `warp-cli override show` → `No override currently set` (verified).
* `warp-cli settings mode-switch-allowed` → `true` (verified). This is a purpose-built single
  value: help text reads *"Outputs true if Teams users should be able to change connection mode,
  or false if not"* (verified: `warp-cli settings --help`).
* Enrolment: `warp-cli -j registration show` → `"managed": false`,
  `"account": {"type": "free", ...}`, `"alternate_networks": []` (verified).

`managed: false` on a `free` account is the decisive fact. The two documented ways to set
`switch_locked` are a Zero Trust / Teams device policy and `warp-cli override <CODE>`, whose help
reads *"Allow temporary overrides of administrative settings"* and whose `unlock` subcommand
*"Temporarily override policies that require the client to stay enabled"* (verified:
`warp-cli override --help`). Both presuppose an organisation. On an unmanaged free account
neither applies.

**Blast radius, honestly scoped:**

* Personal laptop, today: effectively unreachable. This is a low-priority defect.
* Work laptop: the opposite. A work machine enrolled in a corporate Zero Trust org is exactly
  where `switch_locked` becomes true, and where the drop-and-go-silent behaviour would strand the
  machine in `tunnel_only`. Pub mode is currently personal-gated
  (`main_darwin.yml:47-53`, keyed on `cloudflare-warp` in
  `devbox_extra_brew_casks_no_binaries`; `profiles/personal.yml:11`), so this is latent — but it
  becomes live the moment the work profile ever installs WARP.

### 3.3 Options

| # | Mechanism | Evidence | Cost | Failure modes | Reversibility |
|---|---|---|---|---|---|
| A | Keep the drop; **fix the message.** `off()` distinguishes "never had a lease" from "lease dropped, WARP left in `tunnel_only`" via a small breadcrumb file | pure local change | trivial | breadcrumb can go stale if the user fixes WARP by hand | trivial |
| B | Do not delete the recovery snapshot on policy drop; keep it and let `pub off` offer a best-effort restore | `_restore_previous_state` (`:600-626`) already handles a failing `set_mode` | small | retries forever against a policy that will refuse; log noise | easy |
| C | Switch the probe from `settings.switch_locked` to `warp-cli settings mode-switch-allowed` | verified: returns bare `true` | trivial | one more subprocess; parsing a bare token | trivial |
| D | Refuse to activate unless the account is unmanaged (`registration show` → `managed: false`) | verified field exists | small | blocks a legitimate managed-but-unlocked setup | trivial |

**Recommendation: A + C.**

Reason: the design decision to yield to policy is right and should stand — B would have the
controller argue with an administrator. What is wrong is that the user is told `already OFF`
while sitting in `tunnel_only`. A fixes exactly that, and C replaces an inferred boolean with the
vendor's own purpose-built answer. D is rejected: `managed: false` is the *current* state of a
consumer account, and gating activation on it would break the moment the work laptop enrols,
which is the case we most want to keep working.

The breadcrumb in A should record the last-known previous mode as advisory text only — enough
for the message *"pub lease was dropped by WARP policy; WARP is still in tunnel_only, your
previous mode was `proxy`"* — without pretending it is a restorable snapshot.

---

## 4. `pub on` refusing on `Connecting` and `Unable to connect`

### 4.1 The status model, established

Status values, from the daemon's own enum blob
(verified: `strings /usr/local/bin/warp-cli`, the string
`...DisconnectedConnectingConnectednetwork_health...` and the separate
`DisconnectedConnectingConnectedUnable` and `Registration Missing due to: `):

* `Disconnected`
* `Connecting`
* `Connected`
* `Unable to connect`
* `Registration Missing`

**This set is open, not closed.** It is what one version of one binary's string table exposes, and
the repository already assumes more: `tests/scripts/test_pub_lease.py:238` parametrises
`["Connecting", "Disconnecting", "Unknown"]`, and `Disconnecting` appears nowhere in the enum blob
above. That test is therefore not a claim that WARP emits `Disconnecting` — it is a deliberate pin
on **fail-closed behaviour for any status the controller does not recognise**. Any classification
proposed below must keep that property: a status outside the known set is a refusal, not a
default-to-something branch.

Live shape (verified: `warp-cli -j status`): `{"status": "Disconnected", "reason": "Manual"}` —
so `status` and `reason` are separate fields, and the reason enum listed in §1.3 attaches to the
status rather than replacing it.

The current gate, `_previous_warp_state` (`pub-lease.py:709-711`):

```python
if previous_status not in {"Connected", "Disconnected"}:
    return self._fail(f"WARP is not in a stable state: {previous_status}")
```

Three of the five known statuses are rejected. Two of those three — `Connecting` and
`Unable to connect` — are exactly what a laptop shows in the first seconds on a new Wi-Fi network
and behind an unaccepted captive portal. The gate fires hardest in the situation the feature
exists for.

The current behaviour is pinned by a parametrised test,
`tests/scripts/test_pub_lease.py:239` (`test_on_refuses_unstable_initial_status`), so any change
here is a deliberate contract change, not a bug fix. Note carefully what that test pins: it is one
guard doing two jobs. Refusing `Connecting` is the part worth changing; refusing `Disconnecting`
and `Unknown` — statuses the controller has no model for — is the part that must survive. The two
must be separated, not swapped wholesale.

### 4.2 The correctness question: what should `previous_connected` be?

This is the part worth getting right. `previous_connected` exists to drive
`_restore_previous_state` (`pub-lease.py:610-616`): `True` ⇒ `connect()` and wait for
`Connected`; `False` ⇒ `disconnect()` and wait for `Disconnected`.

The invariant that matters is **"restore the user's intent, not the network's luck"**. If WARP was
`Unable to connect` before the lease, the user's intent was *connected* — WARP was trying — but
restoring `previous_connected = True` would make `_restore_previous_state` wait for `Connected`,
which cannot happen on that network, so the restore fails and the reconciler retries forever.
That converts a transient network problem into a permanently stuck lease. Any design here must
satisfy that constraint: **restore must terminate on a network where connection is impossible.**

The boolean cannot satisfy it and stay honest, because it has only two values for three distinct
pre-states, and the collapse is lossy in a way that changes behaviour. `False` does not mean "was
not connected"; at `:610-616` it means **"actively disconnect"**. So recording a degraded or
in-flight pre-state as `False` does not merely forget the intent, it *inverts* it: a `pub on` that
subsequently rolls back (`_activate` at `:445-449`) issues `disconnect()` and cancels a connection
the user had already asked for, and a later `pub off` brings WARP back disconnected when the user
had left it trying to connect.

**Replace the boolean with the captured status.** Store the settled pre-lease status string
(validated against the known set, per §4.1) rather than a derived flag, and let
`_restore_previous_state` decide from it:

| Captured pre-lease status | Restore action | Terminates because |
|---|---|---|
| `Connected` | `connect()`, wait for `Connected` within the restore budget | unchanged from today |
| `Disconnected` | `disconnect()`, wait for `Disconnected` | unchanged from today |
| `Unable to connect`, or `Connecting` that never settled | **best-effort**: `connect()`, then wait for `Connected` within the restore budget; on timeout treat the restore as complete, log that WARP was left attempting to connect, and delete the metadata | the wait is bounded and its expiry is a success, not a failure |

The third row is the whole change. It preserves intent — WARP is left trying, which is what the
user asked for — while still terminating, because the timeout is defined as a successful outcome
rather than a retry trigger. That is what makes it strictly better than `previous_connected =
false`: no cancelled connection, no forever-retrying reconciler, and the mode restoration (the part
that actually matters, and the part the lease exists to guarantee) has already happened by then in
either case.

The distinction to hold on to: **a bounded wait whose expiry is fatal** is what creates the stuck
lease; **a bounded wait whose expiry is acceptable** does not. Only the connection state gets the
lenient treatment. The mode restoration keeps its existing strict check (`:618-619`) — if the mode
did not come back, that genuinely is a failed restore and must be retried.

`Registration Missing` is different in kind: it means WARP has no identity, so no mode change
will produce a working tunnel. Refusing is correct there. So is refusing any status outside the
known set (§4.1).

### 4.3 Options

| # | Mechanism | Evidence | Cost | Failure modes | Reversibility |
|---|---|---|---|---|---|
| A | Settle-and-retry: poll while status is `Connecting`, up to a short budget, then classify | `wait_for_status` machinery already exists (`:301-315`) | small | adds latency to `pub on` when the network is genuinely broken | trivial |
| B | Three-way classification — stable (`Connected`,`Disconnected`) / transient (`Connecting`) / degraded (`Unable to connect`) — storing the settled status per §4.2 rather than a derived boolean | §4.2 | small | one more string field in the lease, and a restore branch whose timeout is a success | trivial |
| C | Derive connectedness from `settings.always_on` instead of live status | `"always_on": false` present in settings (verified) | small | `always_on` is a *policy* toggle, not a live state; it is `false` here while the user's intent is genuinely "disconnected", so it happens to agree — but it would disagree on a machine with always-on set and WARP failing | trivial |
| D | Refuse only on `Registration Missing` and on statuses outside the known set; accept the rest | minimal | trivial | on its own, accepts `Connecting` without settling, so the captured state comes from a moving target | trivial |
| E | Status quo | `:709-711` | zero | the pub failure described above | n/a |

**Recommendation: A + B, with D's refusal set.**

Concretely: poll for up to ~10 s while the status is `Connecting`; then classify the settled
status and store it. `Connected` and `Disconnected` restore as they do today.
`Unable to connect`, or still `Connecting` after the budget, is recorded as-is and restored
best-effort per the §4.2 table, **with a printed line saying the pre-lease state was degraded and
what the restore will therefore attempt**. `Registration Missing` ⇒ refuse, since no tunnel is
achievable. **Anything not in the known set ⇒ refuse, with no WARP mutation** — the fail-closed
guard that `tests/scripts/test_pub_lease.py:238` exists to protect.

Reason: A alone leaves the captive-portal case broken; B alone captures state from a transient
value; together they give each known status one behaviour and keep the restore invariant sound.
D contributes the refusal set, and the unknown-status half of it is not optional — it is what
stops a future WARP release from steering the controller into an unmodelled branch. C is rejected
because `always_on` answers a different question — it is a policy setting, not the current
connection intent, and the agreement on this machine is coincidence.

Note this **narrows** the parametrised test at `tests/scripts/test_pub_lease.py:239` rather than
replacing it: `Connecting` moves from the refusal list to the classification list, while
`Disconnecting` and `Unknown` stay refusals and keep asserting `not store.metadata_exists()`.
An intended contract change on one of the three parameters, called out in §A.

---

## 5. The two-minute wait

### 5.1 Where the budget goes

`STATUS_WAIT_ATTEMPTS = 60` (`pub-lease.py:27`) at `poll_interval = 1.0` (`:269`), consumed by
`wait_for_status` (`:301-315`), which is called from both `_ensure_tunnel_ready` (`:593`) and
`_restore_previous_state` (`:616`). A failing `pub on` therefore spends up to 60 s failing to
connect, then `_activate` (`:445-449`) calls `_restore_previous_state`, which can spend another
60 s. No output in between.

### 5.2 No local timing evidence exists

Attempted, and this is the honest result:

* `~/Library/Logs/pub-lease.log` does not exist — the controller has never run here (verified).
* `/Library/Application Support/Cloudflare/cfwarp_service_log.txt` is live (405 010 bytes,
  mtime 2026‑09‑06 13:31, verified) but every retained connection transition is a disconnect:
  `grep -nE "Connecting|Connected|Disconnected" …` returns only
  `2026-09-06T08:30:48.340Z … ResponseStatus: Disconnected(Manual)` and
  `2026-09-06T08:33:49.962Z … ResponseStatus: Disconnected(Manual)` (verified). The rotated
  `.txt.1` likewise yields only three `Disconnected(Manual)` broadcasts on 2026‑09‑05 (verified).

**UNVERIFIED: real WARP connect duration on this machine.** The user has not connected WARP within
the retained log window, so there is nothing to measure. A live measurement is a mutating
operation and is deferred to §A.

What *is* known is the shape of the work. The daemon's connection phase enum (verified via
`strings`) lists, in order: `Initializing`, `SettingsChecking`, `NetworkPerformingHappyEyeballs`,
`EstablishingConnection`, `InitializingTunnelInterface`, `ConfiguringInitialFirewall`,
`SettingRoutes`, `ConfiguringFirewallRules`, `CheckingForRouteToDnsEndpoint`,
`ConfiguringLocalSockets`, `ConfiguringLocalDnsProxy`, `ApplyingDnsSettings`,
`ConfiguringForwardProxy`, `PerformingConnectivityChecks`, `ValidatingDnsConfiguration`,
`ValidatingProxyConfiguration`, `EnsuringMtlsIdentity`. Sixteen phases, several of them
network round trips — so a budget of a few seconds would be too tight and 60 s is far too loose.

### 5.3 Options

| # | Mechanism | Cost | Failure modes | Reversibility |
|---|---|---|---|---|
| A | One shorter global budget (e.g. 20 s) | trivial | same number for two paths with different requirements | trivial |
| B | **Separate budgets: activate / interactive-restore / reconciler-restore** | small | three constants to reason about | trivial |
| C | Exponential backoff within the budget | small | fewer samples near the end, where the answer usually arrives | trivial |
| D | Progress output to stderr while waiting | trivial | noise in the daemon log — must be gated on a TTY | trivial |
| E | Non-blocking `pub on`: set the mode, write the lease, return immediately, let the reconciler finish | medium | the shell returns before the tunnel is up — the user's next command may still be direct | medium |

**Recommendation: B + D.**

Proposed values, to be corrected by the §A measurement:

* `ACTIVATE_WAIT_SECONDS = 25` — generous against sixteen phases, a quarter of the current wait.
* `INTERACTIVE_RESTORE_WAIT_SECONDS = 20` — because the reconciler retries every 60 s anyway.
  The parent review's observation is right and load-bearing: `_close_if_needed`
  (`pub-lease.py:563-572`) re-enters restore on the next tick for a lease in phase `restoring`,
  and `_restore_previous_state` sets that phase before touching WARP (`:608`). A long blocking
  restore in the interactive path buys nothing that the reconciler will not do for free.
* `RECONCILE_RESTORE_WAIT_SECONDS = 60` — the daemon has no human waiting on it, and finishing
  the restore promptly is the whole point.

D: emit a `pub: waiting for WARP …` line to stderr on a TTY only, so the daemon log stays clean.

E is rejected: it breaks the one guarantee `pub on` currently gives — that when the prompt returns,
traffic is tunnelled.

---

## 6. One runtime, across laptops

> **Deferred.** This section and §B are carved out of this design pass and are being decided
> separately. The *finding* below (§6.1) is verified and stands — it is the reason the question
> exists. The *remedy* (§6.2, §6.3) is retained as input to that separate pass and should not be
> read as a settled recommendation: the choice of interpreter is inseparable from whether the
> controller stays a single deployed file or becomes a deployed package, which §B.2 shows is a
> larger change than a same-directory package refactor. Nothing in §1–§5, §7 or §8 depends on this
> being resolved first.

### 6.1 The finding that decides this

`/usr/bin/python3` is not a Python interpreter. It is the `xcode-select` shim:

```
verified: ls -li /usr/bin/python3 /usr/bin/git /usr/bin/clang /usr/bin/swift
1152921500312571585 -rwxr-xr-x  78 root  wheel  118928 Jun 25 06:29 /usr/bin/clang
1152921500312571585 -rwxr-xr-x  78 root  wheel  118928 Jun 25 06:29 /usr/bin/git
1152921500312571585 -rwxr-xr-x  78 root  wheel  118928 Jun 25 06:29 /usr/bin/python3
1152921500312571585 -rwxr-xr-x  78 root  wheel  118928 Jun 25 06:29 /usr/bin/swift
```

All four are the **same inode**, hard-linked 78 times. It dispatches through the active developer
directory, and on this machine that is Xcode, not the Command Line Tools:

```
verified: xcode-select -p            → /Applications/Xcode.app/Contents/Developer
verified: xcrun --find python3       → /Applications/Xcode.app/Contents/Developer/usr/bin/python3
verified: /usr/bin/python3 -c 'import sys; print(sys.executable); print(sys.prefix)'
  /Applications/Xcode.app/Contents/Developer/usr/bin/python3
  /Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9
```

The standalone CLT interpreter also exists —
`/Library/Developer/CommandLineTools/usr/bin/python3` is a symlink to
`../../Library/Frameworks/Python3.framework/Versions/3.9/bin/python3` (verified) — and CLT is
installed (`pkgutil --pkgs | grep CLTools` lists `com.apple.pkg.CLTools_Executables`, verified).

So the daemon's interpreter is *whatever `xcode-select -p` currently points at*. Deleting Xcode,
running `xcode-select --switch`, or an Xcode update that moves the developer directory all change
or remove the interpreter that a **system LaunchDaemon** depends on. On a Mac with neither Xcode
nor CLT, the shim raises the GUI "install command line developer tools" dialog. The playbook's
existing guard (`configure_pub_mode.yml:13-40`) checks the shim at *deploy* time; nothing rechecks
it at *run* time, and the daemon fires every 60 s.

This directly answers "нужен единый способ, и чтобы работало на разных ноутах": the current
arrangement is not one way, it is two — the plist pins `/usr/bin/python3`
(`local.pub-lease.plist.j2:17`) while the controller carries `#!/usr/bin/env python3`
(`pub-lease.py:1`), and the teardown task invokes the script through that shebang
(`configure_pub_mode.yml:352-365`, pinned by `tests/deploy/test_pub_mode.py:764`). The daemon and
the CLI can be running different interpreters on the same machine.

### 6.2 The repository already has the right idiom

Two precedents, both in `install_configs.yml`:

* **Block 1b** (`:63-89`): `uv sync --frozen --no-dev` materialises `.claude/bin/.venv`.
* **Block 3c** (`:341-368`): the same for `~/.config/aerospace/layouts/`, and the comment at
  `:348-351` is exactly our problem — *"the aerospace.toml keybindings invoke the built
  console-script at `~/.config/aerospace/layouts/.venv/bin/aerospace-layouts` by ABSOLUTE path
  (`exec-and-forget` runs via `/bin/bash -c` with no `uv` on PATH), so the venv must exist for
  the layout binds to work."*

A LaunchDaemon has the same constraint as `exec-and-forget`: no PATH, no shell profile, absolute
paths only. Block 3c is the closest existing solution to the pub-lease problem.

Tooling is present: `uv 0.11.31` at `/opt/homebrew/bin/uv`, and `uv python list` shows both
Homebrew CPython 3.14.6 and a uv-managed `~/.local/share/uv/python/cpython-3.14-macos-aarch64-none/`
already downloaded (verified).

### 6.3 Options

| # | Mechanism | Pre-CLT | Pre-Homebrew | Works at boot before login | Deploy complexity | Daemon/CLI parity |
|---|---|---|---|---|---|---|
| A | Pin `/usr/bin/python3` in shebang **and** plist (template the shebang) | **no** — GUI installer prompt | yes | yes, if CLT/Xcode present | trivial | yes |
| B | **uv-managed CPython + `uv sync --frozen`, absolute console-script path** | yes | no — needs `uv`, which `make init` installs before this task | yes — venv on the boot volume under `$HOME` | small; idiom already in the repo twice | yes, by construction |
| C | Homebrew `python3` pin | yes | no | yes | small | yes, but a brew Python upgrade (3.14 → 3.15) breaks the venv path |
| D | Self-contained binary (PyInstaller / Nuitka) | yes | yes | yes | **high** — build, sign, notarise, ship | yes |
| E | Rewrite in Go | yes | yes | yes | high — new language, new build/release path, ~920 lines to port | yes |

**Recommendation: B.**

Reason: it is the only option that gives one interpreter to both callers *by construction* rather
than by two coordinated pins, it is already the established repository idiom twice over, and its
one weakness — a dependency on `uv` — is not real here, because `make init` installs Homebrew and
the toolchain before any of this runs and the playbook already hard-fails when `uv` is missing
(`install_configs.yml:76-82`, `failed_when: devbox_uv_path.rc != 0`).

Two implementation notes:

* Pin the interpreter with a `.python-version` next to the project so the venv is built against a
  uv-managed CPython under `~/.local/share/uv/python/`, not against `/opt/homebrew/bin/python3`.
  That removes option C's failure mode (a brew Python upgrade orphaning the venv).
* Keep the program stdlib-only regardless. The venv then exists purely to pin an interpreter, and
  `uv sync --frozen` has nothing to resolve — which is exactly why this is cheap.

A is the fallback if B is judged too heavy: template the shebang from `devbox_pub_python_path`
so both callers share one pin. It does not fix the pre-CLT case, but it does fix the split.
D and E are rejected on cost for a program with no distribution requirement — see §B, where the
same question is asked at the level of the whole component.

---

## 7. The leftover candidate plist

### 7.1 Why the mechanism exists

Read `configure_pub_mode.yml:116-180` and `:247-255`. The sequence is:

1. Render the template to `.local.pub-lease.plist.candidate` (`:116-125`).
2. `stat` the candidate and the installed plist (`:127-145`).
3. If they differ, or nothing is installed, write the marker
   `.local.pub-lease-reload-required` with `force: false` (`:147-164`).
4. Copy candidate → real plist (`:166-179`).
5. `bootout` if the marker exists and the job is loaded (`:215-228`); `bootstrap` if the marker
   exists or the job is not loaded (`:230-245`).
6. Remove the marker (`:247-255`).

The marker is a **crash-safe reload flag**: if the play dies between step 4 and step 5, the plist
on disk is new but launchd is still running the old one. The marker survives, and the next run
performs the reload. `force: false` is what makes it survive. This is deliberate and the
comment at `:319-324` shows the ordering was reasoned about. Any proposal must preserve it.
It is pinned by `tests/deploy/test_pub_mode.py:443`
(`test_pending_reload_marker_survives_until_launchdaemon_reload_completes`).

The candidate file, by contrast, is only needed *within* one run — to compare against the
installed plist before overwriting it. It is removed only on the disabled path
(`configure_pub_mode.yml:376`), so on the enabled path it accumulates permanently in
`/Library/LaunchDaemons/` as a root-owned mode‑0600 dotfile.

### 7.2 Does launchd care?

`man launchd.plist`: *"property list files are expected to have their name end in `.plist`. Also
please note that it is the expected convention for launchd property list files to be named
`<Label>.plist`."* `man launchd` FILES lists `/Library/LaunchDaemons` as *"System-wide daemons
provided by the administrator"* with no statement about filtering.

So: the documentation states an expectation about naming, not an explicit guarantee that
non-`.plist` files are ignored. In practice a file named `.local.pub-lease.plist.candidate` does
not end in `.plist` and is a dotfile.

**UNVERIFIED: that launchd definitively ignores it.** Proving it would mean placing a file in
`/Library/LaunchDaemons/` and re-bootstrapping the domain, which needs root and mutates system
state. The risk is judged low but it is not zero, and "probably ignored" is a poor reason to
leave root-owned litter in a system directory.

### 7.3 Options

| # | Mechanism | Cost | Failure modes | Reversibility |
|---|---|---|---|---|
| A | Delete the candidate after a successful `bootstrap` | trivial | a crash between copy and delete leaves it — same as today, but rare instead of always | trivial |
| B | **Stage the candidate outside `/Library/LaunchDaemons/`** (e.g. `/Library/Application Support/devbox/local.pub-lease.plist.candidate`) | small — two path variables in `:42-56` | new directory to create and own | trivial |
| C | Compare checksums in memory (`template` to a `check_mode` run, or hash the rendered content) and drop the candidate file entirely | medium — loses the on-disk artefact used by `stat` comparison | harder to debug; changes the tested task shape | medium |
| D | `ansible.builtin.template` with `validate: plutil -lint %s` writing straight to the final path | small | `validate` runs before the move, but the marker protocol still needs a *pre-copy* comparison, so this does not replace steps 2–3 | trivial |

**Recommendation: B, plus A as belt and braces.**

Reason: B removes the question in §7.2 entirely rather than betting on launchd's tolerance, and
it keeps the marker protocol, the `stat`-based comparison and the task structure — so
`tests/deploy/test_pub_mode.py:443` and `:124` keep testing the same behaviour with different
paths. A costs one task and reduces the residue to a crash window. C is rejected because it
trades a hygiene problem for a debuggability problem. D is useful independently —
`plutil -lint` validation of a generated plist is worth adding — but it does not address the
candidate at all.

The marker itself should stay in `/Library/LaunchDaemons/` or move alongside the candidate; either
is fine, but it must keep `force: false` and must keep outliving a failed run.

---

## 8. `StartInterval` 60 → 300 — recommend reverting the agreement

### 8.1 The documented behaviour

`man launchd.plist`, `StartInterval`:

> This optional key causes the job to be started every N seconds. **If the system is asleep during
> the time of the next scheduled interval firing, that interval will be missed due to shortcomings
> in kqueue(3).** If the job is running during an interval firing, that interval firing will
> likewise be missed.

This contradicts the assumption in the original review that launchd coalesces a missed firing and
runs it promptly on wake. It does not: the firing is *missed*. The job next runs at the following
periodic firing — so the worst-case latency after opening the lid is one full interval.

`ProcessType Background` (`local.pub-lease.plist.j2:36-37`) is documented as applying resource
limits "intended to prevent them from disrupting the user experience", and the man page notes the
default for unspecified jobs is "light resource limits ... throttling its CPU usage and I/O
bandwidth". Background is the right classification and is not itself a latency problem, but it
does mean the job is deprioritised — another reason not to widen the interval.

### 8.2 Why 300 s is worse once §1 lands

Today the reconciler has one time-sensitive job: notice expiry. With a 6 h lease, 60 s versus
300 s of granularity is irrelevant — which is why "300 sounds reasonable" was a fair reading of
the original review.

With §1 implemented the reconciler acquires a second, genuinely latency-sensitive job: notice
that the network changed. The close latency becomes `NETWORK_MISS_LIMIT × StartInterval`:

| Interval | Miss limit 2 | Worst case after opening the lid at home |
|---|---|---|
| 60 s | ~2 min | ~2 min |
| 300 s | ~10 min | ~10 min |

Ten minutes of home traffic through Cloudflare, every time, is a direct regression against the
stated goal. The interval and the anti-flap limit multiply.

### 8.3 What the idle cost actually is

The reconciler exits before constructing a controller when there is no metadata —
`main` (`pub-lease.py:911-912`): `if command == "reconcile" and not store.metadata_exists():
return 0`. So an idle tick is one `/bin/sh` and one Python interpreter start, with **zero**
`warp-cli` invocations. Measured interpreter start on this machine: `/usr/bin/python3` executing
the controller's `status` path completes promptly (verified: the controller ran end-to-end under
`/usr/bin/python3` 3.9.6, printing `WARP: mode=proxy, status=Disconnected` / `pub lease:
inactive`). At roughly 40 ms per idle tick, 1 440 ticks/day is on the order of one minute of CPU
per day — and it is `ProcessType Background`, so it yields to anything the user is doing.

### 8.4 Options

| # | Mechanism | Close latency (miss limit 2) | Idle cost | Notes |
|---|---|---|---|---|
| A | **Keep `StartInterval` 60** | ~2 min | ~1 min CPU/day | matches §1's requirement |
| B | 120 s | ~4 min | ~30 s CPU/day | halves an already-negligible cost, doubles the latency |
| C | 300 s | ~10 min | ~12 s CPU/day | undoes a meaningful part of §1 |
| D | Two jobs — a fast one gated on lease presence, a slow keeper | ~2 min | lowest | launchd cannot conditionally schedule; would need `KeepAlive`/`PathState`, documented as race-prone; and `LaunchEvents` needs `xpc_set_event_stream_handler(3)` — unavailable to Python (`man launchd.plist`) |
| E | Resident daemon on `com.apple.system.config.network_change` | near-instant | a permanent process | see §1.4 option E — wrong process model for this program |

**Recommendation: A — keep 60 s, and revisit the earlier agreement.**

Reason: the cost being optimised away is ~1 minute of throttled background CPU per day; the cost
being introduced is up to 10 minutes of unwanted tunnelling per pub visit. That trade is the wrong
way round for the stated goal. This is flagged as an open question in §C because the user already
agreed to 300 s on the basis of the earlier, incomplete analysis.

If a compromise is wanted, B (120 s) with `NETWORK_MISS_LIMIT = 1` gives the same ~2 min close
latency at half the tick rate — at the cost of losing the anti-flap margin. A is cleaner.

---

## A. Testing strategy

### A.1 What already exists

**`tests/scripts/test_pub_lease.py`** (30 256 bytes) loads the controller via
`importlib.util.spec_from_file_location` (`:28-35`) — necessary because `pub-lease.py` is
hyphenated and lives outside any package. It already provides a `FakeWarp` implementing the
`WarpPort` Protocol (`:42-93`) and a `Harness` (`:104`). Coverage by class:

| Class | Line | Covers |
|---|---|---|
| `TestPubLeaseLifecycle` | `:143` | activation, disabled marker, restore of connected/disconnected, reboot ends lease, renewal keeps snapshot, read-only status, **refusal on unstable status (`:239`)** |
| `TestPubLeaseOwnership` | `:249` | policy lock before ownership, policy drop, mode drift, restoring-phase acceptance, failed-restore retention |
| `TestPubLeaseStateCompatibility` | `:330` | all v1 phases, interrupted state, corrupt→recovery, invalid rejection, **unknown-field preservation (`:405`)**, external-reader contract |
| `TestPubLeaseRecoveryAndMaintenance` | `:454` | force quarantine, retention, log rotation, atomic-write failure |
| `TestPubLeaseFailures` | `:530` | write failures at each phase, inspection failure, stderr propagation |
| `TestWarpClientAdapter` | `:629` | non-zero exit handling |
| `TestPubLeaseLocking` | `:651` | non-blocking contention, private state dir, interactive timeout |
| `TestPubLeaseCliParity` | `:756` | CLI argument contract, reconcile-without-state, status side-effect freedom, silent contention |

**`tests/deploy/test_pub_mode.py`** covers the plist shape (`:52`, asserting `Label`,
`UserName`, `StartInterval == 60`), the append-mode log wrapper (`:82`), Python 3.9 source
compatibility (`:118`), the deploy/candidate tasks (`:124`), the profile gate (`:186`, `:212`),
the fish wrapper fallback (`:219`), the disabled teardown (`:260`, `:420`), the reload marker
(`:443`), system-domain management and legacy cleanup (`:620`, `:667`), dev-mode safety (`:730`),
the teardown shebang dispatch (`:764`), the no-shell-tools gate (`:790`), and the proxy migration
(`:799`–`:861`).

This is strong. The gaps below are genuinely new surface, not re-tests.

### A.2 Unit-level additions

Reuse `FakeWarp`; add a second injectable port by the same pattern.

1. **`NetworkPort` protocol** — `signature() -> str | None`. Inject a `FakeNetwork` into
   `Controller` exactly as `WarpPort` is injected (`pub-lease.py:363-380`). Cases:
   * same signature over N reconciles ⇒ `expires_at` advances, `hard_expires_at` does not
   * different signature once ⇒ `network_misses == 1`, lease survives
   * different signature twice ⇒ restore performed, metadata deleted, reason "network changed"
   * `None` (unobtainable) ⇒ neither renewal nor miss; lease still closes at `expires_at`
   * signature present but `now >= hard_expires_at` ⇒ close, reason "maximum lease duration"
   * lease file without `network_signature` (a v1 fixture) ⇒ today's behaviour, no crash
2. **Renewal guards (§1.5)** — the cases that prove renewal cannot mask an existing closure. Each
   asserts the lease is closed and WARP restored, *not* renewed, even though the signature matches:
   * matching signature + `now >= expires_at` ⇒ closed on expiry, `expires_at` not advanced. This
     is the one the guard exists for: an expired lease is never resurrected.
   * matching signature + `phase == "restoring"` ⇒ the interrupted restore completes
     (`_close_if_needed` at `:564-572`), no renewal
   * matching signature + `phase == "activating"` ⇒ same
   * matching signature + boot-session mismatch ⇒ closed with reason "boot session changed"
     (`:580`), no renewal
   * matching signature + `phase == "active"` + `now < expires_at` ⇒ the only renewing case
3. **Gateway MAC normalisation** — table test proving `c4:f:a6:64:be:10` and
   `c4:0f:a6:64:be:10` hash identically. Both forms were observed on this machine (§1.5), so this
   is a real, not hypothetical, case.
4. **Lease field validation (§1.5)** — extend `test_rejects_invalid_v1_state` (`:377-403`) with the
   new fields, asserting `StateError` and `harness.warp.calls == []` for each: `network_misses` as
   `"1"`, as `True`, as `-1`, as a float; `hard_expires_at` non-finite, and earlier than
   `started_at`; `network_signature` not a 64-character lower-case hex digest. Plus the positive
   cases: all three absent ⇒ loads and behaves as today; all three valid ⇒ loads and round-trips.
   The point is that these must fail *at load*, not raise `TypeError` inside the reconciler where
   nothing catches it (`:890`, `:897-918`).
5. **Status classification (§4)** — **narrow** `test_on_refuses_unstable_initial_status` (`:239`)
   rather than replacing it. `Connecting` moves out of its parameter list into a new classification
   test; `Disconnecting` and `Unknown` stay in it, still asserting return code 1, the refusal
   message, and `not store.metadata_exists()`. Deleting that test would remove the only guard
   against an unrecognised future status reaching a mutation path. The new classification test then
   covers: `Connected` ⇒ captured as connected; `Disconnected` ⇒ captured as disconnected;
   `Connecting` ⇒ settles within the budget then classifies; `Connecting` that never settles, and
   `Unable to connect` ⇒ captured as degraded with the printed notice; `Registration Missing` ⇒
   refusal. Plus a restore test per degraded state: `connect()` is issued, the bounded wait expires,
   and the restore is nonetheless treated as complete with metadata deleted — the assertion that
   the degraded path terminates.
6. **Wait budgets (§5)** — assert the activate path uses the activate budget and the reconciler
   restore path uses the reconciler budget, by counting `sleeper` calls on the existing fake
   clock.
7. **Policy-drop legibility (§3)** — after a drop, `pub off` must not print `already OFF`; it must
   name `tunnel_only` and the last-known previous mode.
8. **New fixtures** — extend `tests/scripts/fixtures/pub_lease/` with `v1-active-signature.json`
   and `v1-active-capped.json` alongside the existing `v1-*` and `bash-*` files. The names carry
   `v1-` deliberately: §1.5 keeps the schema at `version: 1`, and `version == 2` remains a rejected
   value pinned at `:380`. A `v2-*` fixture would contradict both.
9. **`fish_greeting` states (§2)** — the greeting is derived from the lease file, so it needs the
   same state coverage as the controller: `active` with time remaining, `restoring`, `activating`,
   expired-but-not-yet-reconciled, corrupt/unparseable, and absent. Each asserts the emitted text
   and — equally important — that no `warp-cli` subprocess was spawned.

### A.3 Deploy-level additions

10. Candidate staged outside `/Library/LaunchDaemons/` (§7), and removed after bootstrap.
11. Marker still `force: false` and still survives a failed reload — extend `:443` rather than
    replace it.
12. `plutil -lint` validation of the rendered plist.
13. If §8's recommendation is accepted, `:75` continues asserting `StartInterval == 60`; if the
    user overrules, that assertion changes to 300 and the §1 miss limit must drop to 1 in the same
    commit.
14. Deferred with §6: an assertion that the plist interpreter and the deployed shebang resolve to
    the same runtime. It is the strongest available regression guard for "единый способ", and it
    belongs to whichever commit settles that question — writing it now would pin the split the
    deferred pass exists to remove.

### A.4 Manual end-to-end scenarios

These need a real Mac and real network changes. Each has an exact pass condition.

| # | Scenario | Steps | Pass condition |
|---|---|---|---|
| E1 | Pub → home, lid closed | On network A: `pub on`; `pub status` shows an active lease. Close the lid. Move to network B. Open the lid. Wait 3 min. | `pub status` reports inactive; `warp-cli -j settings` shows `operation_mode` back to the pre-lease value; `warp-cli -j status` matches the pre-lease status; `~/Library/Logs/pub-lease.log` contains a "network changed" line |
| E2 | Same network, long session | On network A: `pub on`. Wait 45 min without touching anything. | `pub status` still active; `expires_at` has advanced past the original 30 min; `hard_expires_at` unchanged |
| E3 | Hard cap | Contrive by writing a lease whose `hard_expires_at` is 2 min out, on the active network. Wait 3 min. | lease closed; log reason "maximum lease duration reached"; WARP restored |
| E4 | Reboot mid-lease | `pub on`, then `sudo reboot`. Log in. Wait 2 min. | lease closed with reason "boot session changed"; WARP restored. Confirms the existing `:199` unit test against reality |
| E5 | Captive portal | Join a captive-portal network without accepting the portal. Run `pub on`. | Either the lease activates, or it fails with a message naming the degraded pre-state — **not** `WARP is not in a stable state`. Command returns within ~30 s, not ~120 s |
| E6 | WARP quit mid-lease | `pub on`, then quit Cloudflare WARP.app. Wait 2 min. Read the log. | log shows retained-lease messages, not a crash loop; lease metadata intact; relaunching WARP lets the next reconcile finish |
| E7 | Policy lock mid-lease | Requires a Zero Trust enrolment — not reproducible on this free/unmanaged account (`managed: false`, verified). Simulate at unit level instead (§A.2 case 5) | unit test only; note the limitation |
| E8 | Work-profile teardown with an active lease | `pub on` on the personal profile; run the play with the pub gate false. | `Pub mode — restore active lease before removal` reports changed; WARP restored; `~/.local/bin/pub-lease` and the plist gone; the assert at `configure_pub_mode.yml:298-317` did not trip |
| E9 | Notification delivery (§2) | With the daemon installed, force a lease close and watch Notification Centre. | a notification appears naming the restore. **This is the test that resolves the UNVERIFIED item in §2.3** |
| E10 | Idle cost (§8) | With no lease, sample the daemon over an hour. | no `warp-cli` process spawned; per-tick wall time under ~100 ms |

### A.5 Mutating measurements requiring the user's approval

None of the following were run. Each changes live network state.

| Measurement | Exact command | Expected observation | Why it is needed |
|---|---|---|---|
| WARP connect duration | `warp-cli mode tunnel_only && time warp-cli connect && time (while ! warp-cli -j status \| grep -q '"status": "Connected"'; do sleep 1; done)` | wall-clock seconds from `connect` to `Connected` | sets `ACTIVATE_WAIT_SECONDS` in §5; currently UNVERIFIED because no connect appears in the retained WARP logs |
| WARP restore duration | `warp-cli mode proxy && time warp-cli disconnect` then poll for `Disconnected` | wall-clock seconds | sets the restore budgets in §5 |
| Behaviour on a captive-portal network | `warp-cli -j status` while behind an unaccepted portal | the exact `status` **and** `reason` strings | confirms which of the §4 classification branches the real portal case takes |
| Notification from the system domain | install the daemon, then `launchctl asuser $(id -u) /usr/bin/osascript -e 'display notification "test" with title "pub"'` from within the daemon | notification appears | resolves §2.3 |
| launchd tolerance of the candidate file | place a dotfile in `/Library/LaunchDaemons/` and `launchctl bootstrap system …` | no error, no spurious job | resolves §7.2 — recommended *not* to run; §7's recommendation makes it moot |

Restore afterwards in every case: `warp-cli mode proxy` and `warp-cli disconnect`, which is the
state observed today (verified: `operation_mode: proxy`, `status: Disconnected`).

---

## B. Should this become a standalone program?

> **Deferred.** Together with §6, this question is carved out of the present pass and is being
> decided separately. What follows is retained as input to that decision, not as a settled
> recommendation. §B.2 in particular establishes a constraint that any packaging proposal has to
> answer: the controller is deployed *outside* the repository, so the in-repo import idiom that
> works for `scripts/otelbox_edge/` does not apply to it.

### B.1 Current shape

| Artefact | Size |
|---|---|
| `roles/devbox/files/.local/bin/pub-lease.py` | 923 lines |
| `roles/devbox/tasks/darwin/configure_pub_mode.yml` | 379 lines |
| `roles/devbox/templates/darwin/Library/LaunchDaemons/local.pub-lease.plist.j2` | 39 lines |
| `tests/scripts/test_pub_lease.py` | 30 256 bytes |
| `tests/deploy/test_pub_mode.py` | 941 lines |
| fish wrapper + migration | 7 + 48 lines |

### B.2 The friction that is real

* Tests reach the module through `importlib.util.spec_from_file_location` (`:28-35`) because the
  file is hyphenated and outside any package. Meanwhile the repo already configures
  `pythonpath = ["scripts"]` (`pyproject.toml:358`), which is how `otelbox_edge` is imported
  cleanly *in the test environment*.
* The same diff being reviewed restructured `scripts/otelbox-edge-*.sh` into
  `scripts/otelbox_edge/{__init__,cert_check,config,smoke}.py` plus three 8-line wrappers
  (verified: `cat scripts/otelbox-edge-config.py` is exactly
  `from otelbox_edge.config import main` / `raise SystemExit(main())`).

  **That precedent does not transfer to pub mode.** Those wrappers resolve `otelbox_edge` for one
  reason only: each wrapper lives
  *inside* `scripts/`, next to the package, and Python puts a script's own directory on `sys.path`.
  They are also executed in place from the repository checkout — Ansible invokes them by repo path
  (`install_configs.yml:539`: `{{ role_path }}/../../scripts/otelbox-edge-cert-check.py`), so the
  package is always a sibling of the running script. `pub-lease` has neither property: it is
  *copied* to `~/.local/bin/pub-lease` (`configure_pub_mode.yml:107-114`, a single-file
  `ansible.builtin.copy`) and runs from outside the repository, where no sibling package exists and
  nothing puts one on the path. `pythonpath = ["scripts"]` (`pyproject.toml:358`) is `[tool.pytest]`
  configuration and applies under pytest only; `package = false` (`:41`) means nothing is installed
  and no console script is generated.

  The applicable precedent is the AeroSpace one: a full deployed project tree with its own
  `pyproject.toml`, `[project.scripts]` and a `uv_build` backend
  (`roles/devbox/files/.config/aerospace/layouts/pyproject.toml:15-21`), materialised with
  `uv sync --frozen` and invoked by absolute console-script path. That is a materially larger
  change than the `otelbox_edge` refactor, and sizing it belongs to the deferred pass — as does the
  ordering constraint it runs into, since pub mode is configured at `main_darwin.yml:44-45`, before
  `install_configs.yml` at `:63` where such venvs are materialised.
* `pyproject.toml:40` sets `package = false` under `[tool.uv]` — the repo deliberately is not a
  distributable package. Extraction would fight that decision, not extend it.

### B.3 The friction that is not real

* **Reuse on the work laptop: none.** Pub mode is gated on the profile installing
  `cloudflare-warp` (`main_darwin.yml:47-53`), and that cask is personal-only
  (`profiles/personal.yml:9-11`). A separate repo would be maintained for one machine.
* **Release/versioning: not wanted.** The deployment is Ansible-driven and idempotent. A version
  number would add a skew dimension (deployed version vs repo version) that the current
  copy-and-reload design does not have.
* **A private Homebrew tap** means a formula, a release artefact, checksums, and a bottle story
  for a program with exactly one user. The repo already carries the cost of one such dependency
  (`abrosimov/otelcol-otelbox`) and that one is genuinely shared with `remote_server_setup` —
  pub mode is not.

### B.4 Options

| # | Option | Testability | Release cost | Work-laptop reuse | Ansible coupling | Verdict |
|---|---|---|---|---|---|---|
| A | Stay exactly as-is | importlib hack persists | none | n/a | tight | rejected — the hack is real friction |
| B | Restructure as a `pub_lease` package + thin wrapper | clean import, no `importlib` hack | none | n/a | needs a deployed package tree, not a file copy (§B.2) | candidate for the deferred pass |
| C | New repo under `$AION_AUTOPOIESEON` (new-style `base/`) | clean | moderate | none | loosened, but the plist still comes from here | rejected — cost without a beneficiary |
| D | Go binary + private tap | clean | high | none | loose | rejected — cost without a beneficiary |
| E | `uv` tool (`uv tool install`) | clean | low | none | the daemon would depend on a tool-managed shim path | rejected — `devbox_packages.uv_tools` is for third-party tools, and it re-introduces a PATH dependency in a LaunchDaemon |

C, D and E can be rejected now, and are: every argument for them rests on reuse or release, and
neither exists — pub mode is a single-machine, single-user, Ansible-deployed component gated to the
personal profile (§B.3). Extraction would buy ceremony.

**A versus B is the open decision, and it is deferred.** The choice turns on a question §B.2
settles the terms of but does not answer: a package has to reach the controller at
`~/.local/bin/pub-lease`, outside the repository, so B is not a same-directory refactor but a
deployed project tree — `pyproject.toml`, `[project.scripts]`, a lock file, `uv sync --frozen`, an
absolute console-script path, and a resolution of the `main_darwin.yml:44-45` versus `:63` ordering.
That is the work the separate pass has to size, and it is also where the §6 interpreter question
gets answered, because the two are decided by the same choice.

Nothing in §1–§5, §7 or §8 waits on it. A shape like:

```
scripts/pub_lease/{__init__,state,warp,network,controller,cli}.py
roles/devbox/files/.local/bin/pub-lease.py   # thin wrapper
```

is the obvious candidate for B and is recorded here only as the starting point for that pass.

### B.5 Sequencing

§6 and §B are excluded — they are decided separately and are not prerequisites for anything below.
The controller stays a single self-contained deployed file for all of these steps.

1. **§4** (status classification and the captured-status restore) and **§5** (wait budgets) —
   small, self-contained, they fix the at-the-pub failure. Highest value per line changed.
2. **§3** (policy-drop message) and **§7** (candidate staging) — small corrections, no design risk.
3. **§1** (network signature + guarded renewal) — the feature work. New network port and fake, the
   validated lease fields of §1.5, new fixtures. It needs no packaging change: the signature
   helper, the `NetworkPort` protocol and its fake all fit inside the existing single file
   alongside `WarpPort` (`pub-lease.py:41-54`).
4. **§2** (notification + greeting) — last, because §1 removes most of the need for it and the
   remaining need is precisely defined only after §1 exists.
5. **§8** — decide before step 3, since the interval and `NETWORK_MISS_LIMIT` must be chosen
   together.

Steps 1–2 are safe to do immediately. Step 3 is the substantial work. None of it is blocked on
first deployment: pub mode is absent from this laptop (§0), so there is no live lease here to
migrate — but the compatibility surface listed in §0 still has to keep working, and step 3 in
particular must leave a v1 lease file loading unchanged.

---

## C. Open questions

**C1. `StartInterval` — keep 60 s after all?**

Trigger: `man launchd.plist` states a sleeping system *misses* an interval firing, so the interval
is also the post-wake detection latency. With §1's network detection and `NETWORK_MISS_LIMIT = 2`,
300 s means up to ~10 min of tunnelled traffic after opening the lid at home; 60 s means ~2 min.
The idle cost being saved is ~1 min of `ProcessType Background` CPU per day. The user already
agreed to 300 s, on the basis of the earlier analysis that did not include §1.

* **(Recommended) Keep 60 s.** Best match to the stated goal; idle cost is negligible and already
  short-circuits without touching `warp-cli` (`pub-lease.py:911-912`).
* 120 s with `NETWORK_MISS_LIMIT = 1` — same ~2 min close latency, half the ticks, no anti-flap
  margin.
* 300 s as agreed — accept ~10 min of home tunnelling per pub visit.

**C2. How long should the lease and the hard cap be?**

Trigger: §1.5 proposes `LEASE_SECONDS = 1_800` (renewal window) and
`MAX_LEASE_SECONDS = 43_200` (hard ceiling). The current single value is 21 600
(`pub-lease.py:24`). With auto-renewal the renewal window no longer bounds a session, so the
question is what "must not be globally permanent" should mean numerically.

* **(Recommended) 30 min window, 12 h cap.** The window only bounds how long a lease survives
  after the network becomes unreadable (asleep, link-down); the cap bounds a pathological case
  where you genuinely stay on one network all day.
* 30 min window, 8 h cap — tighter ceiling; forces a re-`pub on` on a very long sitting.
* 60 min window, 12 h cap — more forgiving of a long sleep in a bag, at the cost of a longer tail.
* No cap, rely on the signature alone — rejected here, but it is the user's call: it would mean a
  lease that lives as long as you stay on one network, which reads against "не должен быть
  глобален пожизненно".

**C3. Does §2's notification path actually deliver?**

Trigger: `launchctl asuser $(id -u) /usr/bin/true` succeeds as the ordinary user (verified), and
`man launchctl` documents `asuser` as adopting the target user's Mach bootstrap namespace — but
whether Notification Centre *renders* a notification posted from a system-domain job is
**UNVERIFIED** and cannot be tested without installing the daemon.

* **(Recommended) Implement A+B from §2 and settle it with manual test E9.** `fish_greeting` works
  regardless, so the feature is not blocked on the answer.
* Move the notification half into a separate user-domain LaunchAgent that watches the lease file —
  guaranteed GUI session, at the cost of a second supervisor.
* Skip notifications; ship `fish_greeting` only.

**C4. Should the network signature include the DHCP vendor fingerprint?**

Trigger: `ipconfig getsummary en0` exposes `option_125` carrying `ETISALAT-HG6244B` /
`K2411G03044` (verified) — a very strong identifier for this network. It is vendor-optional, so a
pub router may omit it.

* **(Recommended) No — router IP + gateway MAC only.** Uniform across networks; a missing optional
  component would otherwise make signatures incomparable. The primary interface is read to locate
  the route but is deliberately not hashed (§1.5), so a dock change on the same router does not
  read as a network change.
* Include it when present, as an additional discriminator, with a documented "absent" sentinel —
  slightly stronger, meaningfully more code.

**C5. Is the work laptop ever going to run pub mode?**

Trigger: §3's policy-lock trap is unreachable on this machine (`managed: false`, free account —
verified) but is exactly what a corporate Zero Trust enrolment produces. The gate at
`main_darwin.yml:47-53` currently keeps pub mode off the work profile entirely.

* **(Recommended) Assume no, fix the message anyway (§3 recommendation A+C).** Cheap insurance.
* Plan for yes — then §3 rises in priority and options B/D deserve reconsideration.
