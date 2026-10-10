# Progress

- [x] CI: patched Metamod:Source and NavBot built for Windows (x86, orangebox, MSVC)
- [x] Windows ZPS 2.4 dedicated server running (tested under Wine 11 on Linux)
- [x] Gamedata: vtable offsets (45), computed from the Linux vtables with MSVC layout rules;
      vtable lengths match the DLL's RTTI for every class; disputed slots checked in the code
- [x] Gamedata: signatures (LevelShutdown for gEntList, FireOutput, LookupAttachment);
      CanAttachBarricade doesn't exist on Windows (optional in the plugin)
- [x] NavBot loads, 23 bots join, move, fight; survivor and zombie AI run, lessons load
- [x] Release package built by CI; clean install from it works
- [x] Soak test: 20 minutes, two maps, a map change, no crashes or plugin errors
- [ ] Tested on a real Windows PC (install.ps1 has only been syntax-checked and replayed in bash)
