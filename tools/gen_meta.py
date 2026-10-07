"""The reflection's sources, written from the client (patterns of tools/gen_sources.py; the machinery is in
client-src/src/Meta.h):

  MetaClasses.h    every class description found: its class (declared), the description's own class and global
  MetaClasses.cpp  the start-up function of each description that is understood: constructor arguments, base, members
  MetaMembers.cpp  MetaClass::AddMember<T> for every member type the client has a function for, and
                   MetaStaticClass<K>() for every getter of a description

A description is found by its call of the MetaClass constructor (rva 0x9b9a60); its class is named by the hash it
passes (data/hashes, else Class_<hash>), its global <class>_Meta.
"""
import bisect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_sources as G  # noqa: E402

NL = chr(10)
META_CTOR, META_DTOR, META_ADD, ATEXIT, EMPTY_TEXT = 0x9b9a60, 0x9bb6c0, 0x9bd410, 0xf411a5, 0x1532fb2
PRIMITIVE = {1: 'bool', 2: 'signed char', 3: 'u8', 4: 'short', 5: 'u16', 6: 'int', 7: 'u32', 8: 'long long', 9: 'u64',
             0xa: 'float', 0xb: 'Vector2', 0xc: 'Vector3', 0xd: 'Vector4', 0xe: 'Matrix44', 0xf: 'Color',
             0x10: 'MetaString', 0x11: 'HashValue', 0x12: 'FileLink'}
MANGLED = {'bool': '_N', 'signed char': 'C', 'u8': 'E', 'short': 'F', 'u16': 'G', 'int': 'H', 'u32': 'I',
           'long long': '_J', 'u64': '_K', 'float': 'M'}
WRAPPED = {0x82: 'MetaPointer', 0x83: 'MetaEmbed', 0x84: 'MetaLink'}
CONTAINERS = {0x80: 'BinList', 0x81: 'BinList2', 0x85: 'BinOption'}
NATURAL = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 4, 7: 4, 8: 8, 9: 8, 0xa: 4, 0xb: 8, 0xc: 12, 0xd: 16, 0xe: 64, 0xf: 4,
           0x10: 12, 0x11: 4, 0x12: 8}
OURS = {'MetaClass', 'MetaString', 'Vector2', 'Vector3', 'Vector4', 'Matrix44', 'Color', 'HashValue', 'FileLink',
        'RString', 'NoParent'}


def mangle(t):
    """MSVC's encoding of a member type (only the forms used here)."""
    if t in MANGLED:
        return MANGLED[t]
    m = re.fullmatch(r'(\w+)<(\w+)>', t)
    if m:
        return f'U?${m[1]}@U{m[2]}@@@@'
    return f'U{t}@@'


def member_wrapper(im, rva):
    """(code, description address or 0) of a one-member function that only forwards to MetaClass::AddMember."""
    fw = G.pattern(r'push dword ptr \[esp \+ 0xc\]', f'push {EMPTY_TEXT:#x}', 'push 0', 'push 0', r'push (?P<of>\w+)',
                   'push 0', r'push (?P<code>\w+)', r'push dword ptr \[esp \+ 0x24\]',
                   r'push dword ptr \[esp \+ 0x24\]', f'call {META_ADD:#x}', 'ret 0xc')
    via = G.pattern('push esi', r'push dword ptr \[esp \+ 0x10\]', 'mov esi, ecx', f'push {EMPTY_TEXT:#x}', 'push 0',
                    'push 0', r'call (?P<get>0x[0-9a-f]+)', 'push eax', 'push 0', r'push (?P<code>\w+)',
                    r'push dword ptr \[esp \+ 0x28\]', 'mov ecx, esi', r'push dword ptr \[esp \+ 0x28\]',
                    f'call {META_ADD:#x}', 'pop esi', 'ret 0xc')
    t = im.text(rva)
    m = t and fw.match(t)
    if m:
        code, of = int(m['code'], 16), int(m['of'], 16)
        if (code in PRIMITIVE and of == 0) or (code in WRAPPED and of):
            return code, of
        return None
    m = t and via.match(t)
    if m and int(m['code'], 16) in WRAPPED:
        of = getter(im, int(m['get'], 16))
        if of:
            return int(m['code'], 16), of, int(m['get'], 16)     # the description comes from a call
    return None


def getter(im, rva):
    """The address a function returns when it is only `mov eax, imm32; ret`."""
    t = im.text(rva) if im.size(rva) == 6 else None
    m = t and re.fullmatch(r'mov eax, (0x[0-9a-f]+)\nret', t)
    return int(m[1], 16) if m else None


def run_initializer(im, rva):
    """Follow a start-up function made of pushes, immediate stores and calls. -> list of events, or None if it holds
    anything else. Events: ('call', target, ecx, [args]), ('store', address, value); values are ('imm', n) or
    ('ret', event index)."""
    stack, ecx, eax, events = [], None, None, []
    for ins in im.md.disasm(im.img[rva:rva + im.size(rva)], rva):
        op, a = ins.mnemonic, ins.op_str
        if op == 'push':
            if re.fullmatch(r'0x[0-9a-f]+|\d+', a):
                stack.append(('imm', int(a, 0)))
            elif a == 'eax' and eax is not None:
                stack.append(eax)
            else:
                return None
        elif op == 'mov' and a.startswith('ecx, ') and re.fullmatch(r'0x[0-9a-f]+', a[5:]):
            ecx = int(a[5:], 16)
        elif op == 'mov' and a.startswith('dword ptr ['):
            m = re.fullmatch(r'dword ptr \[(0x[0-9a-f]+)\], (0x[0-9a-f]+|\d+|eax)', a)
            if not m:
                return None
            v = eax if m[2] == 'eax' else ('imm', int(m[2], 0))
            if v is None:
                return None
            events.append(('store', int(m[1], 16), v))
        elif op == 'call' and re.fullmatch(r'0x[0-9a-f]+', a):
            t = int(a, 16)
            if t == META_CTOR:
                n, this = 10, ecx
            elif t == ATEXIT:                       # cdecl: the caller takes the argument off afterwards
                n, this = 1, None
            elif member_wrapper(im, t) or container_wrapper(im, t):
                n, this = 3, ecx
            elif getter(im, t) is not None:
                n, this = 0, None
            else:
                return None
            if len(stack) < n:
                return None
            args = stack[len(stack) - n:][::-1]
            if t != ATEXIT:
                del stack[len(stack) - n:]
            events.append(('call', t, this, args))
            eax = ('ret', len(events) - 1)
            ecx = None
        elif op == 'add' and re.fullmatch(r'esp, (0x[0-9a-f]+|\d+)', a):
            k = int(a[5:], 0) // 4
            if len(stack) < k:
                return None
            del stack[len(stack) - k:]
        elif op == 'pop' and a == 'ecx':
            if not stack:
                return None
            stack.pop()
        elif op == 'ret' and not a:
            return events if not stack else None
        else:
            return None
    return None


