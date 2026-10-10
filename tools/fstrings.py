#!/usr/bin/env python3
"""fstrings.py server.dll ADDR: strings, calls and size of the function at ADDR"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_vtable as wv
from capstone.x86 import X86_OP_IMM, X86_OP_MEM
pe = wv.PE(sys.argv[1]); va = int(sys.argv[2], 16)
ins = wv.disasm(pe.read(va, 6000), va, 6000)
strs = []
for i in ins:
    for op in i.operands:
        v = op.imm & 0xffffffff if op.type == X86_OP_IMM else (op.mem.disp & 0xffffffff if op.type == X86_OP_MEM and op.mem.base == 0 else None)
        if v and pe.base <= v < pe.base + len(pe.data):
            s = pe.cstr(v)
            if s: strs.append(s)
print(f'{len(ins)} instructions, {sum(1 for i in ins if i.mnemonic == "call")} calls')
for s in strs: print('  str:', repr(s[:90]))
