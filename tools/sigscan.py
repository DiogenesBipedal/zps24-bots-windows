#!/usr/bin/env python3
"""sigscan.py server.dll SIG   (SourceMod style: \\xE8\\x2A... with 2A = wildcard) -> matches"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_vtable as wv

def parse(sig):
    return [None if b == 0x2A else b for b in bytes(int(x, 16) for x in re.findall(r'\\x([0-9A-Fa-f]{2})', sig))]

def scan(pe, pat):
    a, sz = pe.sec('.text')
    data = pe.read(a, sz)
    first = next(i for i, b in enumerate(pat) if b is not None)
    out = []
    start = 0
    while True:
        i = data.find(bytes([pat[first]]), start)
        if i < 0: break
        start = i + 1
        s = i - first
        if s < 0 or s + len(pat) > len(data): continue
        if all(p is None or data[s + k] == p for k, p in enumerate(pat)):
            out.append(a + s)
    return out

if __name__ == '__main__':
    pe = wv.PE(sys.argv[1])
    m = scan(pe, parse(sys.argv[2]))
    print(len(m), 'match(es):', ' '.join(hex(x) for x in m[:10]))
