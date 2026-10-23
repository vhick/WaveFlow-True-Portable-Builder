# WaveFlow True Portable Builder v1.0

Standalone, **manual** GitHub Actions builder for [InstaZDLL/WaveFlow](https://github.com/InstaZDLL/WaveFlow) **v1.8.4**, Windows x64. This is a builder repository, NOT a finished Windows app.

## Use GitHub Desktop (no commands on your PC)

1. Extract this builder ZIP and open GitHub Desktop.
2. **File → New repository**; name it `WaveFlow-True-Portable-Builder`; uncheck *Initialize with README*.
3. **Repository → Show in Explorer**; copy the CONTENTS of this extracted folder into the repository folder. Keep `.github/workflows/build.yml` at the root.
4. Back in GitHub Desktop, commit all changes (e.g. `Add WaveFlow true portable builder v1.0`) and **Publish repository**.
5. Open your repository in the browser. Go to **Actions → Build WaveFlow True Portable → Run workflow** (branch `main`).
6. Once successful, open the run → **Artifacts** → `WaveFlowPortable-v1.8.4-win64` (available for 1 day).
7. Extract the downloaded artifact, then extract the contained `WaveFlowPortable-v1.8.4-win64.zip` to your PortableApps folder.
8. Launch **WaveFlowPortable.exe** at the top level, NOT `App/WaveFlow.exe`.

## Why source build instead of extracting an installer?

WaveFlow's v1.8.4 Windows release ships a `setup.exe`; the source has a pre-Tauri SQLite schema guard, a local log resolver, and an autostart registry toggle. The source is patched so these work safely with a portable `Data` folder, without modifying the audio engine.

## Files and features

- `App/WaveFlow.exe`: application built from upstream v1.8.4; Tauri context overrides app-specific data dirs to `../Data/Tauri`.
- `Data/Tauri/waveflow`: profiles, `app.db`, playlists, plugins, caches. Tauri WebView data stays in `Data`.
- `Data/Logs`: Rust application logs, pre-Tauri initialization included.
- `Data/Roaming`, `Data/Local`, `Data/Home`, `Data/Temp`: child-process-only environment redirection for paths not using Tauri.
- `Data/TraceGuard/TraceGuard.log`: conservative before/after host trace review.
- Original upstream icon is embedded in the native launcher and saved in `App/AppInfo`.
- `Other/Source`: GPL-3.0-only license and upstream third-party notices.
- The bundled official Web Radio plugin resources are copied into `App/plugins`.
- Cargo default features are patched to `["sync_v2"]` and Tauri builds with `--features sync_v2` to keep remote-source support while **excluding installer updates**.
- Windows autostart action is disabled at source to prevent a permanent HKCU Run entry.
- Manually triggered, ZIP-only output, one-day GitHub Actions artifact retention.

## Validation checklist

- Play FLAC, MP3, DSD, and test WASAPI exclusive mode only if your DAC supports it.
- Add a small music folder, create a playlist, change settings, switch skins, quit via the tray, then relaunch.
- Check `Data/Tauri/waveflow/app.db`, `Data/Logs` and `Data/TraceGuard/TraceGuard.log`.
- Move `WaveFlowPortable` to another drive: settings should remain, but absolute music folder paths may need reselecting.
- Test plugin store and network features. MPD, DLNA, Discord, Windows notifications and remote links may use external/OS services.
- Use the installed WebView2 Runtime provided by Windows. This package does not redistribute it.

## Precautions

- Always **Quit** using the tray menu before replacing the `App` directory or unplugging portable media. Closing the main window can leave the player running.
- On upgrades **KEEP `Data`**. Replace `App`, `Other`, and launcher only.
- Do not run installed and portable WaveFlow simultaneously; the single-instance guard might redirect the second launch.
- Existing nonportable WaveFlow settings are **not** imported or deleted.
- TraceGuard only removes **newly created and empty app-specific directories**, never registry entries, existing files or shared Windows caches. A zero-remnants guarantee cannot be made without live tests.
- As WaveFlow is GPL-3.0-only, anyone distributing modified portable binaries must comply with source-code and license obligations. This kit records modifications and includes original license files.

## Status

The ZIP was structurally checked and the source patch is based on reviewed v1.8.4 upstream source. **Windows build, functionality and zero-remnant behavior remain unverified until you run GitHub Actions and test Windows.** Please send Actions logs if the build fails.