def ctor_of(im, rva):
    """(description address, class hash) from the first MetaClass constructor call of a function, read from the
    immediate pushes and `mov ecx, imm` before it; None when they are not plain."""
    pushes, ecx = [], None
    for ins in im.md.disasm(im.img[rva:rva + im.size(rva)], rva):
        op, a = ins.mnemonic, ins.op_str
        if op == 'push':
            pushes.append(int(a, 0) if re.fullmatch(r'0x[0-9a-f]+|\d+', a) else None)
        elif op == 'mov' and a.startswith('ecx, '):
            ecx = int(a[5:], 16) if re.fullmatch(r'0x[0-9a-f]+', a[5:]) else None
        elif op == 'call':
            if a == f'{META_CTOR:#x}':
                return (ecx, pushes[-1]) if ecx is not None and len(pushes) >= 10 and pushes[-1] is not None else None
            pushes = []
    return None


def ctor_args(im, rva):
    """The ten arguments of the first MetaClass constructor call of a function (immediate pushes), or None."""
    pushes = []
    for ins in im.md.disasm(im.img[rva:rva + im.size(rva)], rva):
        op, a = ins.mnemonic, ins.op_str
        if op == 'push':
            pushes.append(int(a, 0) if re.fullmatch(r'0x[0-9a-f]+|\d+', a) else None)
        elif op == 'call':
            if a == f'{META_CTOR:#x}':
                args = pushes[-10:][::-1]
                return args if len(args) == 10 and None not in args else None
            pushes = []
    return None


def parent_of(im, rva, g):
    """How a description's start-up function (or own constructor, this in esi) sets the base description:
    ('imm', address), ('call', getter) or None."""
    eax = None
    for ins in im.md.disasm(im.img[rva:rva + im.size(rva)], rva):
        op, a = ins.mnemonic, ins.op_str
        if op == 'call':
            t = int(a, 16) if re.fullmatch(r'0x[0-9a-f]+', a) else None
            eax = ('call', t) if t is not None and getter(im, t) is not None else None
        m = re.fullmatch(r'dword ptr \[(0x[0-9a-f]+|esi \+ 0x1c)\], (0x[0-9a-f]+|eax)', a) if op == 'mov' else None
        if m and (m[1] == 'esi + 0x1c' or int(m[1], 16) == g + 0x1c):
            return eax if m[2] == 'eax' else ('imm', int(m[2], 16))
    return None


def this_ctor_of(im, rva):
    """Class hash of a description's own out-of-line constructor: a function that calls the MetaClass constructor on
    its this pointer (ecx on entry, kept in esi)."""
    pushes, this_in = [], {'ecx'}
    for ins in im.md.disasm(im.img[rva:rva + im.size(rva)], rva):
        op, a = ins.mnemonic, ins.op_str
        if op == 'push':
            pushes.append(int(a, 0) if re.fullmatch(r'0x[0-9a-f]+|\d+', a) else None)
        elif op == 'mov' and a == 'esi, ecx' and 'ecx' in this_in:
            this_in.add('esi')
        elif op == 'mov' and a == 'ecx, esi' and 'esi' in this_in:
            this_in.add('ecx')
        elif op == 'call':
            if a == f'{META_CTOR:#x}' and 'ecx' in this_in and len(pushes) >= 10 and pushes[-1] is not None:
                return pushes[-1]
            return None
        elif op == 'mov' and a.startswith('ecx'):
            this_in.discard('ecx')
    return None


def call_sites(im, targets):
    """target -> functions that call it (rel32 calls)."""
    out = {t: [] for t in targets}
    i = im.img.find(b'\xe8', 0x1000)
    while 0 <= i < G.TEXT1 - 5:
        t = i + 5 + int.from_bytes(im.img[i + 1:i + 5], 'little', signed=True)
        if t in out:
            out[t].append(im.starts[bisect.bisect_right(im.starts, i) - 1])
        i = im.img.find(b'\xe8', i + 1)
    return out


