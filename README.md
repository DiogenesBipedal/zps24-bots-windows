# ZPS 2.4 Bots for Windows

The Windows version of [zps24-bots](https://github.com/DiogenesBipedal/zps24-bots): NavBot
bots with the survivor and zombie AI for a **Zombie Panic! Source 2.4** dedicated server running
on Windows. Same bots, same AI, same learning from your play.

**Install:** download the zip from [Releases](../../releases), unzip, double-click
`install.bat`. Full guide: [docs/INSTALL.md](docs/INSTALL.md).

## What's in this repo

The AI plugins, configs and source patches are shared with the Linux build (`core/`, a submodule
of the main repo). This repo adds what Windows needs:

- **Windows builds** of the patched Metamod:Source and NavBot, made by GitHub Actions with MSVC
  (`.github/workflows/build-windows.yml`), with the same pinned versions and patches as Linux.
- **Windows gamedata** (`gamedata/`). ZPS 2.4's Windows `server.dll` has no symbols, so:
  - vtable offsets are computed from the Linux vtables with MSVC's layout rules
    (`tools/msvc_layout.py`): one destructor slot instead of two, overloads grouped in reverse.
    The computed vtable lengths match the real ones (found through RTTI) for every class used;
  - signatures were found by what the functions do (strings they print, how they're called) and
    made unique with `tools/makesig.py`.
  See [docs/PORTING.md](docs/PORTING.md).
- **Installer**: `scripts/install.ps1` (SteamCMD, the server, SourceMod, this package, maps,
  admin, firewall, start script).
- **Nav meshes** for the bot maps (`data/`).

Tested with the Windows 2.4 dedicated server under Wine 11 on Linux
(`scripts/wine-server.sh`).

**Status: v1.0.** Built by CI with MSVC and tested under Wine; not yet on a real Windows PC.
If something fails there, please open an issue with the server console output.
