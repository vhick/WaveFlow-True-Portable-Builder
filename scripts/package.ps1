param(
  [Parameter(Mandatory=$true)][string]$Source,
  [Parameter(Mandatory=$true)][string]$BuilderRoot
)
$ErrorActionPreference = 'Stop'
$Source = [IO.Path]::GetFullPath($Source)
$BuilderRoot = [IO.Path]::GetFullPath($BuilderRoot)
$base = Join-Path $BuilderRoot 'dist/WaveFlowPortable'
$zip = Join-Path $BuilderRoot 'dist/WaveFlowPortable-v1.8.4-win64.zip'
if (Test-Path -LiteralPath $base) { Remove-Item -LiteralPath $base -Recurse -Force }
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
foreach ($rel in @('App','App/AppInfo','Data','Data/TraceGuard','Data/Tauri','Data/Logs','Data/Roaming','Data/Local','Data/Temp','Data/Home','Other','Other/Source')) {
  New-Item -ItemType Directory -Path (Join-Path $base $rel) -Force | Out-Null
}
$exe = Join-Path $Source 'src-tauri/target/release/waveflow.exe'
$launcher = Join-Path $BuilderRoot 'launcher/WaveFlowPortable.exe'
if (!(Test-Path -LiteralPath $exe)) { throw 'Built WaveFlow.exe missing' }
if (!(Test-Path -LiteralPath $launcher)) { throw 'Native launcher missing' }
Copy-Item -LiteralPath $exe -Destination (Join-Path $base 'App/WaveFlow.exe')
Copy-Item -LiteralPath $launcher -Destination (Join-Path $base 'WaveFlowPortable.exe')
$icon = Join-Path $Source 'src-tauri/crates/app/icons/icon.ico'
Copy-Item -LiteralPath $icon -Destination (Join-Path $base 'App/AppInfo/appicon.ico')
$png = Join-Path $Source 'src-tauri/crates/app/icons/32x32.png'
if (Test-Path -LiteralPath $png) { Copy-Item -LiteralPath $png -Destination (Join-Path $base 'App/AppInfo/appicon.png') }
$pngBig = Join-Path $Source 'src-tauri/crates/app/icons/128x128.png'
if (Test-Path -LiteralPath $pngBig) { Copy-Item -LiteralPath $pngBig -Destination (Join-Path $base 'App/AppInfo/appicon_128.png') }
# --no-bundle produces no installer; copy the Tauri resources explicitly.
$plugins = Join-Path $Source 'src-tauri/resources/plugins'
if (!(Test-Path -LiteralPath $plugins)) { throw "Bundled plugin resources missing: $plugins" }
Copy-Item -LiteralPath $plugins -Destination (Join-Path $base 'App/plugins') -Recurse -Force
Copy-Item -LiteralPath (Join-Path $Source 'LICENSE') -Destination (Join-Path $base 'Other/Source/GPL-3.0-LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $Source 'THIRD_PARTY_NOTICES.md') -Destination (Join-Path $base 'Other/Source/THIRD_PARTY_NOTICES.md')
@'
[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=WaveFlow Portable
AppID=WaveFlowPortable
Publisher=InstaZDLL / Portable builder (unofficial)
Homepage=https://github.com/InstaZDLL/WaveFlow
Category=Music & Video
Description=WaveFlow Hi-Res music player, portable source build
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion=1.8.4.0
DisplayVersion=1.8.4

[Control]
Icons=1
Start=WaveFlowPortable.exe
'@ | Set-Content -LiteralPath (Join-Path $base 'App/AppInfo/appinfo.ini') -Encoding utf8
@'
WaveFlow Portable v1.8.4

RUN: WaveFlowPortable.exe at the top level; not App/WaveFlow.exe.
Music library and profile data: Data/Tauri/waveflow/.
WebView2 data and logs are redirected to folders inside Data.
Use the tray menu Quit to exit completely and finish TraceGuard logging.
This edition disables Windows autostart and installer-based self-updates.
To update the app, replace the App and Other folders and launcher, KEEP the Data folder.
Optional features such as MPD, DLNA, remote server sync and media controls may use OS state.
WebView2 Runtime must be present on the Windows computer.
Existing nonportable WaveFlow profile data are NOT automatically imported or deleted.
Move to a new machine may break absolute music-library paths; reselect folders if required.
TraceGuard safely reports activity; never deletes nonempty user files or pre-existing traces.

This is an unofficial portable build of a GPL-3.0-only application.
Source: https://github.com/InstaZDLL/WaveFlow (v1.8.4)
'@ | Set-Content -LiteralPath (Join-Path $base 'Other/PORTABLE-README.txt') -Encoding utf8
foreach($rel in @('Data/KEEP.txt','Data/TraceGuard/KEEP.txt')) {
  'Keep this folder when upgrading. No user data will be overwritten.' | Set-Content -LiteralPath (Join-Path $base $rel) -Encoding ascii
}
Compress-Archive -LiteralPath $base -DestinationPath $zip -CompressionLevel Optimal
if ((Get-Item -LiteralPath $zip).Length -lt 100000) { throw 'Unexpectedly small portable ZIP' }
Write-Host "Created $zip"
