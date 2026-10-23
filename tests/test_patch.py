"""Offline fail-closed patch regression tests; no third-party modules needed."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH = ROOT / 'scripts' / 'patch_portable.py'
GET_SET = '''#[tauri::command]
pub async fn get_auto_start(app: tauri::AppHandle) -> AppResult<bool> {
    Ok(app.autolaunch().is_enabled().unwrap_or(false))
}
#[tauri::command]
pub async fn set_auto_start(app: tauri::AppHandle, enabled: bool) -> AppResult<()> {
    let manager = app.autolaunch();
    let result = if enabled {
        manager.enable()
    } else {
        manager.disable()
    };
    result.map_err(|err| crate::error::AppError::Other(format!("autostart: {err}")))?;
    Ok(())
}
'''
LIB = '''// This part is the Tauri Builder plugin chain.
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
        .plugin(tauri_plugin_opener::init())
'''


def setup_tree(root, auto=GET_SET, lib=LIB):
    paths = {
        'package.json': json.dumps({'version':'1.8.4'}),
        'src-tauri/crates/app/tauri.conf.json': json.dumps({'identifier':'app.waveflow','version':'1.8.4','app':{},'bundle':{'active':True}}),
        'src-tauri/crates/app/Cargo.toml': 'default = ["updater", "sync_v2"]',
        'src-tauri/crates/app/src/paths.rs': '    pub fn root_for_identifier(identifier: &str) -> AppResult<PathBuf> {\n        dirs::data_dir()',
        'src-tauri/crates/app/src/logging.rs': 'fn resolve_log_dir() -> Option<PathBuf> {',
        'src-tauri/crates/app/src/commands/preferences.rs': auto + '\n/// UI zoom level (1.0 = 100 %). Stored in `app_setting`.\nconst KEY_UI_ZOOM: &str = "ui.zoom_level";',
        'src-tauri/crates/app/src/lib.rs': lib,
    }
    for name, data in paths.items():
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data, encoding='utf-8')


def run_patch(root):
    return subprocess.run([sys.executable, str(PATCH), '--source', str(root)], text=True, capture_output=True)


class PortablePatchTests(unittest.TestCase):
    def test_original_source_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            setup_tree(root)
            result = run_patch(root)
            self.assertEqual(0, result.returncode, result.stderr)
            prefs = (root / 'src-tauri/crates/app/src/commands/preferences.rs').read_text()
            self.assertIn('pub async fn get_auto_start(_app:', prefs)
            self.assertIn('/// UI zoom level', prefs)
            self.assertNotIn('manager.enable()', prefs)
            lib = (root / 'src-tauri/crates/app/src/lib.rs').read_text()
            self.assertIn('.plugin(tauri_plugin_opener::init())', lib)
            self.assertNotIn('.plugin(tauri_plugin_autostart::init(', lib)

    def test_blank_lines_and_windows_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source = GET_SET.replace('}\n#[tauri::command]', '}\n\n#[tauri::command]')
            source = source.replace('}\n', '}\r\n')
            lib = LIB.replace('        .plugin(tauri_plugin_opener::init())', '\n        .plugin(tauri_plugin_opener::init())')
            setup_tree(root, auto=source, lib=lib)
            result = run_patch(root)
            self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_unknown_additional_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            added = GET_SET + '#[tauri::command]\npub async fn extra() {}\n'
            setup_tree(root, auto=added)
            result = run_patch(root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('unexpected additional commands', result.stderr)

    def test_rejects_unfamiliar_registry_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            setup_tree(root, auto=GET_SET.replace('manager.disable()', 'do_something_else()'))
            result = run_patch(root)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('manager.disable()', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
