# ZPS 2.4 Bots for Windows (work in progress)

The Windows version of [zps24-bots](https://github.com/DiogenesBipedal/zps24-bots): NavBot
bots and the survivor/zombie AI for a **Zombie Panic! Source 2.4** dedicated server running on
Windows.

The AI plugins, configs and source patches are shared with the Linux build (the `core`
submodule). This repo adds what Windows needs:

- Windows builds of the patched Metamod:Source and NavBot (GitHub Actions, MSVC).
- Windows gamedata. ZPS 2.4's Windows `server.dll` has no symbols, so every function the
  plugins and extensions use is found by vtable offset or byte signature.
- Install and start scripts for Windows.

**Status: in progress.** See [docs/PROGRESS.md](docs/PROGRESS.md).
