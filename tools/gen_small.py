"""Sources for the client's small straight-line functions, lifted from the client's own code: the function is run
symbolically (registers and stack slots hold expressions over its arguments, `this` and globals), every store, call
and the returned value becomes a C++ statement, and the file is compiled with Riot's compiler; gen_sources.py keeps
only the functions that come out identical (`// match:` lines, verified like every other source).

What a function is called and what its types are is not known: it is named after its rva. A member function of
`struct K<rva>` when it uses ecx as it comes in (thiscall), else a free function `k<rva>`; its arguments are 32-bit
integers a0, a1, ...; addresses are integers too (`*(int*)(a0 + 4)`). The client's globals are `g_<virtual address>`,
the functions it calls `T<rva>::f` / `t<rva>` (or the K / k name when that function is lifted too), virtual calls go
through `I<slot>_<arguments>` interfaces. Only functions without branches are lifted; what the lifter does not model
(stack locals, floating point, fastcall, named library targets) is left out.

  gen_small.py <first rva hex> <end rva hex>        print the lifted source of that range (for trying forms out)
"""
import bisect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402
import packet_emu as P  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402
from capstone import x86 as X  # noqa: E402

NL = chr(10)
TEXT1 = 0x1000 + 0xfa96ec
RIOT = (0x60000, 0xbc0000)           # Riot's own code; libraries and the runtime come after it
ALLOCATION_RVAS = {0x9bb8d0, 0x9bb8e0, 0x9bb8f0, 0x9bb930, 0x9bb940, 0x9bb950}
# Calls lifted here have these exact source ABIs. Aligned/nothrow wrappers are
# generated separately; unknown calls to their overloads remain conservative.
ALLOCATION_CALLS = {0x9bb8d0: ('new', 1, False), 0x9bb930: ('delete', 1, True),
                    0x9bb940: ('delete', 2, True)}
# Measured native member ABIs supplied by a shared, independently verified type.
# A destructor returns no value: EAX left behind by it is not a source result.
NATIVE_CALLS = {0xae14d0: ('UiResourceReference', '~UiResourceReference', 0, 'UiResourceRefs.h'),
                0x5894b0: ('UiHashLinkTriple', 'UiHashLinkTriple', 0, 'UiResourceRefs.h'),
                0x58ac50: ('HeroFloatingInfoIconsData', '~HeroFloatingInfoIconsData', 0, 'BinClasses.h'),
                0x2338b0: ('FontType', '~FontType', 0, 'BinClasses.h'),
                0xa21cf0: ('ILogicBoolDriver', 'ILogicBoolDriver', 0, 'BinClasses.h'),
                0x9b78e0: ('MetaString', 'MetaString', 4, '../Meta.h'),
                0x9b7840: ('MetaString', 'MetaString', 4, '../Meta.h')}
NATIVE_PARAMETERS = {0x9b78e0: ('const char*',),0x9b7840:('const MetaString&',)}
NATIVE_OWNERS = {0x31e950: '??_GUiResourceReference@@',
                 0x2d0d00: '??$MetaVirtual2@USummonerIconData@@@@',
                 **{rva: '??$MetaDestruct@' for rva in
                    (0x576830, 0x576390, 0x5766e0, 0x576510, 0x5b7660)}}
import gen_vfx_runtime
import gen_meta_placements
import gen_ui_elements
import gen_poly_placements
NATIVE_CALLS.update({rva:(name,name,0,'BinClasses.h') for name,rva in gen_ui_elements.CONSTRUCTORS.items()})
NATIVE_OWNERS.update({rva:f'??$MetaConstruct@U{name}@@@@' for name,(rva,_,_) in gen_ui_elements.PLACEMENTS.items()})
NATIVE_OWNERS.update({rva:f'??${fn}@U{name}@@@@' for name,rvas in gen_vfx_runtime.CALLBACKS.items()
                     for (_,fn,_),rva in zip(gen_vfx_runtime.ORDER,rvas)})
NATIVE_OWNERS.update({rva:f'??$MetaConstruct@U{name}@@@@' for name,rva in gen_meta_placements.RVA.items()})
NATIVE_OWNERS.update(gen_poly_placements.owners())
# UI atlas texture providers (client-src/src/UiAtlas*.cpp): constructors and placement callbacks.
NATIVE_OWNERS.update({rva:f'??0{name}@ui_native@@' for name,rva in
                      (('AtlasData3SliceH',0xaded90),('AtlasData3SliceV',0xadee10),
                       ('AtlasData9Slice',0xadee90),('AtlasData',0xadef20))})
NATIVE_OWNERS.update({rva:f'??$MetaConstruct@U{name}@@@@' for name,rva in
                      (('AtlasData',0xadb910),('AtlasData3SliceH',0xadb990),
                       ('AtlasData3SliceV',0xadb9c0),('AtlasData9Slice',0xadba40))})


def call_returns_void(kind):
    if kind[0]=='direct' and kind[1] in NATIVE_CALLS:
        typ,member,_,_=NATIVE_CALLS[kind[1]]
        # A placement-new expression yields the constructed object's pointer.
        # This is the native constructor's EAX value, unlike a destructor.
        if typ==member:return False
    return kind[0] == 'direct' and (kind[1] in NATIVE_CALLS or
        kind[1] in ALLOCATION_CALLS and ALLOCATION_CALLS[kind[1]][2])
FAMILY = {}
for full, parts in (('eax', ('eax', 'ax', 'al', 'ah')), ('ecx', ('ecx', 'cx', 'cl', 'ch')),
                    ('edx', ('edx', 'dx', 'dl', 'dh')), ('ebx', ('ebx', 'bx', 'bl', 'bh')),
                    ('esi', ('esi', 'si')), ('edi', ('edi', 'di')), ('ebp', ('ebp', 'bp')), ('esp', ('esp', 'sp'))):
    for p in parts:
        FAMILY[p] = full
SAVED = ('ebx', 'esi', 'edi', 'ebp')


class Unsupported(Exception):
    pass


# ---------------------------------------------------------------------------------------------------- expressions
# An expression is a tuple: ('arg', i) | ('this',) | ('const', v) | ('addr', va) | ('load', id) | ('call', id)
# | ('bin', op, a, b) | ('un', op, a) | ('cmp', op, a, b) | ('ext', signed, bits, a) | ('trunc', bits, a)
# | ('saved', reg) | ('in', reg) | ('unk',).   Loads and call results are numbered values (Let statements).

def const(v):
    return ('const', v & 0xffffffff)


def is_const(e, v=None):
    return e[0] == 'const' and (v is None or e[1] == v & 0xffffffff)


def add(a, b):
    if is_const(b, 0):
        return a
    if is_const(a) and is_const(b):
        return const(a[1] + b[1])
    if a[0] == 'bin' and a[1] == '+' and is_const(a[3]) and is_const(b):
        return add(a[2], const(a[3][1] + b[1]))
    if is_const(a) and not is_const(b):
        return add(b, a)
    return ('bin', '+', a, b)


def usable(e):
    """An expression the source can name (not a register's unknown or saved value)."""
    if e[0] in ('unk', 'saved', 'in'):
        return False
    return all(usable(x) for x in e[1:] if isinstance(x, tuple))


