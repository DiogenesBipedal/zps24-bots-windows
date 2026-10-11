#!/bin/bash
# Assemble the Windows release folder. Used by CI; works anywhere with bash.
#   package.sh BINDIR SMDIR OUTDIR
#     BINDIR: built addons (addons/metamod, addons/sourcemod/extensions + NavBot's gamedata/configs)
#     SMDIR:  an unpacked official SourceMod (for spcomp and its includes)
#     OUTDIR: where to put the release folder
set -e
BIN=$1; SM=$2; OUT=$3
REPO=$(cd "$(dirname "$0")/.." && pwd)
CORE=$REPO/core
rm -rf "$OUT"; mkdir -p "$OUT"
A=$OUT/addons
mkdir -p "$A/metamod" "$A/sourcemod"
cp -r "$BIN/addons/metamod/." "$A/metamod/"
rm -f "$A/metamod/metaplugins.ini"
printf '"Plugin"\n{\n\t"file"\t"addons/metamod/bin/server"\n}\n' > "$A/metamod.vdf"
printf '"Metamod Plugin"\n{\n\t"alias"\t\t"sourcemod"\n\t"file"\t\t"addons/sourcemod/bin/sourcemod_mm"\n}\n' > "$A/metamod/sourcemod.vdf"
cp -r "$BIN/addons/sourcemod/." "$A/sourcemod/"
rm -rf "$A/sourcemod/scripting"
# Gamedata with Windows entries
G=$A/sourcemod/gamedata
mkdir -p "$G/navbot.games" "$G/sdktools.games" "$G/sdkhooks.games" "$G/core.games/custom"
cp "$REPO/gamedata/navbot.games-game.zps.txt"      "$G/navbot.games/game.zps.txt"
cp "$REPO/gamedata/sdktools.games-game.zpanic.txt" "$G/sdktools.games/game.zpanic.txt"
cp "$REPO/gamedata/sdkhooks.games-game.zpanic.txt" "$G/sdkhooks.games/game.zpanic.txt"
cp "$REPO/gamedata/core.games-custom-zps24.txt"    "$G/core.games/custom/zps24.txt"
cp "$REPO/gamedata/zps24_ai.games.txt"             "$G/zps24_ai.games.txt"
mkdir -p "$A/sourcemod/configs/navbot/zps"
cp "$CORE/configs/navbot/weapons.cfg" "$A/sourcemod/configs/navbot/zps/weapons.cfg"
cp "$CORE/configs/zps24_maps.cfg" "$A/sourcemod/configs/"
mkdir -p "$A/sourcemod/data/navbot/zps"
cp "$REPO"/data/navbot/zps/*.smnav "$A/sourcemod/data/navbot/zps/"
# Plugins (same sources as Linux)
mkdir -p "$A/sourcemod/plugins"
SPCOMP=$SM/addons/sourcemod/scripting/spcomp.exe
[ -x "$SPCOMP" ] || SPCOMP=$SM/addons/sourcemod/scripting/spcomp
for p in zps24_compat zps24_botprobe zps24_navdebug zps24_ammorespawn zps24_learn zps24_survivors zps24_zombies zps24_admin zps24_radio navbot_quota; do
	"$SPCOMP" -i"$SM/addons/sourcemod/scripting/include" -i"$BIN/addons/sourcemod/scripting/include" -i"$CORE/plugins" \
		"$CORE/plugins/$p.sp" -o"$A/sourcemod/plugins/$p.smx" > /dev/null
done
# Configs
mkdir -p "$OUT/cfg/sourcemod"
cp "$CORE/configs/server.cfg" "$OUT/cfg/server.cfg"
cp "$CORE/configs/plugin.navbot_quota.cfg" "$OUT/cfg/sourcemod/"
cp "$CORE/configs/mapcycle_bots.txt" "$OUT/"
# Installer
mkdir -p "$OUT/scripts"
cp "$REPO/scripts/install.ps1" "$OUT/scripts/"
printf '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%%~dp0scripts\\install.ps1" %%*\r\npause\r\n' > "$OUT/install.bat"
cp "$REPO/docs/INSTALL.md" "$OUT/README.md"
echo "Packaged into $OUT"