class Analysis:
    def __init__(self, im):
        self.im = im
        self.names = G.hash_names(('binfields',))      # member names
        types = G.hash_names(('bintypes',))
        callers = set()
        i = im.img.find(b'\xe8', 0x1000)
        while 0 <= i < G.TEXT1 - 5:
            if i + 5 + int.from_bytes(im.img[i + 1:i + 5], 'little', signed=True) == META_CTOR:
                callers.add(im.starts[bisect.bisect_right(im.starts, i) - 1])
            i = im.img.find(b'\xe8', i + 1)
        self.callers = sorted(callers)
        self.found = {}             # description address -> (start-up function, class hash)
        self.followed = {}          # description address -> events of its start-up function
        for s in self.callers:
            c = ctor_of(im, s)
            if c:
                self.found[c[0]] = (s, c[1])
                ev = run_initializer(im, s)
                ctor = [e for e in ev or () if e[0] == 'call' and e[1] == META_CTOR]
                if ev and len(ctor) == 1 and ctor[0][2] == c[0] and all(a[0] == 'imm' for a in ctor[0][3]):
                    self.followed[c[0]] = ev
        # descriptions whose own constructor is a function of its own: the start-up function only calls it
        self.ctor = {}              # description address -> its out-of-line constructor
        own = {s: this_ctor_of(im, s) for s in self.callers if not ctor_of(im, s)}
        own = {s: h for s, h in own.items() if h is not None}
        for s, users in call_sites(im, own).items():
            if len(users) != 1:
                continue
            m = re.fullmatch(NL.join([r'mov ecx, (0x[0-9a-f]+)', r'call (0x[0-9a-f]+)', r'push (0x[0-9a-f]+)',
                                      'call 0xf411a5', 'pop ecx', 'ret']), im.text(users[0]) or '')
            if m and int(m[2], 16) == s:
                g = int(m[1], 16)
                self.found[g] = (users[0], own[s])
                self.ctor[g] = s
        self.cls = {g: types.get(h, f'Class_{h:08x}') for g, (s, h) in self.found.items()}
        clash = OURS & set(self.cls.values())
        if clash:
            raise SystemExit(f'Riot class names clash with ours: {clash}')
        seen = {}
        for g in sorted(self.cls):
            seen.setdefault(self.cls[g], []).append(g)
        self.unique = {k for k, v in seen.items() if len(v) == 1}
        self.gname = {g: self.cls[g] + '_Meta' + ('' if self.cls[g] in self.unique else f'_{g:x}') for g in self.cls}

    def from_call(self):
        """Member types whose function gets the description by a call."""
        if not hasattr(self, '_from_call'):
            self._from_call = set()
            for s in self.im.starts:
                w = member_wrapper(self.im, s)
                if w and len(w) == 3 and self.member_type(*w[:2]):
                    self._from_call.add(self.member_type(*w[:2]))
        return self._from_call

    def element(self, code, size, of):
        """C++ type of a container's element (or a map's key / value: size None)."""
        k = None
        if of is not None:
            r = of[1] if of[0] == 'imm' else getter(self.im, of[1])
            k = self.cls[r] if r in self.cls and self.cls[r] in self.unique else None
            if k is None:
                return None
        if code in PRIMITIVE and (size is None or size == NATURAL[code]):
            return PRIMITIVE[code]
        if code == 0x83 and k:
            return k
        if code in WRAPPED and k:
            return f'{WRAPPED[code]}<{k}>'
        return f'BinValue<{code:#x}, {size:#x}>' if size is not None else None

    def wrapper_type(self, rva):
        """C++ type of the member a member function adds (the T of its MetaClass::AddMember<T>), or None."""
        w = member_wrapper(self.im, rva)
        if w:
            return self.member_type(*w[:2])
        c = container_wrapper(self.im, rva)
        if not c:
            return None
        if not hasattr(self, 'variants'):
            self.variants = {}
        if c['slot'] == 5:              # list-like: element code and size
            if 4 not in c['stores'] or 8 not in c['stores']:
                return None
            e = self.element(c['stores'][4][1], c['stores'][8][1], c['of'])
            kind = CONTAINERS.get(c['code'])
            base = f'{kind}<{e}' if e and kind else None
        else:                           # map: key and value codes
            if c['code'] != 0x86 or 4 not in c['stores'] or c['stores'][4][0] != 2:
                return None
            kc, vc = c['stores'][4][1] & 0xff, c['stores'][4][1] >> 8
            key, value = self.element(kc, None, None), self.element(vc, None, c['of'] if vc in (0x82, 0x83, 0x84) else None)
            base = f'BinMap<{key}, {value}' if key and value else None
        if base is None:
            return None
        # different functions (another container type) with the same element types get a variant number
        n = self.variants.setdefault(base, [])
        if rva not in n:
            n.append(rva)
        k = n.index(rva)
        return base + (f', {k}>' if k else '>')

    def member_type(self, code, of, *via):
        if code in PRIMITIVE:
            return PRIMITIVE[code]
        return f'{WRAPPED[code]}<{self.cls[of]}>' if of in self.cls and self.cls[of] in self.unique else None


def analysis(im):
    if not hasattr(im, 'meta'):
        im.meta = Analysis(im)
    return im.meta


def meta_header(im, a=None):
    a = a or analysis(im)
    out = ['// Every class description of the reflection found in the client (generated by tools/gen_meta.py): the',
           '// class it describes (Riot\'s name), the description\'s own class and its global. MetaClassOf(K*) gives',
           '// the description of K where the client has its address.',
           '#pragma once', '#include "../Meta.h"', '', 'struct MetaString;']
    out += [f'struct {k};' for k in sorted(set(a.cls.values()))]
    out.append('')
    for g in sorted(a.found, key=lambda g: a.gname[g]):
        n = a.gname[g]
        out.append(f'struct {n}Class : MetaClass {{ {n}Class(); }};')
        out.append(f'extern {n}Class {n};')
    out.append('')
    for g in sorted(a.found, key=lambda g: a.gname[g]):
        if a.cls[g] in a.unique:
            out.append(f'inline const MetaClass* MetaClassOf({a.cls[g]}*) {{ return &{a.gname[g]}; }}')
    out.append('')
    for k in sorted(a.from_call()):
        out.append(f'template <> struct MetaFromCall<{k}> {{ static constexpr bool value = true; }};')
    return out, 0


