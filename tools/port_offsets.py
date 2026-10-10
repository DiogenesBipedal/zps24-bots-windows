#!/usr/bin/env python3
"""Port every vtable offset in the core repo's gamedata to Windows.

port_offsets.py server.dll server_i486.so [--write]

For each "linux" offset, the Windows index is found by matching the Linux function at that
index against the Windows vtable of a class that has it (fingerprints, see win_vtable.py).
Prints a table; with --write, writes gamedata files with both "linux" and "windows" values
into gamedata/.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_vtable as wv

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(HERE, '..', 'core', 'gamedata')
OUT = os.path.join(HERE, '..', 'gamedata')

# Which class's vtable to match each offset in (single inheritance: derived vtables start with
# the base slots, so the player class covers CBaseEntity/CBaseAnimating/CBaseCombatCharacter).
CLASS = {
    'Reload': 'CBaseCombatWeapon',
    'CGameRules::ShouldCollide': 'CHL2MPRules',
    'CBaseFilter::PassesFilterImpl': 'CBaseFilter',
}
DEFAULT = 'CHL2MP_Player'
SKIP = {'EntInfo'}            # not a vtable index (CGlobalEntityList struct offset)


def offsets(path):
    text = open(path).read()
    # "Name" { "linux" "N" }
    return text, [(m.group(1), int(m.group(2))) for m in re.finditer(r'"([^"]+)"\s*\{\s*"linux"\s*"(\d+)"\s*\}', text)]


def main():
    dll, so = sys.argv[1], sys.argv[2]
    write = '--write' in sys.argv
    pe, elf = wv.PE(dll), wv.ELF(so)
    cache = {}
    results = {}
    for fn in sorted(os.listdir(CORE)):
        text, offs = offsets(os.path.join(CORE, fn))
        for name, li in offs:
            if name in SKIP:
                continue
            cls = CLASS.get(name, DEFAULT)
            if cls not in cache:
                cache[cls] = (pe.vtable(cls), elf.vtable(cls))
            wvt, lvt = cache[cls]
            sym = lvt[li]
            dem = wv.demangle([sym])[0]
            try:
                lf = wv.lin_fp(elf, sym)
            except KeyError:
                lf = set()
            cands = sorted(((wv.score(lf, wv.win_fp(pe, wvt[w])), w) for w in range(max(0, li - 4), min(len(wvt), li + 3))), reverse=True)
            best, second = cands[0], cands[1]
            sure = best[0] >= 0.3 and best[0] - second[0] >= 0.08
            results[(fn, name)] = (li, best[1], sure)
            print(f'{fn:40s} {name:32s} linux {li:3d} -> windows {best[1]:3d} ({best[0]:.2f}, next {second[0]:.2f}@{second[1]}) {"" if sure else "CHECK"}  {dem}')
    if write:
        os.makedirs(OUT, exist_ok=True)
        for fn in sorted(os.listdir(CORE)):
            text = open(os.path.join(CORE, fn)).read()
            def add(m):
                key = (fn, m.group(1))
                if key not in results:
                    return m.group(0)
                return m.group(0).replace(f'"linux"\t\t"{m.group(2)}"', f'"linux"\t\t"{m.group(2)}"\n\t\t\t\t"windows"\t"{results[key][1]}"')
            text = re.sub(r'"([^"]+)"\s*\{\s*"linux"\s*"(\d+)"\s*\}', add, text)
            open(os.path.join(OUT, fn), 'w').write(text)


if __name__ == '__main__':
    main()
