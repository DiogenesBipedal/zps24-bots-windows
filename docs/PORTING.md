# Porting the ZPS 2.4 bots to Windows

How the Windows build was made, for anyone redoing or checking it.

## 1. Binaries

The Linux build compiles a patched Metamod:Source 1.12 and NavBot 0.1.2-pr2 (see the core repo's
`scripts/build.sh` and `patches/`). The patches are portable C++, so the Windows build is the same
sources with MSVC, on a GitHub Actions Windows runner
(`.github/workflows/build-windows.yml`). One problem came up:

- **"The filename or extension is too long" when linking NavBot.** AMBuild names object files
  after their full source path, and NavBot has hundreds of files; from the default workspace
  (`D:\a\<repo>\<repo>\...`) the linker command passed Windows' 32K character limit. Building
  in `C:\w` fixed it.

## 2. Gamedata

SourceMod, SDKTools, SDKHooks and NavBot need to know where certain functions are in the game's
`server.dll`: either a **vtable offset** (the slot of a virtual function) or a **signature**
(a byte pattern that finds a non-virtual function). The Linux `server_i486.so` keeps its
symbols, so the Linux gamedata names things directly. The Windows `server.dll` has no symbols.

### Vtable offsets: computed, then verified

The 45 offsets are computed from the Linux vtables (`tools/msvc_layout.py`). GCC (Itanium ABI)
and MSVC both lay out virtual functions in declaration order, base class first, with two
differences:

1. **Destructors.** Itanium has two entries (complete-object and deleting destructor); MSVC has
   one (scalar deleting destructor). Everything after the destructor moves up by one.
2. **Overloads.** MSVC puts all the overloads of a name that a class declares together, at the
   position of the first one, in reverse declaration order. So `CommitSuicide(bool, bool)` and
   `CommitSuicide(const Vector&, bool, bool)` swap places, and slots after the destructor don't
   always shift by exactly one.

The script walks the class chain (from the Linux RTTI: each `_ZTI` typeinfo names its base),
splits the vtable into the part each class adds, applies both rules, and maps every Linux index to
a Windows index.

**Verification.** MSVC keeps RTTI in `server.dll`: each class has a type descriptor named like
`.?AVCHL2MP_Player@@`, referenced by a "complete object locator", which is pointed to by the
word just before the class's vtable. `tools/win_vtable.py` follows that chain to read the real
Windows vtables. For every class used (`CHL2MP_Player`, `CBaseCombatWeapon`, `CHL2MPRules`,
`CBaseFilter`, ...), the computed length equals the real one: 477, 363, 184, 181 slots.

Disputed slots were settled by reading the code (`tools/side.py` disassembles a Linux function
and Windows candidates side by side):
- `Think`: Linux calls the entity's second stored function pointer; Windows slot 46 does too
  (slot 45, the fingerprint's guess, calls the first: `MoveDone`). On Linux a member function
  pointer is 8 bytes, on MSVC 4, so the field offsets differ but the order doesn't.
- `PlayerRunCommand` / `ProcessUsercmds`: Windows 377 has the same "if dead, clear IN_..."
  check as Linux `PlayerRunCommand`; 376 walks the commands `0x54` bytes apart, which is also how
  we know ZPS 2.4's `CUserCmd` is 84 bytes on Windows too (NavBot's `CUserCmdSize`).

### Signatures

| Gamedata | How it was found |
|---|---|
| `LevelShutdown` (gives `gEntList`) | SourceMod's own ep2 signature matches twice in 2.4's DLL; both load the same global into `ecx`. Extended until it matches one place (`tools/makesig.py`). Offset 11 is the `mov ecx, offset gEntList`. SourceMod only uses this for the mods its `engine.ep2.txt` lists, so ZPS needs it in `core.games/custom/zps24.txt`. |
| `FireOutput` | Obsidian Conflict's signature matches exactly once; the function prints `(%0.2f) output: (%s,%s) -> ...`, which is `CBaseEntityOutput::FireOutput`. |
| `LookupAttachment` | The function called right after code pushes attachment names (`"eyes"`, `"anim_attachment_RH"`...), 12 call sites. Same body as Linux: get the model, `Studio_FindAttachment()`, `+ 1`. |
| `CanAttachBarricade` | Not in the Windows DLL. Nothing in the game calls it (on Linux it only exists because every symbol is exported), so MSVC's linker dropped it. The survivor plugin treats it as optional and barricades with furniture. |

`tools/sigscan.py` checks any signature against the DLL.

## 3. Testing under Wine

`scripts/wine-server.sh start|stop|cmd|log` runs the Windows dedicated server with Wine on a
Linux PC (port 27025, so it can run next to the Linux server). With the gamedata above:
Metamod, SourceMod and NavBot load, the nav mesh loads, 23 bots join, move, fight, and the
survivor and zombie AI run, including the lessons learned on Linux (same data files).