def meta_classes(im, a=None):
    """The start-up functions of the descriptions and their atexit callbacks."""
    a = a or analysis(im)
    defs, matches, skipped = [], [], 0
    for g in sorted(a.followed, key=lambda g: a.found[g][0]):
        s, ev = a.found[g][0], a.followed[g]
        if s in im.done:
            continue
        ctor = [e for e in ev if e[0] == 'call' and e[1] == META_CTOR][0]
        h, create, destroy, construct, destruct, getcls, size, align, b28, b29 = [x[1] for x in ctor[3]]
        k, n = a.cls[g], a.gname[g]
        stores = [e for e in ev if e[0] == 'store']
        atexit = [e for e in ev if e[0] == 'call' and e[1] == ATEXIT]
        members = [e for e in ev if e[0] == 'call' and e[1] not in (META_CTOR, ATEXIT) and e[2] is not None]
        parent = None
        ok = len(atexit) == 1 and all(e[2] == g for e in members)
        for st in stores:
            if st[1] == g and st[2] == ('imm', 0):
                continue
            if st[1] == g + 0x1c and st is stores[-1]:
                v = st[2]
                if v[0] == 'imm':
                    parent = '&' + a.gname[v[1]] if v[1] in a.gname else None
                else:
                    r = getter(im, ev[v[1]][1])
                    parent = f'MetaStaticClass<{a.cls[r]}>()' if r in a.cls and a.cls[r] in a.unique else None
                ok = ok and parent is not None
            else:
                ok = False
        body = []
        for e in members:
            mh, off, last = (x[1] if x[0] == 'imm' else None for x in e[3])
            t = a.wrapper_type(e[1])
            if t is None or None in (mh, off, last):
                ok = False
                break
            nm = a.names.get(mh)
            hs = f'HASH("{nm}")' if nm else f'{mh:#010x}u'
            body.append(f'AddMember<{t}>({hs}, {off:#x}, {last});')
        if not ok:
            skipped += 1
            continue
        f = atexit[0][3][0][1] - G.P.BASE

        def fn(x, what):
            return f'&{what}<{k}>' if x else 'nullptr'
        hs = f'HASH("{k}")' if not k.startswith('Class_') else f'{h:#010x}u'
        body = ['unknown00 = 0;'] + ([f'parent = {parent};'] if parent else []) + body
        defs += [f'inline {n}Class::{n}Class()',
                 f'    : MetaClass({hs}, {fn(create, "MetaCreate")}, {fn(destroy, "MetaDestroy")}, '
                 f'{fn(construct, "MetaConstruct")}, {fn(destruct, "MetaDestruct")},',
                 f'                {fn(getcls, "MetaVirtual2")}, {size:#x}, {align:#x}, '
                 f'{str(bool(b28)).lower()}, {str(bool(b29)).lower()})',
                 '{'] + [f'    {b}' for b in body] + ['}', f'{n}Class {n};', '']
        matches.append(f'// match: {s:x} ??__E{n}@@YAXXZ')
        if im.text(f) == f'mov ecx, {g:#x}{NL}jmp {META_DTOR:#x}':
            matches.append(f'// match: {f:x} ??__F{n}@@YAXXZ')
    written = {g for g in a.followed}
    rest = []
    for g in sorted(a.found, key=lambda g: a.found[g][0]):
        if g in written and any(f'??__E{a.gname[g]}@' in m for m in matches):
            continue
        n, s = a.gname[g], a.found[g][0]
        if s in im.done:
            continue
        f = None
        for ins in im.md.disasm(im.img[s:s + im.size(s)], s):
            if ins.mnemonic == 'push' and ins.op_str.startswith('0x'):
                v = int(ins.op_str, 16) - G.P.BASE
                if im.text(v) == f'mov ecx, {g:#x}{NL}jmp {META_DTOR:#x}':
                    f = v
        if g in a.ctor:
            matches.append(f'// match: {s:x} ??__E{n}@@YAXXZ')
            rest.append(f'{n}Class {n};     // its constructor is a function of its own (rva {a.ctor[g]:#x})')
        else:
            rest.append(f'{n}Class {n};     // start-up function rva {s:#x} not rebuilt yet: only its atexit callback is')
        if f is not None:
            matches.append(f'// match: {f:x} ??__F{n}@@YAXXZ')
    defs += rest
    lines = ['// The start-up function of each class description of the reflection (Meta.h; generated by',
             '// tools/gen_meta.py from the client): the description\'s facts, its base and its members. Class and',
             '// member names are Riot\'s, found from their hashes; a name not in data/hashes stays a hash. Sizes are',
             '// the client\'s numbers; the described classes themselves are only declared (MetaClasses.h).']
    lines += matches + ['#include "MetaClasses.h"', ''] + defs
    print(f'meta classes: {len(a.callers)} start-up functions, {len(a.found)} descriptions found, '
          f'{len(a.followed)} followed, {skipped} with parts not handled yet, {len(matches)} functions written')
    return lines, len(matches)


def meta_members(im, a=None):
    """AddMember<T> for each forwarding member function, MetaStaticClass<K>() for each description getter."""
    a = a or analysis(im)
    wrappers, getters = {}, {}
    for s in im.starts:
        if s in im.done:
            continue
        w = member_wrapper(im, s)
        if w:
            t = a.member_type(*w[:2])
            if t:
                wrappers[s] = t
            continue
        r = getter(im, s)
        if r in a.cls and a.cls[r] in a.unique:
            getters[s] = a.cls[r]
    lines = ['// MetaClass::AddMember<T> for the member types the client has a function for (generated by',
             '// tools/gen_meta.py). Each one is a function of its own in the client: the start-up functions call them.']
    lines += [f'// match: {s:x} ??$AddMember@{mangle(t)}@MetaClass@@QAEXIII@Z' for s, t in sorted(wrappers.items())]
    lines += ['#include "MetaClasses.h"', '',
              'template <class T> void MetaClass::AddMember(u32 hash, u32 offset, u32 last)',
              '{',
              '    AddMember(hash, offset, MetaType<T>::code, 0, MetaType<T>::Of(), nullptr, 0, "", last);',
              '}', '']
    lines += [f'template void MetaClass::AddMember<{t}>(u32, u32, u32);' for t in sorted(set(wrappers.values()))]
    print(f'meta members: {len(wrappers)} member functions')
    return lines, len(wrappers)


