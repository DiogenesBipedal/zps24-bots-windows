#!/usr/bin/env python3
"""Find vtable offsets and signatures for the Windows (MSVC, stripped) ZPS 2.4 server.dll, using
the unstripped Linux server_i486.so as the reference.

  win_vtable.py vtable  server.dll CLASS                  windows vtable of CLASS (via RTTI)
  win_vtable.py match   server.dll server.so CLASS IDX... for each Linux index of CLASS, the best
                                                          matching Windows index (by fingerprint)
  win_vtable.py func    server.dll server.so SYMBOL       find the Windows function matching a Linux
                                                          symbol (vtables first, then string refs)

A function's fingerprint: the member offsets ([reg+disp]), immediates and strings it uses, plus
how many calls it makes. Struct layouts and constants are the same on both platforms, so the
right Windows function shares most of them with its Linux twin.
"""
import struct, subprocess, sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core', 'tools'))

CS = Cs(CS_ARCH_X86, CS_MODE_32)
CS.detail = True


class PE:
    def __init__(self, path):
        self.pe = pefile.PE(path, fast_load=True)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.data = self.pe.get_memory_mapped_image()
        self.secs = [(s.Name.rstrip(b'\0').decode(), self.base + s.VirtualAddress, s.Misc_VirtualSize) for s in self.pe.sections]

    def sec(self, name):
        for n, a, sz in self.secs:
            if n == name:
                return a, sz
        raise KeyError(name)

    def in_sec(self, va, name):
        a, sz = self.sec(name)
        return a <= va < a + sz

    def read(self, va, n):
        o = va - self.base
        return self.data[o:o + n]

    def u32(self, va):
        return struct.unpack('<I', self.read(va, 4))[0]

    def cstr(self, va, maxlen=200):
        b = self.read(va, maxlen)
        end = b.find(b'\0')
        s = b[:end if end >= 0 else maxlen]
        if len(s) >= 3 and all(32 <= c < 127 or c in (9, 10) for c in s):
            return s.decode()
        return None

    # --- RTTI ---------------------------------------------------------------------------------
    def type_descriptor(self, cls):
        name = f'.?AV{cls}@@'.encode() + b'\0'
        i = self.data.find(name)
        if i < 0:
            return None
        return self.base + i - 8          # TypeDescriptor: pVFTable, spare, name

    def vtable_addr(self, cls):
        td = self.type_descriptor(cls)
        if td is None:
            raise KeyError(f'no RTTI for {cls}')
        tdb = struct.pack('<I', td)
        # Complete Object Locator: signature(0), offset, cdOffset, pTypeDescriptor, pClassDescriptor
        best = None
        start = 0
        while True:
            i = self.data.find(tdb, start)
            if i < 0:
                break
            start = i + 1
            col = self.base + i - 12
            sig, off, cdoff = struct.unpack('<III', self.read(col, 12))
            if sig != 0 or off != 0:
                continue                   # only the primary vtable (offset 0)
            # The vtable is the dword after a pointer to this COL.
            colb = struct.pack('<I', col)
            j = self.data.find(colb)
            while j >= 0:
                va = self.base + j
                if self.in_sec(va, '.rdata'):
                    best = va + 4
                    break
                j = self.data.find(colb, j + 1)
            if best:
                break
        if best is None:
            raise KeyError(f'no vtable for {cls}')
        return best

    def is_code(self, va):
        a, sz = self.sec('.text')
        return a <= va < a + sz

    def vtable(self, cls):
        va = self.vtable_addr(cls)
        out = []
        while True:
            f = self.u32(va + 4 * len(out))
            if not self.is_code(f):
                break
            out.append(f)
        return out


class ELF:
    def __init__(self, path):
        import vtable as lv           # the Linux tool from the core repo
        self.b = lv.Binary(path)
        self.lv = lv

    def vtable(self, cls):
        return self.b.vtable(cls)

    def addr(self, sym):
        return self.b.syms[sym]


def disasm(code, va, limit=4000):
    """Instructions of a function, up to the first ret/jmp-out at the end of straight-line code."""
    out = []
    for ins in CS.disasm(code[:limit], va):
        out.append(ins)
        if ins.mnemonic in ('ret', 'retn') or ins.mnemonic == 'int3':
            # Keep going only if a jump earlier targets past this point.
            far = max([int(i.op_str, 16) for i in out if i.mnemonic.startswith('j') and i.op_str.startswith('0x')] or [0])
            if far <= ins.address:
                break
    return out


def fingerprint(insns, strfn):
    feats = set()
    calls = 0
    for ins in insns:
        if ins.mnemonic == 'call':
            calls += 1
        for op in ins.operands:
            if op.type == X86_OP_MEM and op.mem.base != 0 and op.mem.disp and abs(op.mem.disp) < 0x10000:
                feats.add(('d', op.mem.disp))
            elif op.type == X86_OP_IMM:
                v = op.imm & 0xffffffff
                s = strfn(v)
                if s:
                    feats.add(('s', s))
                elif 4 < v < 0x100000 and ins.mnemonic not in ('call', 'jmp') and not ins.mnemonic.startswith('j'):
                    feats.add(('i', v))
            elif op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.disp:
                s = strfn(op.mem.disp & 0xffffffff)
                if s:
                    feats.add(('s', s))
    feats.add(('calls', min(calls, 20)))
    feats.add(('len', min(len(insns) // 5, 40)))
    return feats


def win_fp(pe, va):
    return fingerprint(disasm(pe.read(va, 4000), va), lambda v: pe.cstr(v) if pe.base <= v < pe.base + len(pe.data) else None)


def lin_fp(elf, sym):
    addr, size = elf.addr(sym)
    code = elf.b.read(addr, max(size, 16))
    def strfn(v):
        try:
            b = elf.b.read(v, 200)
        except Exception:
            return None
        end = b.find(b'\0')
        s = b[:end if end >= 0 else 200]
        if len(s) >= 3 and all(32 <= c < 127 for c in s):
            return s.decode()
        return None
    return fingerprint(list(CS.disasm(code, addr)), strfn)


def score(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def demangle(names):
    p = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True)
    return p.stdout.splitlines()


def cmd_match(dll, so, cls, idxs):
    pe, elf = PE(dll), ELF(so)
    wv = pe.vtable(cls)
    lvt = elf.vtable(cls)
    print(f'{cls}: linux {len(lvt)} slots, windows {len(wv)} slots')
    for i in idxs:
        sym = lvt[i]
        name = demangle([sym])[0]
        try:
            lf = lin_fp(elf, sym)
        except KeyError:
            print(f'  linux {i} {name}: no symbol body'); continue
        cands = []
        for w in range(max(0, i - 4), min(len(wv), i + 3)):
            cands.append((score(lf, win_fp(pe, wv[w])), w))
        cands.sort(reverse=True)
        best = cands[0]
        second = cands[1] if len(cands) > 1 else (0, -1)
        flag = '' if best[0] - second[0] > 0.1 else '   <-- check'
        print(f'  linux {i:3d} -> windows {best[1]:3d}  ({best[0]:.2f} vs {second[0]:.2f} at {second[1]})  {name}{flag}')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'vtable':
        pe = PE(sys.argv[2])
        for i, f in enumerate(pe.vtable(sys.argv[3])):
            print(i, hex(f))
    elif cmd == 'match':
        cmd_match(sys.argv[2], sys.argv[3], sys.argv[4], [int(x) for x in sys.argv[5:]])
