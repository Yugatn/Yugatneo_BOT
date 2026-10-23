# AMALGAMA Guardian for Linux — deployment blueprint

**Not a tested DEB/RPM package or install script.** These are example systemd units for a controlled test VM. They are NOT installed automatically.

## Prerequisites

- Linux with systemd, Python 3.11+, cryptography package installed for the same Python interpreter.
- A dedicated unprivileged `amalgama` service user.
- Trusted code installed read-only at `/opt/amalgama`, with the `amalgama` Python package importable.
- Signed agent envelope in `/etc/amalgama/signed-agents.json`, pinned Ed25519 public key in root-owned `/etc/amalgama/guardian.env`.
- `/opt/amalgama/agents` exists and is readable by the service user.
- Verify signed manifests, trusted key distribution, filesystem permissions, and backups before enabling any service.

Example environment file: `AMALGAMA_PUBLIC_KEY_HEX=<64 hex characters>`. Do not put a private key here. Public keys must be obtained independently; no TOFU.

### Manual activation only

Review and adapt the unit for the actual Linux distribution and Python import path. Install the units with administrator authorization, then run `systemd-analyze verify` and a single manual `systemctl start amalgama-guardian.service`. Inspect `journalctl -u amalgama-guardian.service` before considering `systemctl enable --now amalgama-guardian.timer`.

The service is intended to be offline (`PrivateNetwork=yes`) and read-only. **The current implementation has not been tested in a real sandbox**. Its security depends on systemd/kernel and the host trust boundary. The systemd environment variable expansion and Python path must be checked on target distribution. Never enable the timer by default.

## Linux repository integration

Proposed future DEB/RPM packages: separate agent, policy files, public key bundle, opt-in systemd timer and signed repository metadata. Package installation must be initiated by the owner. Repository packages must not replace bootloader, format disks, or modify EFI variables.

## Live USB

A bootable ISO is **not yet built**. Proposed workflow: derive a read-only Live environment from an established Linux distribution, sign images and verify Secure Boot compatibility, provide diagnostic mode with no automatic disk writes, and offer an opt-in package installation with preview and rollback. USB insertion alone cannot start software.

## Caveats

This systemd unit is a proposed hardening profile, not proof of full isolation. A compromised kernel or privileged host process can undermine the Guardian. For higher assurance, consider external hardware attestation or separate trusted machine.
