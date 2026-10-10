# ZPS 2.4 Bots for Windows: install

Bots for **Zombie Panic! Source 2.4** on a dedicated server you run on your own Windows PC:
survivor bots that defend their house, barricade with furniture and fight from a safe
distance; zombie bots that break in through windows, knock planks off doors and hunt everyone
down; and both learn from the way you play.

## What you need

- Windows 10 or 11 (64-bit is fine; the server is 32-bit).
- About 7 GB of free disk space.
- **ZPS 2.4** in Steam, to play on the server and for the two bot maps: Steam > Library >
  Zombie Panic! Source > Properties > Betas > choose `legacy2.4`.

## Install

1. Unzip this package anywhere.
2. Double-click **install.bat**. It installs everything into `C:\zps24-server`:
   - the ZPS 2.4 dedicated server (through SteamCMD, about 6 GB the first time);
   - SourceMod 1.12;
   - Metamod:Source and NavBot built for ZPS 2.4, the bot AI plugins, configs and the nav
     meshes for the bot maps;
   - the cabin and church maps, copied from your ZPS 2.4 game.

   To install somewhere else, run from a command prompt:
   `install.bat -ServerDir D:\zps24-server`
3. Run **C:\zps24-server\start-server.bat**. Allow srcds.exe through the Windows firewall if asked.
4. Start ZPS 2.4, open the console (`~`) and type the `connect` line the installer printed
   (`connect <your PC's LAN IP>`).

Run install.bat again any time to update. Your configs are kept.

## Playing

- **M** opens the admin menu (your PC is admin automatically): add or remove bots, bot
  skill, change map, spawn items, radio.
- The server window is a console: type commands there, e.g. `changelevel zpo_church_siege_final_h`,
  `sm_zps24ai_status`, `sm_zps24learn_status`, `quit`.
- The bots learn from you as you play: your hold-out spots, routes, furniture placements,
  break-ins as a zombie, and how close you let zombies get. See the main project's docs.

## Other maps

Bots need a nav mesh for each map. On a new map, in the server console:

```
sv_cheats 1
sm_nav_generate
```

Wait until it says the mesh was saved (a minute or two), then `sv_cheats 0` and change map.

## Settings and docs

All settings, commands and how everything works are in the main project:
https://github.com/DiogenesBipedal/zps24-bots (docs/SETTINGS.md, docs/MANUAL.md).

## Known differences from Linux

- The barricade hammer check (`CanAttachBarricade`) doesn't exist in the Windows server.dll,
  so bots barricade with furniture only (the default on Linux too).
