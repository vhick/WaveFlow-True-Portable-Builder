// WaveFlow Portable v1.0 launcher: native Windows, no administrator rights.
// Changes to environment are child-process-only; does not modify registry.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <set>
#include <ctime>
#include <iomanip>

namespace fs = std::filesystem;

static std::wstring envValue(const wchar_t* key) {
    DWORD len = GetEnvironmentVariableW(key, nullptr, 0);
    if (!len) return L"";
    std::vector<wchar_t> buf(len + 1, 0);
    DWORD copied = GetEnvironmentVariableW(key, buf.data(), (DWORD)buf.size());
    return copied ? std::wstring(buf.data(), copied) : L"";
}
static void setEnv(const wchar_t* key, const fs::path& value) {
    SetEnvironmentVariableW(key, value.c_str());
}
static bool registryKeyPresent(HKEY hive, const wchar_t* path) {
    HKEY key = nullptr;
    LONG result = RegOpenKeyExW(hive, path, 0, KEY_READ, &key);
    if (result == ERROR_SUCCESS) RegCloseKey(key);
    return result == ERROR_SUCCESS;
}
static bool startupValuePresent() {
    HKEY key = nullptr;
    LONG result = RegOpenKeyExW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, KEY_QUERY_VALUE, &key);
    if (result != ERROR_SUCCESS) return false;
    const wchar_t* values[] = { L"WaveFlow", L"waveflow", L"WaveFlowPortable" };
    bool found = false;
    for (auto value : values) {
        if (RegQueryValueExW(key, value, nullptr, nullptr, nullptr, nullptr) == ERROR_SUCCESS) found = true;
    }
    RegCloseKey(key);
    return found;
}
static void logEntry(const fs::path& logPath, const std::wstring& event) {
    std::wofstream output(logPath, std::ios::app);
    if (!output) return;
    std::time_t now = std::time(nullptr);
    std::tm tmBuf{};
    localtime_s(&tmBuf, &now);
    output << std::put_time(&tmBuf, L"%Y-%m-%d %H:%M:%S") << L" | " << event << L"\n";
}
static std::wstring trailingArgs() {
    const wchar_t* cmd = GetCommandLineW();
    if (!cmd) return L"";
    if (*cmd == L'"') {
        ++cmd;
        while (*cmd && *cmd != L'"') ++cmd;
        if (*cmd == L'"') ++cmd;
    } else {
        while (*cmd && *cmd != L' ' && *cmd != L'\t') ++cmd;
    }
    while (*cmd == L' ' || *cmd == L'\t') ++cmd;
    return std::wstring(cmd);
}
static int fail(const std::wstring& text, const fs::path& log) {
    if (!log.empty()) logEntry(log, L"ERROR: " + text);
    MessageBoxW(nullptr, text.c_str(), L"WaveFlow Portable", MB_OK | MB_ICONERROR);
    return 1;
}
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    wchar_t selfBuf[32768]{};
    DWORD n = GetModuleFileNameW(nullptr, selfBuf, 32768);
    if (!n || n == 32768) return fail(L"Cannot locate the portable launcher.", fs::path());
    fs::path base = fs::path(selfBuf).parent_path();
    fs::path data = base / L"Data";
    fs::path log = data / L"TraceGuard" / L"TraceGuard.log";
    fs::path program = base / L"App" / L"WaveFlow.exe";
    std::error_code ec;
    for (const wchar_t* sub : { L"Tauri", L"Roaming", L"Local", L"Logs", L"Temp", L"Home", L"TraceGuard" }) {
        fs::create_directories(data / sub, ec);
        if (ec) return fail(L"Cannot write to the portable Data folder. Please move WaveFlowPortable to a writable drive.", log);
    }
    if (!fs::exists(program, ec)) return fail(L"Missing App\\WaveFlow.exe. Extract the complete portable ZIP.", log);

    const fs::path originalRoaming(envValue(L"APPDATA"));
    const fs::path originalLocal(envValue(L"LOCALAPPDATA"));
    const fs::path originalHome(envValue(L"USERPROFILE"));
    std::vector<fs::path> watched;
    // Explicit app-named host directories only. Never scan/delete shared Windows caches.
    for (const auto& path : { originalRoaming, originalLocal }) {
        if (path.empty()) continue;
        watched.push_back(path / L"app.waveflow");
        watched.push_back(path / L"waveflow");
        watched.push_back(path / L"WaveFlow");
    }
    if (!originalHome.empty()) watched.push_back(originalHome / L".waveflow");
    std::vector<bool> existed;
    for (const auto& path : watched) existed.push_back(fs::exists(path, ec));
    bool softwareBefore = registryKeyPresent(HKEY_CURRENT_USER, L"Software\\WaveFlow");
    bool startupBefore = startupValuePresent();
    logEntry(log, L"===== portable launch =====");
    logEntry(log, L"Launcher root: " + base.wstring());
    logEntry(log, L"App data: " + (data / L"Tauri").wstring());

    // Child-only environment — actual Windows profile state is not changed.
    setEnv(L"APPDATA", data / L"Roaming");
    setEnv(L"LOCALAPPDATA", data / L"Local");
    setEnv(L"USERPROFILE", data / L"Home");
    setEnv(L"HOME", data / L"Home");
    setEnv(L"TEMP", data / L"Temp");
    setEnv(L"TMP", data / L"Temp");
    setEnv(L"WAVEFLOW_PORTABLE_ROOT", data);
    setEnv(L"WAVEFLOW_PORTABLE_DATA", data / L"Tauri");
    // Avoid polluting the user's working directory with temp/relative writes.
    SetCurrentDirectoryW((base / L"App").c_str());

    std::wstring fullCommand = L"\"" + program.wstring() + L"\"";
    std::wstring additional = trailingArgs();
    if (!additional.empty()) fullCommand += L" " + additional;
    std::vector<wchar_t> command(fullCommand.begin(), fullCommand.end());
    command.push_back(L'\0');
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION child{};
    BOOL launched = CreateProcessW(program.c_str(), command.data(), nullptr, nullptr, FALSE,
                                   0, nullptr, (base / L"App").c_str(), &startup, &child);
    if (!launched) return fail(L"Failed to launch App\\WaveFlow.exe (Windows error " + std::to_wstring(GetLastError()) + L").", log);
    CloseHandle(child.hThread);
    // Wait until the tray process REALLY exits, so databases and logs flush.
    WaitForSingleObject(child.hProcess, INFINITE);
    DWORD exitCode = 1;
    GetExitCodeProcess(child.hProcess, &exitCode);
    CloseHandle(child.hProcess);
    logEntry(log, L"WaveFlow exited; exit code=" + std::to_wstring(exitCode));

    for (size_t i = 0; i < watched.size(); ++i) {
        const auto& path = watched[i];
        if (existed[i]) continue; // pre-existing files/dirs MUST be preserved
        if (!fs::exists(path, ec)) continue;
        if (fs::is_directory(path, ec) && !fs::is_symlink(path, ec) && fs::is_empty(path, ec)) {
            if (fs::remove(path, ec)) {
                logEntry(log, L"Removed newly created EMPTY app-specific directory: " + path.wstring());
            }
        } else {
            logEntry(log, L"REVIEW: newly created nonempty app-specific host path (preserved): " + path.wstring());
        }
    }
    if (!softwareBefore && registryKeyPresent(HKEY_CURRENT_USER, L"Software\\WaveFlow")) {
        logEntry(log, L"REVIEW: newly detected HKCU\\Software\\WaveFlow (preserved)");
    }
    if (!startupBefore && startupValuePresent()) {
        logEntry(log, L"REVIEW: newly detected WaveFlow startup value (preserved)");
    }
    logEntry(log, L"TraceGuard finished. Pre-existing paths untouched; no shared Windows cache deletion.");
    return static_cast<int>(exitCode);
}
