# v1.1 — 2026-10-23

- Fixes GitHub Actions failure `PATCH FAILED disable Windows startup registry integration: expected exactly 1 original snippet, got 0`.
- Safely matches both upstream autostart function boundaries regardless of harmless whitespace differences.
- Validates that the only removed code contains exactly the expected registry-changing autostart calls; fails closed on unfamiliar code.
- Makes removal of the Tauri autostart-plugin registration whitespace-tolerant.
- No changes to compiled launcher behavior, data isolation, TraceGuard, official source version, or output layout.
- The full Windows build has not been executed locally.

# WaveFlow True Portable Builder

## v1.0 — 2026-10-23

- First standalone manually triggered GitHub Actions source builder for official v1.8.4.
- Original icon, PortableApps-compatible native launcher, ZIP-only artifact.
- Fail-closed portable source patches for Tauri data paths, preflight database, logs, updater, and autostart.
- Keep the `sync_v2` feature and embedded bundled plugin resources.
- Child environment redirection and conservative TraceGuard snapshots.
- App/Data/Other layout with Data preservation on app upgrades.
- First Windows compile is not yet verified.