class Image:
    def __init__(self):
        self.md = Cs(CS_ARCH_X86, CS_MODE_32)
        self.md.detail = True
        self.img = bytes(P.IMG)
        self.starts = sorted(M.starts())
        self.named = M.known_names()
        self.rebuilt = M.rebuilt_symbols()
        self._conv = {}

    def size(self, rva):
        k = bisect.bisect_right(self.starts, rva)
        e = self.starts[k] if k < len(self.starts) else TEXT1
        while e > rva and self.img[e - 1] == 0xcc:
            e -= 1
        return e - rva

    def code(self, rva, n=None):
        n = self.size(rva) if n is None else n
        out = list(self.md.disasm(self.img[rva:rva + n], rva))
        if not out or out[-1].address + out[-1].size != rva + n:
            return None
        return out

    def convention(self, rva):
        """(uses ecx as it comes in, bytes of stack arguments it pops) of a function the client calls, from its own
        code: ecx read before it is written on the way to the first return, and that return's operand. None when
        that cannot be seen (unknown address, edx used as an argument)."""
        if rva in self._conv:
            return self._conv[rva]
        out = None
        if rva in set(self.starts) or True:
            out = self._scan(rva)
        self._conv[rva] = out
        return out

    def _scan(self, rva):
        written = set()
        this = False
        pos, budget = rva, 400
        while budget > 0 and 0x1000 <= pos < TEXT1:
            ins = next(self.md.disasm(self.img[pos:pos + 16], pos), None)
            if ins is None:
                return None
            budget -= 1
            regs_read, regs_write = ins.regs_access()
            read = {FAMILY.get(ins.reg_name(r), '') for r in regs_read}
            write = {FAMILY.get(ins.reg_name(r), '') for r in regs_write}
            if ins.mnemonic == 'xor' and len(ins.operands) == 2 and ins.operands[0].type == X.X86_OP_REG \
                    and ins.operands[1].type == X.X86_OP_REG and ins.operands[0].reg == ins.operands[1].reg:
                read = set()
            if 'ecx' in read and 'ecx' not in written:
                this = True
            if 'edx' in read and 'edx' not in written and ins.mnemonic not in ('push',):
                return None
            if ins.mnemonic == 'call':
                written |= {'eax', 'ecx', 'edx'}
            written |= write
            if ins.mnemonic == 'ret':
                n = ins.operands[0].imm if ins.operands else 0
                return this, n
            if ins.mnemonic == 'jmp':
                if ins.operands[0].type == X.X86_OP_IMM:
                    pos = ins.operands[0].imm
                    continue
                return None
            if ins.mnemonic.startswith('j'):
                # follow the fall-through; a function's returns all pop the same amount
                pass
            pos += ins.size
        return None


# --------------------------------------------------------------------------------------------- symbolic execution

class Lifted:
    def __init__(self, rva):
        self.rva = rva
        self.stmts = []         # ('let', id, expr) ('store', addr, bits, value) ('call', id, callee, this, args)
        self.lets = {}          # id -> expr
        self.this = False
        self.args = 0           # stack arguments read
        self.pops = 0           # bytes popped by its return
        self.ret = None         # (expr, bits) or None
        self.tail = None        # statement index of a tail call
        self.callees = set()


