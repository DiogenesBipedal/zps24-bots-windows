#!/usr/bin/env python3
"""makesig.py server.dll ADDR: shortest unique SourceMod signature for the function at ADDR.
Relative branch targets and absolute addresses are wildcarded (\\x2A), the rest kept."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_vtable as wv, sigscan as ss
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

def make(pe, va, maxlen=96):
    code = pe.read(va, maxlen + 16)
    pat = []
    for ins in wv.CS.disasm(code, va):
        b = list(ins.bytes)
        n = len(b)
        wild = set()
        rel = ins.mnemonic == 'call' or ins.mnemonic.startswith('j')
        if rel and n >= 5:
            wild.update(range(n - 4, n))               # rel32 target
        imm_off, disp_off = ins.imm_offset, ins.disp_offset
        for op in ins.operands:
            if op.type == X86_OP_IMM and imm_off and pe.base <= (op.imm & 0xffffffff) < pe.base + len(pe.data):
                wild.update(range(imm_off, min(n, imm_off + 4)))
            if op.type == X86_OP_MEM and disp_off and pe.base <= (op.mem.disp & 0xffffffff) < pe.base + len(pe.data):
                wild.update(range(disp_off, min(n, disp_off + 4)))
        pat += [None if i in wild else b[i] for i in range(n)]
        if len(pat) >= 6:
            hits = ss.scan(pe, pat)
            if hits == [va]:
                return ''.join('\\x2A' if p is None else f'\\x{p:02X}' for p in pat)
        if len(pat) > maxlen:
            break
    return None

if __name__ == '__main__':
    pe = wv.PE(sys.argv[1])
    for a in sys.argv[2:]:
        print(a, make(pe, int(a, 16)))
