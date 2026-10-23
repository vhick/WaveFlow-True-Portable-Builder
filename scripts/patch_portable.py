#!/usr/bin/env python3
"""Fail-closed patch for WaveFlow v1.8.4 portable distribution."""
import argparse, json, pathlib, re, sys

p = argparse.ArgumentParser()
p.add_argument('--source', required=True)
a = p.parse_args()
root = pathlib.Path(a.source).resolve()
config_path = root / 'src-tauri/crates/app/tauri.conf.json'
paths_path = root / 'src-tauri/crates/app/src/paths.rs'
logs_path = root / 'src-tauri/crates/app/src/logging.rs'
prefs_path = root / 'src-tauri/crates/app/src/commands/preferences.rs'
lib_path = root / 'src-tauri/crates/app/src/lib.rs'
package_path = root / 'package.json'
cargo_path = root / 'src-tauri/crates/app/Cargo.toml'

def patch_once(path, old, new, label):
    s = path.read_text(encoding='utf-8')
    hits = s.count(old)
    if hits != 1:
        raise RuntimeError(f'PATCH FAILED {label}: expected exactly 1 original snippet, got {hits}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')
    print('PATCHED:', label)

package = json.loads(package_path.read_text(encoding='utf-8'))
config = json.loads(config_path.read_text(encoding='utf-8'))
if config.get('identifier') != 'app.waveflow' or config.get('version') != '1.8.4' or package.get('version') != '1.8.4':
    raise RuntimeError('Refusing unverified upstream version/identifier; this builder targets WaveFlow v1.8.4')
if 'appDirectoriesOverride' in config['app']:
    raise RuntimeError('Unexpected pre-existing override in upstream configuration')
# EXE will be packaged at App/WaveFlow.exe, so ../Data is the portable root.
config['app']['appDirectoriesOverride'] = '../Data/Tauri'
# No bundled installer and no updater for the portable build.
config['bundle']['active'] = False
config['bundle']['targets'] = []
config['bundle']['createUpdaterArtifacts'] = False
config.pop('plugins',None)  # updater plugin uses Cargo feature gating, disabled at build
config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
print('PATCHED: config (dedicated Tauri data path, no installers/updater)')
patch_once(cargo_path, 'default = ["updater", "sync_v2"]', 'default = ["sync_v2"]', 'turn off installer updater by default while preserving sync_v2')
# Preflight occurs before Tauri initializes. Use the SAME storage root as Tauri.
patch_once(paths_path,
    '    pub fn root_for_identifier(identifier: &str) -> AppResult<PathBuf> {\n        dirs::data_dir()',
    '    pub fn root_for_identifier(identifier: &str) -> AppResult<PathBuf> {\n        if let Some(portable_root) = std::env::var_os("WAVEFLOW_PORTABLE_DATA") {\n            return Ok(PathBuf::from(portable_root).join("waveflow"));\n        }\n        dirs::data_dir()',
    'early preflight database root')
patch_once(logs_path,
    'fn resolve_log_dir() -> Option<PathBuf> {',
    'fn resolve_log_dir() -> Option<PathBuf> {\n    if let Some(portable_root) = std::env::var_os("WAVEFLOW_PORTABLE_ROOT") {\n        return Some(PathBuf::from(portable_root).join("Logs"));\n    }',
    'pre-Tauri log directory')
# v1.1: WaveFlow v1.8.4 uses variable whitespace/blank lines around these
# commands. Match the two FUNCTION BOUNDARIES, not an exact raw text block.
# Fail closed unless both functions and the actual registry-changing calls
# are present exactly once. The match stops BEFORE the unrelated UI zoom code.
autostart_text = prefs_path.read_text(encoding='utf-8')
get_decl = re.compile(r'(?m)^[ \t]*#\[tauri::command\][ \t]*\r?\n[ \t]*pub\s+async\s+fn\s+get_auto_start\s*\(')
set_decl = re.compile(r'(?m)^[ \t]*#\[tauri::command\][ \t]*\r?\n[ \t]*pub\s+async\s+fn\s+set_auto_start\s*\(')
get_matches = list(get_decl.finditer(autostart_text))
set_matches = list(set_decl.finditer(autostart_text))
if len(get_matches) != 1 or len(set_matches) != 1 or get_matches[0].start() >= set_matches[0].start():
    raise RuntimeError(f'PATCH FAILED autostart: expected one get/set command in order, found {len(get_matches)}/{len(set_matches)}')