def meta_getters(im, a=None):
    """MetaStaticClass<K>() for each function that only returns a description's address (a file of their own, so
    that the member and start-up functions call them as the client does)."""
    a = a or analysis(im)
    getters = {}
    for s in im.starts:
        r = getter(im, s) if s not in im.done else None
        if r in a.cls and a.cls[r] in a.unique:
            getters[s] = a.cls[r]
    lines = ['// The getters of class descriptions (generated by tools/gen_meta.py): MetaStaticClass<K>() returns the',
             '// description of K. Identical code folding gives one function to every class whose getter would be the',
             '// same (the virtual GetClass of the class itself has the same code).']
    lines += [f'// match: {s:x} ??$MetaStaticClass@U{k}@@@@YAPBUMetaClass@@XZ' for s, k in sorted(getters.items())]
    lines += ['#include "MetaClasses.h"', '']
    lines += [f'template <> const MetaClass* MetaStaticClass<{k}>() {{ return MetaClassOf(({k}*)nullptr); }}'
              for k in sorted(set(getters.values()))]
    print(f'meta getters: {len(getters)}')
    return lines, len(getters)


VIRTUAL_DESTROY = 'mov ecx, dword ptr [esp + 4]|test ecx, ecx|je *|mov eax, dword ptr [ecx]|push 1|call dword ptr [eax]|ret'
VIRTUAL_DESTRUCT = 'mov ecx, dword ptr [esp + 4]|push 0|mov eax, dword ptr [ecx]|call dword ptr [eax]|ret'
VIRTUAL_2 = 'mov ecx, dword ptr [esp + 4]|mov eax, dword ptr [ecx]|jmp dword ptr [eax + 8]'


def shape_is(im, rva, form):
    """The operands standing for '*' when a function's text is form ('|' between lines), else None."""
    t = im.text(rva)
    if t is None:
        return None
    lines, want = t.split(NL), form.split('|')
    if len(lines) != len(want):
        return None
    out = []
    for got, w in zip(lines, want):
        if '*' in w:
            m = re.fullmatch(re.escape(w).replace(re.escape('*'), r'(0x[0-9a-f]+|\d+)'), got)
            if not m:
                return None
            out.append(int(m[1], 0))
        elif got != w:
            return None
    return out


def class_facts(im, a):
    """For every description: its constructor arguments, base description, whether the class is polymorphic."""
    if hasattr(a, 'facts'):
        return a.facts
    facts = {}
    for g, (s, h) in a.found.items():
        where = a.ctor.get(g, s)
        args = ctor_args(im, where)
        if not args:
            continue
        hsh, create, destroy, construct, destruct, v2, size, align, b28, b29 = args
        p = parent_of(im, where, g)
        parent = None
        if p and p[0] == 'imm':
            parent = p[1] if p[1] in a.cls else False
        elif p and p[0] == 'call':
            r = getter(im, p[1])
            parent = r if r in a.cls else False
        if parent is False:
            continue
        poly = bool(destroy) and shape_is(im, destroy - G.P.BASE, VIRTUAL_DESTROY) is not None
        facts[g] = dict(create=create and create - G.P.BASE, destroy=destroy and destroy - G.P.BASE,
                        construct=construct and construct - G.P.BASE, destruct=destruct and destruct - G.P.BASE,
                        v2=v2 and v2 - G.P.BASE, size=size, align=align, parent=parent, poly=poly)
    a.facts = facts
    return facts


def out_of_line(im, f):
    """The constructor / destructor that MetaCreate / MetaConstruct / MetaDestruct / MetaDestroy only call:
    (kind, size or None, target), or None."""
    if not f:
        return None
    r = shape_is(im, f, 'push *|call 0x9bb8d0|add esp, 4|test eax, eax|je *|mov ecx, eax|jmp *|xor eax, eax|ret')
    if r:
        return 'create', r[0], r[2]
    r = shape_is(im, f, 'mov ecx, dword ptr [esp + 4]|jmp *')
    if r:
        return 'jump', None, r[0]
    r = shape_is(im, f, 'push esi|mov esi, dword ptr [esp + 8]|test esi, esi|je *|mov ecx, esi|call *|push *|push esi|'
                        'call 0x9bb940|add esp, 8|pop esi|ret')
    if r:
        return 'delete', r[2], r[1]
    return None


PRIM_SIZE = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 4, 7: 4, 8: 8, 9: 8, 0xa: 4, 0xb: 8, 0xc: 12, 0xd: 16, 0xf: 4, 0x11: 4}


def create_stores(im, f):
    """byte offset -> value written by an inline MetaCreate (`new K` without a constructor call), the vtable
    pointer left out; None when the function is not of that form."""
    t = im.text(f) if f else None
    if not t:
        return None
    lines = t.split(NL)
    if lines[:4] != [lines[0], 'call 0x9bb8d0', 'add esp, 4', 'test eax, eax'] or not lines[4].startswith('je ') \
            or lines[-2:] != ['xor eax, eax', 'ret'] or lines[-3] != 'ret':
        return None
    out = {}
    for x in lines[5:-3]:
        m = re.fullmatch(r'mov (byte|word|dword) ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], (0x[0-9a-f]+|\d+)', x)
        if m:
            off, n, v = int(m[2] or '0', 0), {'byte': 1, 'word': 2, 'dword': 4}[m[1]], int(m[3], 0)
            if off == 0 and n == 4 and v > G.P.BASE:
                continue                    # the vtable pointer
            for j in range(n):
                out[off + j] = (v >> (8 * j)) & 0xff
            continue
        m = re.fullmatch(r'mov(q|ups) (?:qword|xmmword) ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], xmm0', x)
        if m:
            for j in range(8 if m[1] == 'q' else 16):
                out[int(m[2] or '0', 0) + j] = 0
            continue
        if x == 'xorps xmm0, xmm0':
            continue
        return None
    return out


