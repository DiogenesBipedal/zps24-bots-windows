#!/usr/bin/env python3
"""Compute MSVC (Windows) vtable indices from an Itanium (Linux) vtable.

Both compilers lay out virtual functions in declaration order, class by class down the
inheritance chain. Two differences:
  1. Itanium has two destructor entries (complete + deleting); MSVC has one.
  2. MSVC groups the overloads of a name declared in a class together, at the first one's
     position, in reverse declaration order.

msvc_layout.py server.so CLASS [IDX...]   linux index -> windows index for CLASS's vtable
"""
import os, struct, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'tools'))
import vtable as lv


def demangle(names):
    p = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True)
    return p.stdout.splitlines()


def parent(b, cls):
    """Primary base class of cls from its Itanium typeinfo (__si_class_type_info / __vmi)."""
    ti = f'_ZTI{len(cls)}{cls}'
    if ti not in b.syms:
        return None
    addr, _ = b.syms[ti]
    vptr = b.rel.get(addr, '')
    if 'si_class_type_info' in vptr:
        base = b.rel.get(addr + 8)
    elif 'vmi_class_type_info' in vptr:
        base = b.rel.get(addr + 16)          # first base of a multiple-inheritance class
    else:
        return None
    if not base or not base.startswith('_ZTI'):
        return None
    # _ZTI<len><name>
    s = base[4:]
    n = ''
    while s and s[0].isdigit():
        n += s[0]; s = s[1:]
    return s[:int(n)] if n else None


def chain(b, cls):
    out = [cls]
    while True:
        p = parent(b, out[-1])
        if not p:
            break
        out.append(p)
    return list(reversed(out))


def method_name(dem):
    """'Class::Name(args) const' -> 'Name'"""
    head = dem.split('(')[0]
    return head.rsplit('::', 1)[-1]


def layout(b, cls):
    """[(linux_index, windows_index or None for the removed dtor, demangled)]"""
    vt = b.vtable(cls)
    dem = demangle(vt)
    # Segment boundaries: vtable length of each ancestor that has one.
    bounds = []
    for c in chain(b, cls):
        try:
            n = len(b.vtable(c))
        except KeyError:
            continue
        if not bounds or n > bounds[-1]:
            bounds.append(n)
    if not bounds or bounds[-1] != len(vt):
        bounds.append(len(vt))
    order = []          # linux indices in windows order
    start = 0
    for end in bounds:
        seg = list(range(start, end))
        # Group overloads (same method name) declared in this segment: first one's position,
        # reverse order. Destructors: keep one.
        placed = set()
        for i in seg:
            if i in placed:
                continue
            name = method_name(dem[i])
            if name.startswith('~'):
                group = [j for j in seg if method_name(dem[j]).startswith('~')]
                order.append(group[0])
                placed.update(group)
                continue
            group = [j for j in seg if j not in placed and method_name(dem[j]) == name and not name.startswith('<')]
            if len(group) > 1:
                order.extend(reversed(group))
            else:
                order.append(i)
            placed.update(group)
        start = end
    win = {li: wi for wi, li in enumerate(order)}
    return [(i, win.get(i), dem[i]) for i in range(len(vt))]


if __name__ == '__main__':
    b = lv.Binary(sys.argv[1])
    cls = sys.argv[2]
    print('chain:', ' -> '.join(chain(b, cls)))
    lay = layout(b, cls)
    idxs = [int(x) for x in sys.argv[3:]] or range(len(lay))
    for i in idxs:
        li, wi, d = lay[i]
        print(f'{li:4d} -> {wi if wi is not None else "-":>4}  {d}')
