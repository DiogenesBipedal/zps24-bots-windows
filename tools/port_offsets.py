#!/usr/bin/env python3
"""Port every vtable offset in the core repo's gamedata to Windows.

port_offsets.py server.dll server_i486.so [--write]

For each "linux" offset, the Windows index is computed from the Linux vtable with MSVC's layout
rules (msvc_layout.py), checked against the real Windows vtable's length, and given a second
opinion by comparing the two functions' fingerprints (win_vtable.py). Prints a table; with
--write, writes gamedata files with both "linux" and "windows" values into gamedata/.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_vtable as wv
import msvc_layout as ml

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
                lay = ml.layout(elf.b, cls)
                wvt = pe.vtable(cls)
                n = sum(1 for l in lay if l[1] is not None)
                if n != len(wvt):
                    sys.exit(f'{cls}: computed {n} slots, windows has {len(wvt)}: layout rules wrong for this class')
                cache[cls] = (lay, wvt, elf.vtable(cls))
            lay, wvt, lvt = cache[cls]
            wi = lay[li][1]
            dem = lay[li][2]
            try:
                lf = wv.lin_fp(elf, lvt[li])
            except KeyError:
                lf = set()
            here = wv.score(lf, wv.win_fp(pe, wvt[wi]))
            near = max((wv.score(lf, wv.win_fp(pe, wvt[w])), w) for w in range(max(0, wi - 3), min(len(wvt), wi + 4)) if w != wi)
            note = '' if here >= near[0] - 0.02 else f'  (fingerprint prefers {near[1]}: {near[0]:.2f} vs {here:.2f})'
            results[(fn, name)] = (li, wi, True)
            print(f'{fn:40s} {name:32s} linux {li:3d} -> windows {wi:3d}{note}  {dem}')
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