def literal_of(code, raw):
    """C++ initializer for a member of .bin code `code` whose bytes are raw."""
    import struct as st
    v = int.from_bytes(raw, 'little')
    if code == 1:
        return 'true' if v else 'false'
    if code in (2, 4, 6, 8):
        v = int.from_bytes(raw, 'little', signed=True)
        return str(v)
    if code in (3, 5, 7, 9):
        return str(v) if v < 10 else f'{v:#x}'
    if code == 0x11:
        return f'{{{v:#x}}}'

    def fl(b):
        x = st.unpack('<f', b)[0]
        for p in range(1, 10):
            s = f'{x:.{p}g}'
            if st.pack('<f', float(s)) == b:
                break
        s = s if ('.' in s or 'e' in s or 'inf' in s or 'nan' in s) else s + '.0'
        return 'NAN' if 'nan' in s else s + 'f'
    if code == 0xa:
        return fl(raw)
    if code in (0xb, 0xc, 0xd):
        return '{' + ', '.join(fl(raw[i:i + 4]) for i in range(0, len(raw), 4)) + '}'
    if code == 0xf:
        return '{' + ', '.join(str(b) for b in raw) + '}'
    return None


def simple_layout(im, a, facts, g, memo):
    """Members (offset, C++ type, name, initializer or None) of a class whose reflected members are all plain
    values that fill it with nothing unreflected in between, its base being such a class too; None otherwise."""
    if g in memo:
        return memo[g]
    memo[g] = None
    ev, f = a.followed.get(g), facts.get(g)
    if not ev or not f:
        return None
    p = f['parent']
    if p is not None and (p not in facts or simple_layout(im, a, facts, p, memo) is None):
        return None
    base = facts[p]['size'] if p is not None else (4 if f['poly'] else 0)
    mem = []
    for e in ev:
        if e[0] == 'call' and e[2] == g and e[1] != META_CTOR:
            w = member_wrapper(im, e[1])
            if not w or len(w) != 2 or w[1] or w[0] not in PRIM_SIZE:
                return None
            mem.append((e[3][1][1], w[0], e[3][0][1]))
    mem.sort()
    stores = create_stores(im, f['create']) if f['create'] else None
    if stores is None and f['create']:
        return None
    if stores is None:
        # an abstract class: its members' initial values are in what `new` of a class derived from it writes
        if not hasattr(a, 'children'):
            a.children = {}
            for c, fc in facts.items():
                a.children.setdefault(fc['parent'], []).append(c)
        todo, stores = list(a.children.get(g, [])), {}
        while todo:
            c = todo.pop(0)
            st = create_stores(im, facts[c]['create']) if facts[c]['create'] else None
            if st:
                stores = {o: v for o, v in st.items() if o < f['size']}
                break
            todo += a.children.get(c, [])
    pos, out = base, []
    for off, code, h in mem:
        if off < pos or off - pos >= 4:     # overlap, or room for an unreflected member
            return None
        n = PRIM_SIZE[code]
        raw = [stores.get(off + j) for j in range(n)]
        init = literal_of(code, bytes(raw)) if None not in raw else None
        name = a.names.get(h) or f'm_{h:08x}'
        out.append((off, PRIMITIVE[code], name, init))
        pos = off + n
    if f['size'] - pos >= 4:
        return None
    memo[g] = out
    return out


def bin_classes(im, a=None):
    """Placeholder definitions of the described classes: base, size, alignment, virtual or not, and the constructor /
    destructor where the client has them as functions of their own. Members are not laid out yet."""
    a = a or analysis(im)
    facts = class_facts(im, a)
    defs, order, seen, memo = {}, [], set(), {}
    for g, f in facts.items():
        k = a.cls[g]
        if k not in a.unique:
            continue
        p = f['parent']
        if p is not None and (p not in facts or a.cls[p] not in a.unique or f['poly'] != facts[p]['poly']):
            continue
        base = a.cls[p] if p is not None else ('BinObject' if f['poly'] else None)
        base_size = facts[p]['size'] if p is not None else (4 if f['poly'] else 0)
        if f['size'] < base_size:
            continue
        ctor_at = {x[2] for x in (out_of_line(im, f['create']), out_of_line(im, f['construct']))
                   if x and x[0] in ('create', 'jump')}
        dtor_at = set() if f['poly'] else {x[2] for x in (out_of_line(im, f['destruct']), out_of_line(im, f['destroy']))
                                           if x}
        body = []
        if len(ctor_at) == 1:
            body.append(f'    {k}();          // rva {min(ctor_at):#x}')
        if len(dtor_at) == 1:
            body.append(f'    ~{k}();         // rva {min(dtor_at):#x}')
        if f['poly']:
            body.append('    const MetaClass* GetClass() const override;')
        layout = simple_layout(im, a, facts, g, memo)
        if layout is not None:
            for off, typ, name, init in layout:
                t = typ if typ in MANGLED else '::' + typ
                body.append(f'    {t} {name}' + (f' = {init}' if init is not None else '') + f';     // +{off:#x}')
        else:
            n = f['size'] - base_size
            if n:
                body.append(f'    u8 unknown{base_size:02x}[{n:#x}];')
        al = f' alignas({f["align"]})' if f['align'] > 4 else ''
        defs[g] = ([f'struct{al} {k}' + (f' : {base}' if base else ''), '{'] + body +
                   ['};', f'static_assert(sizeof({k}) == {f["size"]:#x}, "size from the description");', ''])

    def visit(g):
        if g is None or g in seen or g not in defs:
            return
        seen.add(g)
        visit(facts[g]['parent'])
        order.append(g)
    for g in sorted(defs, key=lambda g: a.cls[g]):
        visit(g)
    order = [g for g in order if facts[g]['parent'] is None or facts[g]['parent'] in seen]
    out = ['// The classes the reflection describes, as far as the client shows them so far (generated by',
           '// tools/gen_meta.py): base class, size, alignment, virtual or not, and the constructor / destructor where',
           '// the client has them as functions of their own. The members are not laid out yet (unknownXX).',
           '#pragma once', '#include "MetaClasses.h"', '']
    out += [x for g in order for x in defs[g]]
    a.defined = set(order)
    a.laid_out = {g for g in order if memo.get(g) is not None}
    print(f'bin classes: {len(order)} of {len(facts)} described classes defined')
    return out, 0