class Lifter:
    def __init__(self, im, rva):
        self.im = im
        self.f = Lifted(rva)
        self.regs = {r: ('saved', r) if r in SAVED else ('in', r) for r in ('eax', 'ecx', 'edx', 'ebx', 'esi', 'edi', 'ebp')}
        self.low = {}           # register -> (bits, expr) when only its low part holds a value
        self.sp = 0
        self.slots = {}         # entry-relative stack offset (< 0) -> expr pushed there
        self.pending = []       # (offset, expr) pushed as arguments of a coming call
        self.flags = None
        self.next_id = 0

    # values
    def new(self, expr):
        k = self.next_id
        self.next_id += 1
        self.f.lets[k] = expr
        self.f.stmts.append(('let', k, expr))
        return ('load', k) if expr[0] == 'mem' else ('call', k)

    def mem_addr(self, op):
        m = op.mem
        if m.segment:
            raise Unsupported('segment')
        base = self.im.md.reg_name(m.base) if m.base else None
        index = self.im.md.reg_name(m.index) if m.index else None
        if base == 'esp' or index == 'esp':
            if index:
                raise Unsupported('indexed stack')
            return ('stack', self.sp + m.disp)
        e = const(m.disp)
        if base:
            e = add(self.get(base), const(m.disp))
        if index:
            i = self.get(index)
            if m.scale != 1:
                i = ('bin', '*', i, const(m.scale))
            e = add(e, i) if not is_const(e, 0) else i
        if not base and not index:
            return self.global_addr(m.disp)
        if base and not index and self.image_address(m.disp) and not usable(self.get(base)):
            raise Unsupported('table')
        return e

    def image_address(self, v):
        v &= 0xffffffff
        return P.BASE <= v < P.BASE + len(self.im.img)

    def global_addr(self, v):
        v &= 0xffffffff
        if not self.image_address(v):
            raise Unsupported('absolute address outside the image')
        if self.im.named.get(v - P.BASE):
            raise Unsupported('named global')
        if 0x1000 <= v - P.BASE < TEXT1:
            raise Unsupported('address of code')
        return ('addr', v)

    def read(self, op, bits=None):
        bits = bits or op.size * 8
        if op.type == X.X86_OP_REG:
            name = self.im.md.reg_name(op.reg)
            return self.get(name, bits)
        if op.type == X.X86_OP_IMM:
            v = op.imm & 0xffffffff
            if self.image_address(v):
                return self.global_addr(v)
            return const(v)
        a = self.mem_addr(op)
        if a[0] == 'stack':
            return self.stack(a[1], op.size)
        return self.new(('mem', a, op.size * 8, False))

    def stack(self, off, size):
        if size != 4:
            raise Unsupported('stack access size')
        if off >= 4:
            if off % 4:
                raise Unsupported('unaligned argument')
            i = (off - 4) // 4
            self.f.args = max(self.f.args, i + 1)
            return ('arg', i)
        if off in self.slots:
            return self.slots[off]
        raise Unsupported('stack local')

    def get(self, name, bits=32):
        full = FAMILY.get(name)
        if full is None:
            raise Unsupported('register ' + name)
        if full == 'esp':
            raise Unsupported('esp as a value')
        if name in ('ah', 'bh', 'ch', 'dh'):
            raise Unsupported('high byte register')
        if bits == 32:
            if full in self.low:
                b, e = self.low[full]
                rest = self.regs[full]
                if is_const(rest, 0):
                    return ('ext', False, b, e)
                raise Unsupported('mixed register')
            v = self.regs[full]
            if v[0] == 'in' and full == 'ecx':
                self.f.this = True
                return ('this',)
            if v[0] == 'in':
                raise Unsupported('register argument ' + full)
            return v
        if full in self.low and self.low[full][0] >= bits:
            return trunc(self.low[full][1], bits)
        if full in self.low:
            raise Unsupported('partial register read')
        return trunc(self.get(full), bits)

    def set(self, name, value):
        full = FAMILY[name]
        bits = {'e': 32}.get(name[0], 16 if len(name) == 2 and name[1] in 'xip' else 8)
        if name in ('si', 'di', 'bp', 'sp'):
            bits = 16
        if full == 'esp':
            raise Unsupported('esp written')
        if bits == 32:
            self.regs[full] = value
            self.low.pop(full, None)
        else:
            if name in ('ah', 'bh', 'ch', 'dh'):
                raise Unsupported('high byte register')
            self.low[full] = (bits, value)

    def store(self, op, value):
        if op.type == X.X86_OP_REG:
            self.set(self.im.md.reg_name(op.reg), value)
            return
        a = self.mem_addr(op)
        if a[0] == 'stack':
            raise Unsupported('stack store')
        self.f.stmts.append(('store', a, op.size * 8, value))

    # one instruction
    def step(self, ins):
        mn, ops = ins.mnemonic, ins.operands
        if mn == 'mov':
            self.store(ops[0], self.read(ops[1]))
        elif mn in ('movzx', 'movsx'):
            self.store(ops[0], ('ext', mn == 'movsx', ops[1].size * 8, self.read(ops[1])))
        elif mn == 'lea':
            a = self.mem_addr(ops[1])
            if a[0] == 'stack':
                raise Unsupported('address of a stack slot')
            self.store(ops[0], a)
        elif mn == 'push':
            if ops[0].type == X.X86_OP_REG and self.im.md.reg_name(ops[0].reg) in SAVED \
                    and self.regs[self.im.md.reg_name(ops[0].reg)][0] == 'saved' and not self.pending:
                v = self.regs[self.im.md.reg_name(ops[0].reg)]
            else:
                v = self.read(ops[0], 32)
            self.sp -= 4
            self.slots[self.sp] = v
            if v[0] != 'saved':
                self.pending.append((self.sp, v))
        elif mn == 'pop':
            v = self.slots.pop(self.sp, None)
            if v is None:
                raise Unsupported('pop of an unknown slot')
            self.pending = [p for p in self.pending if p[0] != self.sp]
            self.sp += 4
            name = self.im.md.reg_name(ops[0].reg)
            if v[0] == 'saved' and v[1] != FAMILY[name]:
                raise Unsupported('saved register moved')
            self.set(name, v)
        elif mn in ('add', 'sub') and ops[0].type == X.X86_OP_REG and self.im.md.reg_name(ops[0].reg) == 'esp':
            if ops[1].type != X.X86_OP_IMM:
                raise Unsupported('esp arithmetic')
            n = ops[1].imm if mn == 'add' else -ops[1].imm
            if n < 0:
                raise Unsupported('stack frame')
            for k in range(n // 4):
                self.slots.pop(self.sp, None)
                self.pending = [p for p in self.pending if p[0] != self.sp]
                self.sp += 4
        elif mn in ('add', 'sub', 'and', 'or', 'xor', 'imul', 'shl', 'shr', 'sar', 'rol', 'ror'):
            if mn == 'imul' and len(ops) != 2:
                if len(ops) == 3:
                    v = ('bin', '*', self.read(ops[1]), self.read(ops[2]))
                    self.store(ops[0], v)
                    self.flags = None
                    return
                raise Unsupported('imul form')
            if mn == 'xor' and ops[0].type == X.X86_OP_REG and ops[1].type == X.X86_OP_REG and ops[0].reg == ops[1].reg:
                name = self.im.md.reg_name(ops[0].reg)
                self.set(name, const(0))
                self.flags = None
                return
            a = self.read(ops[0])
            b = self.read(ops[1])
            op = {'add': '+', 'sub': '-', 'and': '&', 'or': '|', 'xor': '^', 'imul': '*', 'shl': '<<', 'shr': '>>u',
                  'sar': '>>', 'rol': 'rol', 'ror': 'ror'}[mn]
            bits = ops[0].size * 8
            v = add(a, b) if op == '+' else add(a, const(-b[1])) if op == '-' and is_const(b) else ('bin', op, a, b)
            if bits != 32:
                v = trunc(v, bits)
            self.store(ops[0], v)
            self.flags = ('arith', v, bits)
        elif mn in ('inc', 'dec', 'neg', 'not'):
            a = self.read(ops[0])
            bits = ops[0].size * 8
            v = add(a, const(1 if mn == 'inc' else -1)) if mn in ('inc', 'dec') else ('un', '-' if mn == 'neg' else '~', a)
            if bits != 32:
                v = trunc(v, bits)
            self.store(ops[0], v)
            self.flags = ('arith', v, bits)
        elif mn in ('cmp', 'test'):
            self.flags = (mn, self.read(ops[0]), self.read(ops[1]), ops[0].size * 8)
        elif mn.startswith('set'):
            if not self.flags:
                raise Unsupported('setcc without flags')
            self.store(ops[0], ('cmp', mn[3:], self.flags))
        elif mn == 'call':
            self.call(ins, tail=False)
        elif mn == 'jmp':
            self.call(ins, tail=True)
        elif mn == 'ret':
            self.ret(ins)
        elif mn == 'nop':
            pass
        elif mn == 'cdq':
            raise Unsupported('cdq')
        else:
            raise Unsupported('instruction ' + mn)

    def callee(self, ins):
        """('direct', rva, this, pops) or ('virtual', slot, object, None)."""
        op = ins.operands[0]
        if op.type == X.X86_OP_IMM:
            rva = op.imm & 0xffffffff
            if not 0x1000 <= rva < TEXT1:
                raise Unsupported('call outside the code')
            if rva in ALLOCATION_CALLS:
                return ('direct', rva, False, 0)
            if rva in NATIVE_CALLS:
                return ('direct', rva, True, NATIVE_CALLS[rva][2])
            if self.im.named.get(rva) or (rva in self.im.rebuilt and not self.generated(rva)):
                raise Unsupported('named callee')
            conv = self.im.convention(rva)
            if conv is None:
                raise Unsupported('callee convention')
            return ('direct', rva, conv[0], conv[1])
        if op.type == X.X86_OP_MEM:
            m = op.mem
            if m.base and not m.index and not m.segment:
                vt = self.get(self.im.md.reg_name(m.base))
                if vt[0] == 'load':
                    mem = self.f.lets[vt[1]]
                    if mem[1][0] != 'stack' and mem[2] == 32 and m.disp % 4 == 0:
                        return ('virtual', m.disp // 4, mem[1], vt)
            raise Unsupported('indirect call')
        raise Unsupported('call through register')

    def generated(self, rva):
        return any(t.startswith(f'?f@K{rva:x}@@') or t.startswith(f'?k{rva:x}@@') for t in self.im.rebuilt.get(rva, ()))

    def call(self, ins, tail):
        kind = self.callee(ins)
        if kind[0] == 'virtual':
            slot, obj, vt = kind[1], kind[2], kind[3]
            this = self.regs['ecx'] if 'ecx' not in self.low else ('unk',)
            if this[0] == 'in':
                this = self.get('ecx')
            if this != obj:
                raise Unsupported('virtual call on another object')
            # the vtable load itself is part of the call
            uses_this = True
            pops = None
        else:
            rva, uses_this, pops = kind[1], kind[2], kind[3]
            this = self.get('ecx') if uses_this else None
            if uses_this and not usable(this):
                raise Unsupported('this of a call')
            self.f.callees.add(rva)
        if tail:
            if self.sp != 0:
                raise Unsupported('tail call with a frame')
            if kind[0] == 'direct':
                nargs = ALLOCATION_CALLS[kind[1]][1] if kind[1] in ALLOCATION_CALLS else pops // 4
            else:
                nargs = 0
            args = [('arg', i) for i in range(nargs)]
            self.f.args = max(self.f.args, nargs)
            k = self.next_id
            self.next_id += 1
            self.f.stmts.append(('call', k, kind, this, args))
            self.f.tail = len(self.f.stmts) - 1
            self.f.pops = pops if kind[0] == 'direct' else 0
            returns_void = call_returns_void(kind)
            self.f.ret = None if returns_void else (('call', k), 32)
            self.done = True
            return
        # arguments: the latest pushes; the caller removes them after a cdecl call
        nxt = next(self.im.md.disasm(self.im.img[ins.address + ins.size:ins.address + ins.size + 16],
                                     ins.address + ins.size), None)
        cleanup = 0
        if nxt is not None and nxt.mnemonic == 'add' and nxt.op_str.startswith('esp, '):
            cleanup = nxt.operands[1].imm
        elif nxt is not None and nxt.mnemonic == 'pop' and nxt.op_str == 'ecx':
            cleanup = 4
        if kind[0] == 'direct' and kind[1] in NATIVE_CALLS:
            cleanup = 0  # a native thiscall destructor has no caller-popped argument
        if kind[0] == 'direct':
            if cleanup and pops:
                raise Unsupported('callee pops and caller cleans')
            n = (cleanup or pops) // 4
            if kind[1] in ALLOCATION_CALLS and n != ALLOCATION_CALLS[kind[1]][1]:
                raise Unsupported('allocation call argument count')
            conv = 'cdecl' if cleanup or not pops and not uses_this else 'stdcall' if not uses_this else 'thiscall'
        else:
            if cleanup:
                raise Unsupported('virtual cdecl')
            n = len(self.pending)
            conv = 'thiscall'
        if n > len(self.pending):
            raise Unsupported('arguments not pushed')
        args = [v for _, v in reversed(self.pending[len(self.pending) - n:])] if n else []
        if any(not usable(a) for a in args):
            raise Unsupported('argument value')
        if not cleanup and n:
            # the callee pops its arguments
            for k in range(n):
                self.slots.pop(self.sp, None)
                self.sp += 4
            self.pending = self.pending[:len(self.pending) - n]
        k = self.next_id
        self.next_id += 1
        self.f.stmts.append(('call', k, kind if kind[0] == 'virtual' else ('direct', kind[1], uses_this, n * 4, conv),
                             this, args))
        self.f.lets[k] = ('callres',)
        returns_void = call_returns_void(kind)
        self.regs['eax'] = ('unk',) if returns_void else ('call', k)
        self.low.pop('eax', None)
        self.regs['ecx'] = ('unk',)
        self.regs['edx'] = ('unk',)
        self.low.pop('ecx', None)
        self.low.pop('edx', None)
        self.flags = None

    def ret(self, ins):
        if self.sp != 0:
            raise Unsupported('return with a frame')
        for r in SAVED:
            if self.regs[r] != ('saved', r):
                raise Unsupported('saved register not restored')
        self.f.pops = ins.operands[0].imm if ins.operands else 0
        if 'eax' in self.low:
            b, e = self.low['eax']
            self.f.ret = (e, b) if usable(e) else None
            if self.regs['eax'] == const(0) and usable(e):
                self.f.ret = (e, b)
        else:
            e = self.regs['eax']
            self.f.ret = (e, 32) if usable(e) else None
        self.done = True

    def join(self, before, returned):
        """The end of an `if` block: what is known where its two ways meet."""
        regs, low, sp, slots = before
        if returned:
            self.regs, self.low, self.sp, self.slots, self.pending = dict(regs), dict(low), sp, dict(slots), []
        else:
            if self.sp != sp or self.slots != slots or self.pending:
                raise Unsupported('branch')
            for r in list(self.regs):
                if self.regs[r] != regs[r] or self.low.get(r) != low.get(r):
                    self.regs[r] = ('unk',)
                    self.low.pop(r, None)
        self.flags = None
        self.f.stmts.append(('endif',))

    def run(self):
        code = self.im.code(self.f.rva)
        if not code:
            raise Unsupported('undecodable')
        self.done = False
        # A forward conditional jump skips a block: `if (not the condition) { block }`. The block either falls
        # through to the jump's target (registers it changed are unknown from there on) or returns on its own.
        blocks = []                     # [address after the block, state before it, the block has returned]
        addresses = {ins.address for ins in code}
        end = code[-1].address + code[-1].size
        pops = set()
        for k, ins in enumerate(code):
            while blocks and ins.address == blocks[-1][0]:
                self.join(*blocks.pop()[1:])
            if self.done or blocks and blocks[-1][2]:
                raise Unsupported('code after the end')
            if ins.mnemonic.startswith('j') and ins.mnemonic != 'jmp':
                target = ins.operands[0].imm if ins.operands[0].type == X.X86_OP_IMM else None
                cc = INVERSE.get(ins.mnemonic[1:])
                if target is None or not ins.address < target < end or target not in addresses or cc is None \
                        or blocks and target > blocks[-1][0] or self.pending or not self.flags:
                    raise Unsupported('branch')
                self.f.stmts.append(('if', cc, self.flags))
                blocks.append([target, (dict(self.regs), dict(self.low), self.sp, dict(self.slots)), False])
                continue
            if ins.mnemonic == 'jmp' and blocks and ins.operands[0].type == X.X86_OP_IMM                     and ins.address + ins.size == blocks[-1][0]:
                # the block ends by jumping over what follows: `if (..) { block } else { what follows }`
                target = ins.operands[0].imm
                if not blocks[-1][0] < target < end or target not in addresses or self.pending                         or len(blocks) > 1 and target > blocks[-2][0]:
                    raise Unsupported('jump inside')
                after_then = (dict(self.regs), dict(self.low), self.sp, dict(self.slots))
                regs, low, sp, slots = blocks.pop()[1]
                self.regs, self.low, self.sp, self.slots, self.flags = dict(regs), dict(low), sp, dict(slots), None
                self.f.stmts.append(('else',))
                blocks.append([target, after_then, False])
                continue
            if ins.mnemonic == 'jmp' and (k != len(code) - 1 or blocks):
                raise Unsupported('jump inside')
            if any(r in ins.op_str for r in ('xmm', 'st(', 'mm')) or ins.mnemonic.startswith('f'):
                raise Unsupported('floating point')
            self.step(ins)
            if self.done:
                pops.add(self.f.pops)
                if blocks:              # a return inside a block: the code after the block goes on from its start
                    self.f.stmts.append(('ret', self.f.ret))
                    self.f.ret, self.done, blocks[-1][2] = None, False, True
        if not self.done or blocks:
            raise Unsupported('no end')
        if len(pops) > 1:
            raise Unsupported('returns that pop differently')
        f = self.f
        if f.this and f.pops % 4:
            raise Unsupported('odd pop')
        if f.pops and f.args > f.pops // 4:
            raise Unsupported('reads more arguments than it pops')
        if f.pops:
            f.args = f.pops // 4
        return f


def trunc(e, bits):
    if bits == 32:
        return e
    if e[0] == 'ext' and e[2] == bits:
        return e[3]
    if e[0] == 'trunc' and e[1] <= bits:
        return e
    return ('trunc', bits, e)


# ------------------------------------------------------------------------------------------------------- C++ text

CMP = {'e': '==', 'z': '==', 'ne': '!=', 'nz': '!=', 'l': '<', 'le': '<=', 'g': '>', 'ge': '>=',
       'b': '<u', 'be': '<=u', 'a': '>u', 'ae': '>=u'}
INVERSE = {'e': 'ne', 'ne': 'e', 'z': 'nz', 'nz': 'z', 'l': 'ge', 'ge': 'l', 'le': 'g', 'g': 'le',
           'b': 'ae', 'ae': 'b', 'be': 'a', 'a': 'be'}
CTYPE = {(8, False): 'unsigned char', (8, True): 'signed char', (16, False): 'unsigned short',
         (16, True): 'short', (32, False): 'unsigned int', (32, True): 'int'}


class Writer:
    def __init__(self, sigs, f, style):
        self.sigs = sigs        # rva -> signature of every lifted / called function
        self.f = f
        self.style = style      # {'locals': bool}
        self.names = {}         # let id -> local name (when kept as a local)
        self.used_globals = set()
        self.interfaces = set()

    def ex(self, e):
        k = e[0]
        if k == 'arg':
            return f'a{e[1]}'
        if k == 'this':
            return '(int)this'
        if k == 'const':
            v = e[1]
            return str(v) if v < 0x80000000 else ('(int)' + hex(v) + 'u' if v != 0x80000000 else '(int)0x80000000u')
        if k == 'addr':
            self.used_globals.add(e[1])
            return f'(int)&g_{e[1]:x}'
        if k in ('load', 'call'):
            if e[1] in self.names:
                return self.names[e[1]]
            expr = self.f.lets[e[1]]
            return self.mem(expr) if expr[0] == 'mem' else self.inline_call[e[1]]
        if k == 'bin':
            op, a, b = e[1], self.ex(e[2]), self.ex(e[3])
            if op == '>>u':
                return f'(int)((unsigned int){a} >> {b})'
            if op in ('rol', 'ror'):
                return f'(int)_{"rotl" if op == "rol" else "rotr"}((unsigned int){a}, {b})'
            return f'({a} {op} {b})'
        if k == 'un':
            return f'({e[1]}{self.ex(e[2])})'
        if k == 'ext':
            return f'(int)({CTYPE[(e[2], e[1])]}){self.ex(e[3])}'
        if k == 'trunc':
            return f'({CTYPE[(e[1], False)]}){self.ex(e[2])}'
        if k == 'cmp':
            return self.condition(e[1], e[2])
        raise Unsupported('expression ' + k)

    def condition(self, cc, flags):
        if flags[0] in ('cmp', 'test'):
            a, b, bits = flags[1], flags[2], flags[3]
            if flags[0] == 'test':
                if a == b:
                    a, b = a, const(0)
                else:
                    a, b = ('bin', '&', a, b), const(0)
            op = CMP.get(cc)
            if op is None:
                raise Unsupported('condition ' + cc)
            signed = not op.endswith('u')
            op = op.rstrip('u')
            t = CTYPE[(bits, signed)]
            return f'(({t}){self.ex(a)} {op} ({t}){self.ex(b)})'
        if flags[0] == 'arith' and cc in ('e', 'z', 'ne', 'nz'):
            t = CTYPE[(flags[2], False)]
            return f'(({t}){self.ex(flags[1])} {"==" if cc in ("e", "z") else "!="} 0)'
        raise Unsupported('condition')

    def mem(self, m):
        a, bits, signed = m[1], m[2], m[3]
        return f'*({CTYPE[(bits, True)]}*)({self.ex(a)})'

    def callee_text(self, kind, this, args):
        a = ', '.join(self.ex(x) for x in args)
        if kind[0] == 'virtual':
            slot = kind[1]
            name = f'I{slot}_{len(args)}'
            self.interfaces.add((slot, len(args)))
            return f'(({name}*){self.ex(this)})->s({a})'
        rva = kind[1]
        if rva in NATIVE_CALLS:
            typ, member, _, _ = NATIVE_CALLS[rva]
            if member == typ:
                # Construct a real subobject; placement-new yields its pointer.
                parameters=NATIVE_PARAMETERS.get(rva,())
                if len(parameters)!=len(args):raise Unsupported('native constructor argument types')
                values=', '.join(f'*({parameter[:-1].strip()}*){self.ex(arg)}' if parameter.endswith('&') else
                    f'({parameter}){self.ex(arg)}' for parameter,arg in zip(parameters,args))
                return '(int)('+f'new ((void*){self.ex(this)}) {typ}'+(f'({values})' if values else '')+')'
            # The binary calls a particular complete-object destructor directly,
            # even when the reconstructed class has a virtual destructor.
            return f'(({typ}*){self.ex(this)})->{typ}::{member}({a})'
        if rva in ALLOCATION_CALLS:
            op, nargs, _ = ALLOCATION_CALLS[rva]
            if op == 'new':
                return f'(int)::operator new((size_t){self.ex(args[0])})'
            arg = f'(void*){self.ex(args[0])}'
            if nargs == 2:
                arg += f', (size_t){self.ex(args[1])}'
            return f'::operator delete({arg})'
        sig = self.sigs[rva]
        if sig['this']:
            return f'(({sig["type"]}*){self.ex(this)})->f({a})'
        return f'{sig["name"]}({a})'

    def body(self):
        f = self.f
        # where every value is used: a load or call result used after a later store / call becomes a local
        uses = {}

        def walk(e, at):
            if not isinstance(e, tuple):
                return
            if e[0] in ('load', 'call'):
                uses.setdefault(e[1], []).append(at)
            for x in e[1:]:
                if isinstance(x, tuple):
                    walk(x, at)
        for at, s in enumerate(f.stmts):
            if s[0] == 'let':
                walk(s[2][1] if s[2][0] == 'mem' else (), at)
            elif s[0] == 'store':
                walk(s[1], at)
                walk(s[3], at)
            elif s[0] == 'call':
                if s[3] is not None:
                    walk(s[3], at)
                for x in s[4]:
                    walk(x, at)
            elif s[0] == 'if':
                walk(s[2], at)
            elif s[0] == 'ret' and s[1]:
                walk(s[1][0], at)
        end = len(f.stmts)
        if f.ret:
            walk(f.ret[0], end)
        effects = [at for at, s in enumerate(f.stmts) if s[0] in ('store', 'call')]
        vtables = {s[2][3][1] for s in f.stmts if s[0] == 'call' and s[2][0] == 'virtual'}
        self.inline_call = {}
        lines = []
        for at, s in enumerate(f.stmts):
            if s[0] == 'let':
                k = s[1]
                where = uses.get(k, [])
                later = [u for u in where if any(at < e < u for e in effects)]
                if self.style.get('locals') and where or later or len(where) > 1 and s[2][0] == 'mem' and self.style.get('share'):
                    t = CTYPE[(s[2][2], s[2][3])] if s[2][0] == 'mem' else 'int'
                    if s[2][0] == 'mem' and s[2][2] < 32:
                        t = 'int'
                    lines.append(f'    int v{k} = {self.mem(s[2])};')
                    self.names[k] = f'v{k}'
                elif not where and k in vtables:
                    continue
                elif not where:
                    lines.append(f'    (void)({self.mem(s[2])});')
                    raise Unsupported('load not used')
            elif s[0] == 'if':
                lines.append(f'    if ({self.condition(s[1], s[2])}) {{')
            elif s[0] == 'endif':
                lines.append('    }')
            elif s[0] == 'else':
                lines.append('    } else {')
            elif s[0] == 'ret':
                if self.sig_ret() == 'void':
                    lines.append('    return;')
                elif s[1] and usable(s[1][0]):
                    lines.append(f'    return {self.trunc_to(s[1][0], s[1][1])};')
                else:
                    raise Unsupported('a return without a value')
            elif s[0] == 'store':
                a, bits, v = s[1], s[2], s[3]
                lines.append(f'    *({CTYPE[(bits, True)]}*)({self.ex(a)}) = {self.trunc_to(v, bits)};')
            elif s[0] == 'call':
                k, kind, this, args = s[1], s[2], s[3], s[4]
                text = self.callee_text(kind, this, args)
                if at == f.tail:
                    lines.append(f'    return {text};' if f.ret and self.sig_ret() != 'void' else f'    {text};')
                    continue
                where = uses.get(k, [])
                if where:
                    lines.append(f'    int r{k} = {text};')
                    self.names[k] = f'r{k}'
                else:
                    lines.append(f'    {text};')
        if f.tail is None and f.ret and self.sig_ret() != 'void':
            e, bits = f.ret
            lines.append(f'    return {self.trunc_to(e, bits)};')
        return lines

    def trunc_to(self, e, bits):
        if bits == 32:
            return self.ex(e)
        return f'({CTYPE[(bits, False)]})({self.ex(e)})'

    def sig_ret(self):
        return self.sigs[self.f.rva]['ret']


def signature(f, ret_style):
    """How a lifted function is declared: member of K<rva> or free k<rva>, return type, arguments."""
    if f.this:
        conv = 'thiscall'
    elif f.pops:
        conv = 'stdcall'
    else:
        conv = 'cdecl'
    ret = 'void'
    if f.ret and ret_style != 'void':
        bits = f.ret[1]
        ret = 'int' if bits == 32 else 'bool' if f.ret[0][0] == 'cmp' else CTYPE[(bits, False)]
        if bits == 8 and ret_style == 'u8':
            ret = 'unsigned char'
    return dict(this=f.this, conv=conv, ret=ret, args=f.args, type=f'K{f.rva:x}', name=f'k{f.rva:x}', lifted=True)


def callee_signature(rva, this, pops, conv):
    if rva in NATIVE_CALLS:
        typ, member, native_pops, header = NATIVE_CALLS[rva]
        return dict(this=True, conv='thiscall', ret='int' if typ==member else 'void', args=native_pops // 4,
                    name=member, type=typ, lifted=False, builtin=True, header=header)
    if rva in ALLOCATION_CALLS:
        op, nargs, returns_void = ALLOCATION_CALLS[rva]
        return dict(this=False, conv='cdecl', ret='void' if returns_void else 'int', args=nargs,
                    name=f'operator {op}', type='', lifted=False, builtin=True)
    return dict(this=this, conv=conv, ret='int', args=pops // 4 if conv != 'cdecl' else None, type=f'T{rva:x}',
                name=f't{rva:x}', lifted=False)


def declare(sig, nargs=None):
    n = sig['args'] if sig['args'] is not None else nargs
    params = ', '.join('int' for _ in range(n or 0))
    keep = '__declspec(noinline) ' if sig['lifted'] else ''
    if sig['this']:
        return f'struct {sig["type"]} {{ {keep}{sig["ret"]} f({params}); }};'
    cc = ' __stdcall' if sig['conv'] == 'stdcall' else ''
    return f'{keep}{sig["ret"]}{cc} {sig["name"]}({params});'


def lift_all(im, first=RIOT[0], end=RIOT[1]):
    """Lift every function of [first, end) that no other source has rebuilt: {'lifted': {rva: Lifted}, 'sigs': {rva:
    signature of every lifted or called function}, 'reasons': {why not lifted: count}, 'users': {rva: lifted
    functions that use its result}}."""
    lifted, reasons = {}, {}
    for s in im.starts[bisect.bisect_left(im.starts, first):bisect.bisect_left(im.starts, end)]:
        if s in ALLOCATION_RVAS or s in NATIVE_CALLS:
            continue  # the real standard C++ operator ABIs are emitted separately
        owner = NATIVE_OWNERS.get(s)
        if owner and any(symbol.startswith(owner) for symbol in im.rebuilt.get(s, ())):
            continue  # a verified native destructor/callback owns this body
        if s in im.rebuilt and not any(t.startswith((f'?f@K{s:x}@@', f'?k{s:x}@@')) for t in im.rebuilt[s]):
            continue
        if im.named.get(s):
            continue
        try:
            f = Lifter(im, s).run()
            if s in gen_poly_placements.callbacks() and any(x[0] == 'if' for x in f.stmts):
                # A callback of a class description with a branch (a destructor behind a null test): lifted under
                # a generic name it would only take the name the description's initializer needs. It waits for
                # the typed generators.
                raise Unsupported('description callback')
            lifted[s] = f
        except Unsupported as e:
            why = str(e).split(' 0x')[0]
            reasons[why] = reasons.get(why, 0) + 1
        except (KeyError, IndexError, AttributeError, TypeError, ValueError):
            reasons['lifter error'] = reasons.get('lifter error', 0) + 1
    sigs = {rva: signature(f, 'int') for rva, f in lifted.items()}
    calls, users = {}, {}
    for rva, f in lifted.items():
        for at, s in enumerate(f.stmts):
            if s[0] == 'call' and s[2][0] == 'direct':
                c, kind = s[2][1], s[2]
                if at == f.tail or result_used(f, s[1]):
                    users.setdefault(c, set()).add(rva)
                if c not in sigs:
                    conv = kind[4] if len(kind) > 4 else ('thiscall' if kind[2] else 'stdcall' if kind[3] else 'cdecl')
                    calls.setdefault(c, set()).add((kind[2], kind[3], conv, len(s[4])))
    for c, forms in calls.items():
        if len(forms) == 1 and c not in sigs:
            this, pops, conv, n = next(iter(forms))
            sigs[c] = callee_signature(c, this, pops, conv)
            if conv == 'cdecl' and c not in ALLOCATION_CALLS:
                sigs[c]['args'] = n
    # a function that ends by jumping to another returns what that one returns
    for _ in range(3):
        for rva, f in lifted.items():
            if f.tail is not None:
                kind = f.stmts[f.tail][2]
                if kind[0] == 'direct' and kind[1] in sigs:
                    sigs[rva]['ret'] = sigs[kind[1]]['ret']
    # what is left in eax by a call of a function that returns nothing is not a value
    for _ in range(4):
        for rva, f in list(lifted.items()):
            for s in f.stmts:
                if s[0] == 'call' and s[2][0] == 'direct' and sigs.get(s[2][1], {}).get('ret') == 'void'                         and s[1] != (f.stmts[f.tail][1] if f.tail is not None else None) and result_used(f, s[1]):
                    if f.ret and f.ret[0] == ('call', s[1]) and not result_used_before_return(f, s[1]):
                        f.ret = None
                        sigs[rva]['ret'] = 'void'
                    else:
                        del lifted[rva]
                        del sigs[rva]
                        reasons['result of a void call'] = reasons.get('result of a void call', 0) + 1
                        break
    return dict(lifted=lifted, sigs=sigs, reasons=reasons, users=users)


def result_used_before_return(f, k):
    saved, f.ret = f.ret, None
    try:
        return result_used(f, k)
    finally:
        f.ret = saved


def result_used(f, k):
    def walk(e):
        if not isinstance(e, tuple):
            return False
        if e[0] == 'call' and e[1] == k:
            return True
        return any(walk(x) for x in e[1:] if isinstance(x, tuple))
    for s in f.stmts:
        parts = (s[2],) if s[0] == 'let' else (s[1], s[3]) if s[0] == 'store' else (s[3], *s[4]) if s[0] == 'call' \
            else (s[2],) if s[0] == 'if' else (s[1][0],) if s[0] == 'ret' and s[1] else ()
        if any(walk(x) for x in parts if x is not None):
            return True
    return bool(f.ret) and walk(f.ret[0])


def render(A, rva, style):
    """The definition of one lifted function in one source form: dict(lines, symbol, globals, interfaces, callees),
    or None when it cannot be written."""
    f, sigs = A['lifted'][rva], A['sigs']
    for s in f.stmts:
        if s[0] == 'call' and s[2][0] == 'direct':
            c = sigs.get(s[2][1])
            # the callee as this call sees it must be the callee as it is declared
            if c is None or c['this'] != (s[3] is not None) or c['args'] is not None and c['args'] != len(s[4]):
                return None
    sig = dict(sigs[rva])
    if style.get('void'):
        if sig['ret'] == 'void' or A['users'].get(rva) or f.tail is not None:
            return None
        sig['ret'] = 'void'
    if style.get('u8'):
        if sig['ret'] != 'bool':
            return None
        sig['ret'] = 'unsigned char'
    w = Writer({**sigs, rva: sig}, f, style)
    try:
        body = w.body()
    except Unsupported:
        return None
    params = ', '.join(f'int a{i}' for i in range(sig['args']))
    if sig['this']:
        head = f'{sig["ret"]} {sig["type"]}::f({params})'
        symbol = f'?f@{sig["type"]}@@'
    else:
        cc = ' __stdcall' if sig['conv'] == 'stdcall' else ''
        head = f'{sig["ret"]}{cc} {sig["name"]}({params})'
        symbol = f'?{sig["name"]}@@'
    callees = {s[2][1] for s in f.stmts if s[0] == 'call' and s[2][0] == 'direct'}
    return dict(lines=[f'{head} {{  // @{rva:x}'] + body + ['}', ''], symbol=symbol, sig=sig,
                globals=w.used_globals, interfaces=w.interfaces, callees=callees)


def interface(slot, n):
    pad = ' '.join(f'virtual void x{i}();' for i in range(slot))
    params = ', '.join('int' for _ in range(n))
    return f'struct I{slot}_{n} {{ {pad} virtual int s({params}); }};'


def source(A, items, title, probe=False):
    """A source file of rendered functions {rva: item}."""
    sigs = dict(A['sigs'])
    for rva, it in items.items():
        sigs[rva] = it['sig']
    decl = set(items)
    globals_, interfaces = set(), set()
    for it in items.values():
        decl |= it['callees']
        globals_ |= it['globals']
        interfaces |= it['interfaces']
    lines = [f'// {title} (generated by tools/gen_small.py from the client: straight-line functions lifted to C++).',
             '// Names are ours, from rvas: K<rva>::f / k<rva> lifted, T<rva>::f / t<rva> called, g_<va> globals,',
             '// I<slot>_<arguments> interfaces of virtual calls. Types are not known: every value is a 32-bit int.']
    lines += [f'// match: {rva:x} {it["symbol"]}' for rva, it in sorted(items.items())]
    lines += ['#include <stdlib.h>', '#include <new>', '']
    headers = {sigs[r]['header'] for r in decl if sigs[r].get('header')}
    lines += [f'#include "{"../src/gen/" if probe else ""}{header}"' for header in sorted(headers)]
    from gen_meta_placements import TYPED_GLOBALS
    lines += [f'extern int g_{va:x};' for va in sorted(globals_)
              if 'BinClasses.h' not in headers or f'g_{va:x}' not in TYPED_GLOBALS]
    lines += [interface(s, n) for s, n in sorted(interfaces)]
    lines += [declare(sigs[r]) for r in sorted(decl) if not sigs[r].get('builtin')] + ['']
    for rva in sorted(items):
        lines += items[rva]['lines']
    return lines


STYLES = [{}, {'locals': True}, {'void': True}, {'u8': True}, {'void': True, 'locals': True}]
_ALL = {}


def generated_target(symbol):
    """Address encoded by one of the lifter's declarations, including unnamed targets.

    match_func checks targets known to the inventory; these generated names also
    encode the address the lifted call/load actually refers to. Check those even
    when the target has no existing source or library name.
    """
    m = re.match(r'\?f@[KT]([0-9a-f]+)@@|\?[kt]([0-9a-f]+)@@', symbol)
    if m:
        return int(m[1] or m[2], 16)
    m = re.match(r'\?g_([0-9a-f]+)@@', symbol)
    if m:
        return int(m[1], 16) - P.BASE
    return None


def lifted_targets_match(rva, code):
    return all(generated_target(symbol) in (None, target)
               for symbol, target in M.symbol_addresses(rva, code))


def identical(path, items):
    """rvas of items whose function in the compiled file is the client's."""
    try:
        obj = M.compile_obj(path, M.FLAGS)
    except SystemExit as e:
        print('gen_small: does not compile:', str(e)[:2000], file=sys.stderr)
        return set()
    out = set()
    for rva, it in items.items():
        try:
            if M.compare(path, it['symbol'], rva, M.FLAGS, obj)[3] is None:
                _, code, _ = M.function_of(obj, it['symbol'])
                if lifted_targets_match(rva, code):
                    out.add(rva)
        except SystemExit:
            pass
    return out


def compilable(tmp, A, keep, items, title):
    """items less the candidates that stop the file from compiling (a global or a callee another header declares
    with a real type, a form the compiler rejects): the compiler's error lines name them. One such function must not
    cost the whole shard."""
    items = dict(items)
    for _ in range(12):
        lines = source(A, {**keep, **items}, title, probe=True)
        with open(tmp, 'w', encoding='utf-8', newline=NL) as fh:
            fh.write(NL.join(lines) + NL)
        try:
            M.compile_obj(tmp, M.FLAGS)
            return items
        except SystemExit as e:
            name = os.path.basename(tmp)
            numbers = {int(n) for n in re.findall(re.escape(name) + r'\((\d+)\): error', str(e))}
        drop, owner = set(), None
        heads = {}
        for i, text in enumerate(lines):
            m = re.search(r'// @([0-9a-f]+)$', text)
            owner = int(m[1], 16) if m else owner
            heads[i + 1] = owner
        for n in numbers:
            text = lines[n - 1] if n <= len(lines) else ''
            g = re.fullmatch(r'extern int g_([0-9a-f]+);', text)
            if g:
                drop |= {r for r, it in items.items() if int(g[1], 16) in it['globals']}
            elif heads.get(n) in items:
                drop.add(heads[n])
            else:
                for c in re.findall(r'[KkTt]([0-9a-f]{4,})', text):
                    drop |= {r for r, it in items.items() if int(c, 16) in it['callees'] or r == int(c, 16)}
        if not drop:
            print('gen_small: does not compile, no candidate to blame:', str(e)[:600], file=sys.stderr)
            return {}
        print(f'gen_small: {len(drop)} candidates left out, they do not compile', file=sys.stderr)
        for r in drop:
            items.pop(r, None)
    return {}


def generator(first, end, title):
    """gen_sources.py entry: the lifted functions of [first, end) that come out identical, each in the first source
    form (STYLES) that does."""
    def run(im):
        if 'A' not in _ALL:
            small = Image()
            _ALL['A'] = lift_all(small)
        A = _ALL['A']
        todo = {r for r in A['lifted'] if first <= r < end and r not in im.done}
        keep = {}
        tmp = os.path.join(M.OUT, f'agent_small_candidates_{first:x}.cpp')
        for style in STYLES:
            items = {r: it for r in sorted(todo) for it in [render(A, r, style)] if it}
            if not items:
                continue
            items = compilable(tmp, A, keep, items, title)
            if not items:
                continue
            good = identical(tmp, items)
            for r in good:
                keep[r] = items[r]
            todo -= good
            print(f'gen_small {first:x}: style {style}: {len(good)} of {len(items)} identical', file=sys.stderr)
        return source(A, keep, title), len(keep)
    return run


SHARDS = [(a, min(a + 0x80000, RIOT[1])) for a in range(RIOT[0], RIOT[1], 0x80000)]
ALLOCATION_SOURCE = '''#include <new>
#include <stddef.h>
void* Pool_Alloc(size_t);  // 0x9d4570
void Pool_Free(void*);    // 0x9d42e0
void* operator new(size_t size) { return Pool_Alloc(size); }
void* operator new[](size_t size) { return Pool_Alloc(size); }
void* operator new(size_t size, const std::nothrow_t&) noexcept { return Pool_Alloc(size); }
void* operator new[](size_t size, const std::nothrow_t&) noexcept { return Pool_Alloc(size); }
void operator delete(void* p) noexcept { Pool_Free(p); }
void operator delete[](void* p) noexcept { Pool_Free(p); }
void operator delete(void* p, size_t) noexcept { Pool_Free(p); }
void operator delete[](void* p, size_t) noexcept { Pool_Free(p); }
void* operator new(size_t size, std::align_val_t align) {
    size_t alignment = (size_t)align;
    alignment = alignment < sizeof(void*) ? sizeof(void*) : alignment;
    void* raw = Pool_Alloc(size + alignment);
    size_t pointer = ((size_t)raw + alignment - 1) & -alignment;
    if (pointer == (size_t)raw) pointer += alignment;
    ((void**)pointer)[-1] = raw;
    return (void*)pointer;
}
void* operator new[](size_t size, std::align_val_t align) {
    size_t alignment = (size_t)align;
    alignment = alignment < sizeof(void*) ? sizeof(void*) : alignment;
    void* raw = Pool_Alloc(size + alignment);
    size_t pointer = ((size_t)raw + alignment - 1) & -alignment;
    if (pointer == (size_t)raw) pointer += alignment;
    ((void**)pointer)[-1] = raw;
    return (void*)pointer;
}
void operator delete(void* p, std::align_val_t) noexcept {
    if (p) Pool_Free(((void**)p)[-1]);
}
void operator delete[](void* p, std::align_val_t) noexcept {
    if (p) Pool_Free(((void**)p)[-1]);
}
void operator delete(void* p, size_t, std::align_val_t) noexcept {
    if (p) Pool_Free(((void**)p)[-1]);
}
void operator delete[](void* p, size_t, std::align_val_t) noexcept {
    if (p) Pool_Free(((void**)p)[-1]);
}
'''

ALLOCATION_SYMBOLS = [
    (0x9bb8d0, '??2@YAPAXI@Z'), (0x9bb8d0, '??_U@YAPAXI@Z'),
    (0x9bb8e0, '??2@YAPAXIABUnothrow_t@std@@@Z'), (0x9bb8e0, '??_U@YAPAXIABUnothrow_t@std@@@Z'),
    (0x9bb8f0, '??2@YAPAXIW4align_val_t@std@@@Z'), (0x9bb8f0, '??_U@YAPAXIW4align_val_t@std@@@Z'),
    (0x9bb930, '??3@YAXPAX@Z'), (0x9bb930, '??_V@YAXPAX@Z'),
    (0x9bb940, '??3@YAXPAXI@Z'), (0x9bb940, '??_V@YAXPAXI@Z'),
    (0x9bb950, '??3@YAXPAXW4align_val_t@std@@@Z'), (0x9bb950, '??_V@YAXPAXW4align_val_t@std@@@Z'),
    (0x9bb950, '??3@YAXPAXIW4align_val_t@std@@@Z'), (0x9bb950, '??_V@YAXPAXIW4align_val_t@std@@@Z'),
]


def operator_allocation(im):
    """Replacement operators with real C++ ABIs; every folded alias has its own compiled body."""
    path = os.path.join(M.OUT, 'agent_small_operator_allocation.cpp')
    with open(path, 'w', encoding='utf-8', newline=NL) as fh:
        fh.write(ALLOCATION_SOURCE)
    obj = M.compile_obj(path, M.FLAGS)
    lines = ['// Riot replacement allocation operators (generated by tools/gen_small.py).',
             '// Each match/alias below is supported by its own compiled, byte-identical C++ body.']
    seen = set()
    for rva, symbol in ALLOCATION_SYMBOLS:
        result = M.compare(path, symbol, rva, M.FLAGS, obj)
        if result[3] is not None:
            raise ValueError(f'Allocation ABI {symbol} at {rva:x} is not identical: {result[4]}')
        _, code, _ = M.function_of(obj, symbol)
        expected = {0x9d4570 if rva < 0x9bb930 else 0x9d42e0}
        if {target for _, target in M.symbol_addresses(rva, code)} != expected:
            raise ValueError(f'Allocation ABI {symbol}: unexpected allocator/free target')
        lines.append(f'// {"same" if rva in seen else "match"}: {rva:x} {symbol}')
        seen.add(rva)
    return lines + ALLOCATION_SOURCE.splitlines(), len(seen)


PATTERNS = {'OperatorAllocation.cpp': operator_allocation}
PATTERNS.update({f'Small_{a:06x}.cpp': generator(a, b, f'Small functions of rva {a:x}-{b:x}') for a, b in SHARDS})


def main():
    first, end = int(sys.argv[1], 16), int(sys.argv[2], 16)
    im = Image()
    A = lift_all(im, first, end)
    items = {r: it for r in sorted(A['lifted']) for it in [render(A, r, {})] if it}
    print(NL.join(source(A, items, f'Small functions {first:x}-{end:x}')))
    print('// lifted', len(items), 'reasons', sorted(A['reasons'].items(), key=lambda x: -x[1])[:20], file=sys.stderr)


if __name__ == '__main__':
    main()
