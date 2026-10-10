# Installs a ZPS 2.4 dedicated server with the bots on Windows.
#
#   powershell -ExecutionPolicy Bypass -File install.ps1 [-ServerDir C:\zps24-server]
#
# Steps:
#   1. SteamCMD, then the ZPS 2.4 dedicated server (app 17505, beta legacy2.4)
#   2. SourceMod 1.12 (official Windows build)
#   3. This package: patched Metamod:Source, NavBot, gamedata, the AI plugins, configs, nav meshes
#   4. The cabin and church maps, copied from your ZPS 2.4 game if Steam has it installed
#   5. Admin rights for this PC (by LAN IP), a start script, a firewall rule
# Run it again any time to update; your configs are kept.
param(
	[string]$ServerDir = "C:\zps24-server"
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'      # Invoke-WebRequest is very slow with the progress bar
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pkg = Split-Path -Parent $here                 # the unpacked release (addons\, cfg\, scripts\)
if (-not (Test-Path "$pkg\addons")) { $pkg = $here }

function Step($text) { Write-Host "== $text" -ForegroundColor Cyan }
function Download($url, $out) { Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing }

New-Item -ItemType Directory -Force -Path $ServerDir | Out-Null
$zps = Join-Path $ServerDir 'zps'

Step "1. SteamCMD and the ZPS 2.4 dedicated server (about 6 GB the first time)"
$steamcmd = Join-Path $ServerDir 'steamcmd'
if (-not (Test-Path "$steamcmd\steamcmd.exe")) {
	New-Item -ItemType Directory -Force -Path $steamcmd | Out-Null
	Download 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip' "$env:TEMP\steamcmd.zip"
	Expand-Archive -Force "$env:TEMP\steamcmd.zip" $steamcmd
}
& "$steamcmd\steamcmd.exe" +force_install_dir "$ServerDir" +login anonymous +app_update 17505 -beta legacy2.4 validate +quit
if (-not (Test-Path "$ServerDir\srcds.exe")) { throw "SteamCMD did not install the server (no srcds.exe in $ServerDir)" }

Step "2. SourceMod 1.12 (official build)"
$smdrop = 'https://sm.alliedmods.net/smdrop/1.12'
$smFile = (Invoke-WebRequest -Uri "$smdrop/sourcemod-latest-windows" -UseBasicParsing).Content.Trim()
$tmp = Join-Path $env:TEMP 'zps24-sm'
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
Download "$smdrop/$smFile" "$env:TEMP\$smFile"
Expand-Archive -Force "$env:TEMP\$smFile" $tmp
New-Item -ItemType Directory -Force -Path "$zps\addons", "$zps\cfg" | Out-Null
Copy-Item -Recurse -Force "$tmp\addons\sourcemod" "$zps\addons\"
Get-ChildItem "$tmp\cfg" -Recurse -File | ForEach-Object {         # keep existing configs
	$dest = Join-Path "$zps\cfg" $_.FullName.Substring("$tmp\cfg".Length + 1)
	if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null; Copy-Item $_.FullName $dest }
}
$core = "$zps\addons\sourcemod\configs\core.cfg"
(Get-Content $core) -replace '"DisableAutoUpdate"\s*"no"', '"DisableAutoUpdate"		"yes"' | Set-Content $core

Step "3. Metamod:Source, NavBot, gamedata, plugins (this package)"
Copy-Item -Recurse -Force "$pkg\addons\*" "$zps\addons\"
foreach ($f in @('server.cfg', 'sourcemod\plugin.navbot_quota.cfg')) {
	$dest = "$zps\cfg\$f"
	if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null; Copy-Item "$pkg\cfg\$f" $dest }
}
if (-not (Test-Path "$zps\mapcycle_bots.txt")) { Copy-Item "$pkg\mapcycle_bots.txt" "$zps\" }

Step "4. Maps (cabin and church come with the ZPS 2.4 game)"
$maps = @('zpo_cabin_outbreak_b8_com.bsp', 'zpo_church_siege_final_h.bsp')
$libs = @()
$steam = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
if ($steam) {
	$libs += $steam
	$vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
	if (Test-Path $vdf) {
		Select-String -Path $vdf -Pattern '"path"\s+"([^"]+)"' | ForEach-Object { $libs += $_.Matches[0].Groups[1].Value -replace '\\\\', '\' }
	}
}
foreach ($m in $maps) {
	if (Test-Path "$zps\maps\$m") { continue }
	$found = $null
	foreach ($l in $libs) {
		$p = Join-Path $l "steamapps\common\Zombie Panic Source\zps\maps\$m"
		if (Test-Path $p) { $found = $p; break }
	}
	if ($found) { Copy-Item $found "$zps\maps\"; Write-Host "  copied $m" }
	else { Write-Warning "  $m not found. Install ZPS 2.4 (Steam: Zombie Panic! Source > Properties > Betas > legacy2.4) and run this again, or copy the map into $zps\maps." }
}

Step "5. Admin, start script, firewall"
$ip = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null } | Select-Object -First 1).IPv4Address.IPAddress
if (-not $ip) { $ip = '127.0.0.1' }
$admins = "$zps\addons\sourcemod\configs\admins_simple.ini"
if (-not (Select-String -Path $admins -Pattern "`"!$ip`"" -Quiet)) { Add-Content $admins "`"!$ip`"`t`"99:z`"" }
$pwFile = Join-Path $ServerDir 'rcon_password.txt'
if (-not (Test-Path $pwFile)) { -join ((48..57) + (97..102) | Get-Random -Count 32 | ForEach-Object { [char]$_ }) | Set-Content $pwFile }
$pw = (Get-Content $pwFile).Trim()
@"
@echo off
rem Starts the ZPS 2.4 bot server. Players join with: connect $ip
rem Type commands into the server window (sm_zps24ai_status, changelevel ..., quit).
cd /d "%~dp0"
start "ZPS 2.4 bots" srcds.exe -console -game zps -insecure +ip $ip +sv_lan 1 +maxplayers 24 +rcon_password "$pw" +map zpo_cabin_outbreak_b8_com
"@ | Set-Content -Encoding ASCII "$ServerDir\start-server.bat"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
	if (-not (Get-NetFirewallRule -DisplayName 'ZPS 2.4 server' -ErrorAction SilentlyContinue)) {
		New-NetFirewallRule -DisplayName 'ZPS 2.4 server' -Direction Inbound -Program "$ServerDir\srcds.exe" -Action Allow | Out-Null
	}
} else {
	Write-Host "  (Not running as administrator: Windows will ask to allow srcds.exe through the firewall the first time it starts.)"
}

Write-Host ""
Write-Host "Done. Start the server with $ServerDir\start-server.bat" -ForegroundColor Green
Write-Host "In ZPS 2.4 open the console (~) and type: connect $ip"