def meta_functions(im, a=None):
    """MetaCreate / MetaConstruct / MetaDestroy / MetaDestruct / MetaVirtual2 of the classes defined in
    BinClasses.h whose client functions have the forms those placeholders give."""
    a = a or analysis(im)
    if not hasattr(a, 'defined'):
        bin_classes(im, a)
    facts = class_facts(im, a)
    claims = {}             # rva -> (function template, class)
    vclaims = {}            # rva -> ('dtor' | 'getclass', class): virtual functions of the laid-out classes
    vall = []               # every (rva, kind, class), folded ones included
    for g in sorted(a.defined, key=lambda g: a.cls[g]):
        f, k = facts[g], a.cls[g]
        if f['poly']:
            for key, fn, form in (('destroy', 'MetaDestroy', VIRTUAL_DESTROY),
                                  ('destruct', 'MetaDestruct', VIRTUAL_DESTRUCT), ('v2', 'MetaVirtual2', VIRTUAL_2)):
                if f[key] and shape_is(im, f[key], form) is not None:
                    claims.setdefault(f[key], (fn, k))
        else:
            for key, fn in (('destroy', 'MetaDestroy'), ('destruct', 'MetaDestruct')):
                o = out_of_line(im, f[key])
                if o and o[0] in ('jump', 'delete') and (o[1] is None or o[1] == f['size']):
                    claims.setdefault(f[key], (fn, k))
        for key, fn in (('create', 'MetaCreate'), ('construct', 'MetaConstruct')):
            o = out_of_line(im, f[key])
            if o and o[0] in ('create', 'jump') and (o[1] is None or o[1] == f['size']):
                claims.setdefault(f[key], (fn, k))
        # classes laid out in full: `new K` / `new (p) K` inline
        if g in a.laid_out and f['create'] and create_stores(im, f['create']) is not None:
            claims.setdefault(f['create'], ('MetaCreate', k))
            if f['construct'] and (im.text(f['construct']) or '').startswith('mov eax, dword ptr [esp + 4]'):
                claims.setdefault(f['construct'], ('MetaConstruct', k))
            # the class's table (from the `new`): slot 0 its deleting destructor, slot 1 GetClass
            vt = re.search(r'mov dword ptr \[eax\], (0x[0-9a-f]+)', im.text(f['create']) or '')
            if f['poly'] and vt:
                o = int(vt[1], 16) - G.P.BASE
                slot0 = int.from_bytes(im.img[o:o + 4], 'little') - G.P.BASE
                slot1 = int.from_bytes(im.img[o + 4:o + 8], 'little') - G.P.BASE
                vclaims.setdefault(slot0, ('dtor', k))
                vclaims.setdefault(slot1, ('getclass', k))
                vall += [(slot0, 'dtor', k), (slot1, 'getclass', k)]
    claims = {r: c for r, c in claims.items() if r not in im.done}
    sig = {'MetaCreate': 'PAXXZ', 'MetaConstruct': 'PAXPAX@Z', 'MetaDestroy': 'XPAX@Z', 'MetaDestruct': 'XPAX@Z',
           'MetaVirtual2': 'XPAX@Z'}
    out = ['// The functions a class description points at (Meta.h), for the classes of BinClasses.h whose code the',
           '// placeholder definitions already give (generated by tools/gen_meta.py). Identical code folding gives one',
           '// function to many classes; each address is claimed for one of them.']
    out += [f'// match: {r:x} ??${fn}@U{k}@@@@YA{sig[fn]}' for r, (fn, k) in sorted(claims.items())]
    # the other classes whose description points at a claimed function (folded into it), and constructors /
    # destructors folded into a function rebuilt under another name (a class whose destructor is RString's)
    same = set()
    names = {'create': 'MetaCreate', 'destroy': 'MetaDestroy', 'construct': 'MetaConstruct', 'destruct': 'MetaDestruct',
             'v2': 'MetaVirtual2'}
    for g, f in facts.items():
        k = a.cls[g]
        if k not in a.unique:
            continue
        for key, fn in names.items():
            r = f[key]
            if r in claims and claims[r] != (fn, k):
                same.add(f'// same: {r:x} ??${fn}@U{k}@@@@YA{sig[fn]}')
        if g in a.defined and not f['poly']:
            for key, sym in (('create', f'??0{k}@@QAE@XZ'), ('construct', f'??0{k}@@QAE@XZ'),
                             ('destruct', f'??1{k}@@QAE@XZ'), ('destroy', f'??1{k}@@QAE@XZ')):
                o = out_of_line(im, f[key])
                if o and o[2] in im.done:
                    same.add(f'// same: {o[2]:x} {sym}')
    out += sorted(same)
    out += ['#include "BinClasses.h"', '',
            'template <class T> void* MetaCreate() { return new T; }',
            'template <class T> void* MetaConstruct(void* p) { return new (p) T; }',
            'template <class T> void MetaDestroy(void* p) { delete static_cast<T*>(p); }',
            'template <class T> void MetaDestruct(void* p) { static_cast<T*>(p)->~T(); }',
            'template <class T> void MetaVirtual2(void* p) { static_cast<T*>(p)->Virtual2(); }', '']
    sigs = {'MetaCreate': 'void* MetaCreate<{}>()', 'MetaConstruct': 'void* MetaConstruct<{}>(void*)',
            'MetaDestroy': 'void MetaDestroy<{}>(void*)', 'MetaDestruct': 'void MetaDestruct<{}>(void*)',
            'MetaVirtual2': 'void MetaVirtual2<{}>(void*)'}
    out += [f'template {sigs[fn].format(k)};' for r, (fn, k) in sorted(claims.items())]
    vsym = {'dtor': '??_G{}@@UAEPAXI@Z', 'getclass': '?GetClass@{}@@UBEPBUMetaClass@@XZ'}
    vmatch, vsame = [], set()
    for r, kind, k in vall:
        sym = vsym[kind].format(k)
        if vclaims.get(r) == (kind, k) and r not in im.done and r not in claims:
            vmatch.append(f'// match: {r:x} {sym}')
        else:
            vsame.add(f'// same: {r:x} {sym}')
    getclass = sorted({k for r, kind, k in vall if kind == 'getclass'})
    out += [''] + [f'const MetaClass* {k}::GetClass() const {{ return MetaClassOf(({k}*)nullptr); }}' for k in getclass]
    head = out.index('#include "BinClasses.h"')
    out[head:head] = vmatch + sorted(vsame)
    print(f'meta functions: {len(claims)}')
    return out, len(claims)