start = get_matches[0].start()
# The next section begins with the application's UI zoom documentation.
zoom_marker = re.compile(r'(?m)^[ \t]*/// UI zoom level')
zoom = zoom_marker.search(autostart_text, set_matches[0].end())
if not zoom:
    raise RuntimeError('PATCH FAILED autostart: UI zoom section boundary not found')
end = zoom.start()
original_block = autostart_text[start:end]
# Strict checks: do not cut away extra commands or alter unexpected variants.
if len(re.findall(r'#\[tauri::command\]', original_block)) != 2:
    raise RuntimeError('PATCH FAILED autostart: unexpected additional commands in block')
for required, expected in (('app.autolaunch()', 2), ('manager.enable()', 1), ('manager.disable()', 1)):
    if original_block.count(required) != expected:
        raise RuntimeError(f'PATCH FAILED autostart: expected {expected} occurrence(s) of {required}')
if original_block.count('get_auto_start') != 1 or original_block.count('set_auto_start') != 1:
    raise RuntimeError('PATCH FAILED autostart: unexpected function signatures')
# Ensure function bodies end normally. Detect source changes instead of guessing.
if not re.search(r'\bOk\s*\(\s*\(\s*\)\s*\)\s*\}\s*$',original_block):
    raise RuntimeError('PATCH FAILED autostart: unexpected end of set_auto_start')
portable_autostart = '''#[tauri::command]
pub async fn get_auto_start(_app: tauri::AppHandle) -> AppResult<bool> {
    Ok(false)
}
#[tauri::command]
pub async fn set_auto_start(_app: tauri::AppHandle, enabled: bool) -> AppResult<()> {
    if enabled {
        return Err(crate::error::AppError::Other(
            "Windows autostart is disabled in the portable edition".into(),
        ));
    }
    Ok(())
}

'''
prefs_path.write_text(autostart_text[:start] + portable_autostart + autostart_text[end:],encoding='utf-8')
print('PATCHED: disable Windows startup registry integration (whitespace tolerant, bounded)')
# Remove only the exact registration block; allow harmless changes in spacing.
lib_text = lib_path.read_text(encoding='utf-8')
plugin_pattern = re.compile(
    r'(?ms)^[ \t]*\.plugin\(\s*tauri_plugin_autostart::init\(\s*'
    r'tauri_plugin_autostart::MacosLauncher::LaunchAgent\s*,\s*'
    r'Some\(vec!\["--minimized"\]\)\s*,?\s*\)\s*\)\s*'
    r'(?=^[ \t]*\.plugin\(tauri_plugin_opener::init\(\)\))'
)
patched_lib, plugin_hits = plugin_pattern.subn('',lib_text)
if plugin_hits != 1:
    raise RuntimeError(f'PATCH FAILED remove autostart plugin registration: expected one known block, got {plugin_hits}')
lib_path.write_text(patched_lib,encoding='utf-8')
print('PATCHED: remove autostart plugin registration (whitespace tolerant, bounded)')
summary = root / 'PORTABLE_PATCH_SUMMARY.txt'
summary.write_text('WaveFlow 1.8.4 true-portable patch\n'
                   'Tauri appDirectoriesOverride: ../Data/Tauri\n'
                   'Early preflight db root: WAVEFLOW_PORTABLE_DATA/waveflow\n'
                   'Logs: WAVEFLOW_PORTABLE_ROOT/Logs\n'
                   'Autostart: disabled\n'
                   'Updater: Cargo default features changed to [sync_v2]\n'
                   'No installer output; bundle resources copied by packaging script\n',encoding='utf-8')
print('PORTABLE PATCH SUCCESS. Original playback / plugin / sync_v2 features untouched.')
