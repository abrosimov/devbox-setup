# Pub: purpose and package extraction

Status: extraction handoff, 2026-09-10. This records the intended next step after the current change passes local checks and hosted CI. It does not claim a published package, choose a distribution channel, or extend platform support. Current behaviour is specified in the [README](../../README.md#pub-mode), controller and tests. The [September 6 study](pub-mode-hardening.md) is historical; its packaging discussion predates the intent to distribute pub to other users.

## Problem and evidence

Pub began as a workaround for Claude Code connectivity failures on a particular wifi network. The original cause remains unknown. Its purpose is to enable an alternative path temporarily and restore the previous WARP state without relying on the user remembering to turn it off.

The September 10 diagnosis separated two later failures:

| Observation | Consequence |
| --- | --- |
| With `tunnel_only`, both configured ISP DNS servers timed out. Public DNS and HTTPS with an explicit destination IP worked. | A connected tunnel did not imply working name resolution. New leases use `warp+doh` and check DNS/HTTPS before reporting success. |
| `warp+doh` failed with `Port53Bound`; `mDNSResponder` owned port 53 and Docker had `KernelForUDP=true`. After disabling the option and restarting Docker, live on/off verification passed. | Diagnose DNS-port ownership; do not stop unrelated services from the pub controller. |

These observations concern one Mac and network. They do not establish the original Claude fault, compatibility with every VPN configuration, or uninterrupted existing application sessions. The HTTPS probe establishes transport reachability, not a successful authenticated Claude request.

## User contract to preserve

- `pub on` captures the previous WARP mode and connection intent, enables `warp+doh`, and checks DNS/HTTPS. Failed activation attempts restoration and retains recovery metadata if restoration fails.
- `pub off` restores the captured state. `status` reports both WARP and lease state. `off --force` with unreadable metadata cannot reconstruct a lost previous mode.
- A lease renews for thirty minutes on the same gateway, has a twelve-hour ceiling, and closes after a confirmed network change, expiry or reboot. The supervisor operates independently of the terminal.
- The effect is machine-wide. No application proxy variables or application credentials are required. Application reconnection remains the application's responsibility.
- Saved `tunnel_only` leases remain readable and restorable. Upgrades must preserve the immutable recovery snapshot, lock coordination and ownership rules; never reinterpret old metadata as a new lease.

## Source map

| Responsibility | Current source | Extraction treatment |
| --- | --- | --- |
| Controller, state, WARP and OS adapters | [pub-lease.py](../../roles/devbox/files/.local/bin/pub-lease.py) | Move with its behavioural contract; splitting into modules is optional. |
| Behavioural tests and historical state fixtures | [test_pub_lease.py](../../tests/scripts/test_pub_lease.py), [fixtures](../../tests/scripts/fixtures/pub_lease) | Carry into package tests, including rollback, legacy recovery and interrupted operations. |
| Supervisor installation and teardown | [configure_pub_mode.yml](../../roles/devbox/tasks/darwin/configure_pub_mode.yml), [plist](../../roles/devbox/templates/darwin/Library/LaunchDaemons/local.pub-lease.plist.j2), [deployment tests](../../tests/deploy/test_pub_mode.py) | Turn the lifecycle into package installation, upgrade and uninstall operations. Keep devbox as a consumer. |
| Real host verification | [pub-mode-test.py](../../scripts/pub-mode-test.py), [gate tests](../../tests/scripts/test_pub_mode_test.py) | Replace repository-relative imports with the installed package; preserve real WARP checks and restoration assertions. |
| Shell integration | [pub.fish](../../roles/devbox/files/.config/fish/functions/pub.fish), [greeting](../../roles/devbox/files/.config/fish/functions/fish_greeting.fish) | Provide a shell-independent `pub` entry point; keep greeting optional. |
| Machine provisioning and legacy cleanup | [Docker task](../../roles/devbox/tasks/darwin/configure_docker_desktop.yml), [proxy migration](../../roles/devbox/files/.config/fish/conf.d/pub_proxy_migration.fish), profile gates | Retain in devbox. Package diagnostics explain incompatibilities; installation must not silently rewrite unrelated software settings. |

## Runtime and installation boundary

The current implementation targets macOS, uses Python 3.9+ standard library code, and calls installed `warp-cli`, `/usr/bin/curl` and macOS networking tools. WARP must be installed, registered and permitted to switch modes. Linux and Windows support is not implemented. Docker is not a dependency.

The current supervisor is a system LaunchDaemon running as the owning user. Installation therefore includes privileged supervisor registration and absolute executable/interpreter paths. Existing state lives in `~/.local/state/pub-lease`, logs in `~/Library/Logs/pub-lease.log`. Preserve those locations for migration or explicitly migrate them under the same lock. Concurrent ownership by multiple users is not established by the current tests.

Choose the package format and interpreter provision before publishing. A copied Python wrapper must not depend on imports available only inside the devbox checkout. Provide an explicit install/upgrade/uninstall lifecycle: register the supervisor, retain recoverable state across upgrades, restore an active lease before removal, and stop removal if restoration fails. Removing a package must not uninstall WARP or erase recovery metadata blindly.

## Release checks

1. Validate the exact current commit with local repository gates and green hosted CI. Existing Linux CI covers code and deployment fixtures; it does not run real macOS WARP.
2. Transfer the sources and tests above. Remove checkout paths, personal profile assumptions and mandatory fish integration. Select a package name, licence, versioning and supported installation method.
3. Test installation into a clean user environment without the devbox checkout. The current live gate requires an already installed compatible supervisor, so it is not a first-install test.
4. Exercise install, upgrade from legacy state, on/off, failed activation, interrupted restoration and uninstall. Include Docker running, a DNS-port conflict and unavailable DNS. Verify original WARP state and recovery metadata after every failure case.
5. Run live DNS/HTTPS checks on the supported macOS/WARP versions and record their limits. Keep live tests explicit: they change host networking. Publish only after that evidence exists; then replace devbox's copied controller with installation of the tested package version.