def container_wrapper(im, rva):
    """A member function that makes an elements object (`new`, then stores into it) and passes it to
    MetaClass::AddMember: {code, of: ('imm', a) / ('get', getter) / None, ops: (slot, new size, {offset: (width,
    value)}, vtable)}; None for any other function."""
    if not hasattr(im, 'cw'):
        im.cw = {}
    if rva in im.cw:
        return im.cw[rva]
    im.cw[rva] = None
    t = im.text(rva)
    if not t or f'call {META_ADD:#x}' not in t or 'call 0x9bb8d0' not in t:
        return None
    depth, stack, eax, stores, newsize, alt = 0, [], None, {}, None, False
    for line in t.split(NL):
        op, _, a = line.partition(' ')
        if alt:                         # the path where `new` gave null: eax = 0, then it joins
            if line == 'xor eax, eax':
                alt = False
                continue
        if line == 'push esi' and depth == 0 and not stack:
            depth += 1
            continue
        if line in ('mov esi, ecx', 'mov ecx, esi', 'add esp, 4', 'test eax, eax', 'pop esi', 'xorps xmm0, xmm0'):
            if line == 'add esp, 4' and stack and stack[-1][0] == 'size':
                stack.pop()
            continue
        if op == 'je' or op == 'jne':
            continue
        if op == 'jmp':
            alt = True
            continue
        m = re.fullmatch(r'push dword ptr \[esp \+ (0x[0-9a-f]+|\d+)\]', line)
        if m:
            k = (int(m[1], 0) - 4 * (depth + len(stack))) // 4 - 1
            stack.append(('arg', k))
            continue
        m = re.fullmatch(r'push (0x[0-9a-f]+|\d+)', line)
        if m:
            stack.append(('imm', int(m[1], 0)))
            continue
        if line == 'push eax':
            stack.append(eax)
            continue
        m = re.fullmatch(r'call (0x[0-9a-f]+)', line)
        if m:
            c = int(m[1], 16)
            if c == 0x9bb8d0:
                newsize = stack.pop()[1]
                eax = ('new', newsize)
            elif c == META_ADD:
                if len(stack) != 9:
                    return None
                args = stack[::-1]
                stack = []
                im.cw[rva] = args
                result = args
            elif getter(im, c) is not None:
                eax = ('get', c)
            else:
                return None
            continue
        m = re.fullmatch(r'mov (byte|word|dword) ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], (0x[0-9a-f]+|\d+)', line)
        if m:
            stores[int(m[2] or '0', 0)] = ({'byte': 1, 'word': 2, 'dword': 4}[m[1]], int(m[3], 0))
            continue
        if line == 'movq qword ptr [eax], xmm0':
            stores.setdefault(0, (8, 0))
            continue
        if line.startswith('ret'):
            break
        return None
    args = im.cw.get(rva)
    if not args:
        return None
    # AddMember(hash, offset, code, unknown0, of, list elements, map elements, text, last)
    if args[0] != ('arg', 0) or args[1] != ('arg', 1) or args[8] != ('arg', 2) or args[7] != ('imm', EMPTY_TEXT):
        im.cw[rva] = None
        return None
    if args[2][0] != 'imm' or args[3] != ('imm', 0):
        im.cw[rva] = None
        return None
    slot = 5 if args[5] and args[5][0] == 'new' else 6 if args[6] and args[6][0] == 'new' else None
    other = 6 if slot == 5 else 5
    if slot is None or args[other] != ('imm', 0):
        im.cw[rva] = None
        return None
    of = args[4]
    if of == ('imm', 0):
        of = None
    elif of[0] not in ('imm', 'get'):
        im.cw[rva] = None
        return None
    vt = stores.pop(0, None)
    if not vt or vt[0] != 4:
        im.cw[rva] = None
        return None
    res = dict(code=args[2][1], of=of, slot=slot, size=newsize, stores=stores, vtable=vt[1])
    im.cw[rva] = res
    return res
