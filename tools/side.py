#!/usr/bin/env python3
"""side.py server.dll server.so CLASS LINUX_IDX WIN_IDX...: disassemble a Linux slot and Windows slots"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import win_vtable as wv
pe, elf = wv.PE(sys.argv[1]), wv.ELF(sys.argv[2])
cls = sys.argv[3]; li = int(sys.argv[4])
lvt = elf.vtable(cls); wvt = pe.vtable(cls)
sym = lvt[li]; addr, size = elf.addr(sym)
print('LINUX', li, wv.demangle([sym])[0])
for ins in list(wv.CS.disasm(elf.b.read(addr, min(size, 300)), addr))[:25]:
    print('   ', ins.mnemonic, ins.op_str)
for w in sys.argv[5:]:
    w = int(w); va = wvt[w]
    print('WINDOWS', w, hex(va))
    for ins in wv.disasm(pe.read(va, 400), va)[:25]:
        print('   ', ins.mnemonic, ins.op_str)
