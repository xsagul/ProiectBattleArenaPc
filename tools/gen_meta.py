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
import gen_ui_refs
import gen_reflected_buffers
import gen_reflected_lifetimes
import gen_cursor_arrays
import gen_meta_placements
import gen_vfx_runtime
import gen_ui_elements
import gen_poly_placements

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

# Abstract bases have no reflection create/placement callback to reveal their
# constructor. These entries are established by descendant calls and complete,
# compiled constructor-body comparisons (agent_ctor_parent_probe_audit.json).
BASE_CONSTRUCTORS = {'BaseLoadoutData': 0x22f580, 'TftCutsceneClip': 0x557440,
                     'MapPlaceable': 0xa22bb0,'GenericMapPlaceable':0xa21380,'ILogicBoolDriver':0xa21cf0,
                     'UiElementData': 0xadfd20, 'UIElement':0xadfb60, 'UiElementAsset':0xadfc40}

CPP_KEYWORDS = set('alignas alignof asm auto bool break case catch char char16_t char32_t class const constexpr '
                   'const_cast continue decltype default delete do double dynamic_cast else enum explicit export '
                   'extern false float for friend goto if inline int long mutable namespace new noexcept nullptr '
                   'operator private protected public register reinterpret_cast return short signed sizeof static '
                   'static_assert static_cast struct switch template this thread_local throw true try typedef '
                   'typeid typename union unsigned using virtual void volatile wchar_t while and and_eq bitand '
                   'bitor compl not not_eq or or_eq xor xor_eq'.split())


def cpp_member_name(name):
    """Reflection spelling can be a C++ keyword, unlike a source identifier."""
    name = re.sub(r'\W', '_', name)
    if not name or name[0].isdigit():
        name = 'm_' + name
    return name + '_' if name in CPP_KEYWORDS else name


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


PRIM_SIZE = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 4, 7: 4, 8: 8, 9: 8, 0xa: 4, 0xb: 8, 0xc: 12, 0xd: 16, 0xf: 4,
             0x10: 12, 0x11: 4}


RDATA = (0xfab000, 0x1752000)       # rva range of .rdata, where the vtables are


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
    out, empty_registers = {}, set()
    for x in lines[5:-3]:
        m = re.fullmatch(r'mov (ecx|edx), dword ptr \[0x1b467f0\]', x)
        if m:
            empty_registers.add(m[1])
            continue
        m = re.fullmatch(r'mov dword ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], (ecx|edx)', x)
        if m and m[2] in empty_registers:
            # A runtime empty-string pointer is initialized by MetaString's
            # actual constructor, never substituted with a constant address.
            continue
        m = re.fullmatch(r'mov (byte|word|dword) ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], (0x[0-9a-f]+|\d+)', x)
        if m:
            off, n, v = int(m[2] or '0', 0), {'byte': 1, 'word': 2, 'dword': 4}[m[1]], int(m[3], 0)
            if off == 0 and n == 4 and RDATA[0] <= v - G.P.BASE < RDATA[1]:
                continue                    # the vtable pointer (a float such as 1.0f is far above the image)
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
        name = cpp_member_name(a.names.get(h) or f'm_{h:08x}')
        out.append((off, PRIMITIVE[code], name, init))
        pos = off + n
    if f['size'] - pos >= 4:
        return None
    memo[g] = out
    return out


def zero_construct(im, rva, size):
    """A placement constructor that only clears a contiguous prefix of the object.

    Preserve scalar member initialization separately from block clearing: MSVC emits
    different code for the two source forms even when their byte stores agree.
    """
    text = im.text(rva) if rva else None
    if not text:
        return None
    lines = text.split(NL)
    # The index can concatenate another function after an unconditional return.
    # This form has no branches, so instructions after its first ret are unreachable.
    if 'ret' in lines:
        lines = lines[:lines.index('ret') + 1]
    if lines[0] != 'mov eax, dword ptr [esp + 4]' or lines[-1] != 'ret':
        return None
    stores, vector = [], False
    for line in lines[1:-1]:
        if line == 'xorps xmm0, xmm0' and not stores and not vector:
            vector = True
            continue
        m = re.fullmatch(r'mov dword ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], 0', line)
        if m:
            stores.append((int(m[1] or '0', 0), 4))
            continue
        m = re.fullmatch(r'mov(q|ups) (?:qword|xmmword) ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], xmm0', line)
        if m and vector:
            stores.append((int(m[2] or '0', 0), 8 if m[1] == 'q' else 16))
            continue
        return None
    end = 0
    for off, width in stores:
        if off != end:
            return None
        end += width
    if not end or end > size:
        return None
    return ('block' if vector else 'members'), end


def constant_construct(im, rva, size, member=False, sse=False):
    """Ordered scalar initialization stores, with untouched gaps kept as padding.

    Absolute image addresses are not integer defaults: their source needs the
    referenced object or function, so this deliberately leaves those forms out.
    """
    text = im.text(rva) if rva else None
    if not text:
        return None
    lines = text.split(NL)
    if member:
        if 'ret' not in lines:
            return None
        lines = lines[:lines.index('ret') + 1]
        if lines.count('mov eax, ecx') != 1 or 'xor ecx, ecx' in lines:
            return None
        lines = ['mov eax, dword ptr [esp + 4]'] + [
            line.replace('[ecx', '[eax') for line in lines if line != 'mov eax, ecx']
    if 'ret' not in lines or lines[0] != 'mov eax, dword ptr [esp + 4]':
        return None
    lines = lines[1:lines.index('ret')]
    stores, zero_regs, end, zero_vector = [], set(), 0, False
    for line in lines:
        if sse and line == 'xorps xmm0, xmm0':
            zero_vector = True
            continue
        m = re.fullmatch(r'xor (ecx|edx), \1', line)
        if m:
            zero_regs.add(m[1])
            continue
        m = re.fullmatch(r'mov (byte|word|dword) ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], '
                         r'(0x[0-9a-f]+|\d+|ecx|cx|cl|edx|dx|dl)', line)
        if not m:
            vector = re.fullmatch(r'mov(q|ups) (qword|xmmword) ptr \[eax(?: \+ (0x[0-9a-f]+|\d+))?\], xmm0', line)
            if not sse or not zero_vector or not vector or (vector[1], vector[2]) not in (
                    ('q', 'qword'), ('ups', 'xmmword')):
                return None
            width, off, value, register = 8 if vector[1] == 'q' else 16, int(vector[3] or '0', 0), 0, None
        else:
            width = {'byte': 1, 'word': 2, 'dword': 4}[m[1]]
            off = int(m[2] or '0', 0)
            register = {'ecx': ('ecx', 4), 'cx': ('ecx', 2), 'cl': ('ecx', 1),
                    'edx': ('edx', 4), 'dx': ('edx', 2), 'dl': ('edx', 1)}.get(m[3])
        if m and register:
            if register[0] not in zero_regs or register[1] != width:
                return None
            value = 0
        elif m:
            value = int(m[3], 0)
        if off < end or off + width > size or value >= 1 << (width * 8):
            return None
        if G.P.BASE <= value < G.P.BASE + len(im.img):
            return None
        stores.append((off, width, value))
        end = off + width
    # A three-component aggregate clears 8+4 bytes, with vector zeroing
    # scheduled before scalar-register zeroing. Preserve that aggregate source
    # form; separate Vector2/u32 members take the other compiler path.
    if sse and len(stores) >= 2 and stores[:2] == [(0, 8, 0), (8, 4, 0)] and \
            'xorps xmm0, xmm0' in lines and 'xor ecx, ecx' in lines and \
            lines.index('xorps xmm0, xmm0') < lines.index('xor ecx, ecx'):
        stores[:2] = [(0, 12, 0)]
    return stores or None


def constant_members(stores, size, align):
    """Scalar defaults at their observed offsets; no initialization of gaps."""
    body, pos = [], 0
    for off, width, value in stores:
        if off > pos:
            body.append(f'    u8 unknown{pos:02x}[{off - pos:#x}];')
        if width > 4:
            if align >= 4:
                body.append(f'    ::Vector{width // 4} unknown{off:02x} = {{}};')
            else:
                body.append(f'    u8 unknown{off:02x}[{width:#x}] = {{}};')
            pos = off + width
            continue
        # A narrower natural alignment needs narrower members, not a packed cast.
        # The compiler is allowed to coalesce adjacent byte/word initializers.
        unit = min(width, align, 4)
        while off % unit:
            unit //= 2
        typ = {1: 'u8', 2: 'u16', 4: 'u32'}[unit]
        for delta in range(0, width, unit):
            v = (value >> (delta * 8)) & ((1 << (unit * 8)) - 1)
            body.append(f'    {typ} unknown{off + delta:02x} = {v:#x};')
        pos = off + width
    if pos < size:
        body.append(f'    u8 unknown{pos:02x}[{size - pos:#x}];')
    return body


def hash_pair_layout(im, a, f, g):
    """Two native 12-byte hash-key subobjects with reflected hashes at 0 and 12."""
    if f['parent'] is not None or f['poly'] or f['align'] != 4 or f['size'] != 24:
        return None
    expected = ('push esi\nmov esi, dword ptr [esp + 8]\nmov ecx, esi\n'
                'call 0x9ba240\nlea ecx, [esi + 0xc]\npop esi\njmp 0x9ba240')
    if im.text(f['construct']) != expected:
        return None
    # The called constructor proves the eight runtime bytes following each hash.
    if im.text(0x9ba240) != ('mov dword ptr [ecx], 0\nmov eax, ecx\n'
                            'mov dword ptr [ecx + 4], 0\n'
                            'mov dword ptr [ecx + 8], 0x7fffffff\nret'):
        return None
    members = []
    for event in a.followed.get(g, ()):
        if event[0] != 'call' or event[2] != g or event[1] == META_CTOR:
            continue
        if member_wrapper(im, event[1]) != (0x11, 0):
            return None
        args = event[3]
        if len(args) != 3 or args[0][0] != 'imm' or args[1][0] != 'imm':
            return None
        off, hashed = args[1][1], args[0][1]
        name = cpp_member_name(a.names.get(hashed) or f'm_{hashed:08x}')
        members.append((off, name))
    members.sort()
    if len(members) != 2 or [off for off, _ in members] != [0, 12] or len({name for _, name in members}) != 2:
        return None
    return [f'    UiHashKey {name};     // +{off:#x}, reflected hash and native runtime key state'
            for off, name in members]


def bin_classes(im, a=None):
    """Placeholder definitions of the described classes: base, size, alignment, virtual or not, and the constructor /
    destructor where the client has them as functions of their own. Members are not laid out yet."""
    a = a or analysis(im)
    facts = class_facts(im, a)
    defs, order, seen, memo, zero_ctors, constant_ctors, native_ctors = {}, [], set(), {}, {}, {}, {}
    implicit_dtors, string_ctors, hash_ctors, buffer_ctors, ui_inline_ctors = set(), set(), set(), set(), set()
    poly_inline_ctors = set()
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
        if k in BASE_CONSTRUCTORS:
            ctor_at.add(BASE_CONSTRUCTORS[k])
        dtor_at = set() if f['poly'] else {x[2] for x in (out_of_line(im, f['destruct']), out_of_line(im, f['destroy']))
                                           if x}
        layout = simple_layout(im, a, facts, g, memo)
        ui_layout = gen_ui_refs.layout_of(im, a, f, g)
        hash_layout = hash_pair_layout(im, a, f, g)
        buffer_layout = gen_reflected_buffers.layout_of(im, a, f, g)
        lifetime_layout = gen_reflected_lifetimes.layout_of(im, a, f, g)
        cursor_layout = gen_cursor_arrays.layout_of(im,a,f,g)
        placement_layout=gen_meta_placements.layout_of(im,a,f,g)
        vfx_layout=gen_vfx_runtime.layout_of(im,a,f,g)
        element_layout=gen_ui_elements.layout_of(im,a,f,g)
        poly_layout = None
        if not ctor_at and all(x is None for x in (layout, ui_layout, hash_layout, buffer_layout, lifetime_layout,
                                                   cursor_layout, placement_layout, vfx_layout, element_layout)):
            poly_layout = gen_poly_placements.layout_of(im, a, f, g)
            if poly_layout is not None:
                poly_inline_ctors.add(g)
        if element_layout is not None:
            dtor_at=set();implicit_dtors.add(g)
            if k=='AnchorSingle':
                ctor_at=set();ui_inline_ctors.add(g)
        if vfx_layout is not None:
            ctor_at=set();dtor_at=set();implicit_dtors.add(g)
        if placement_layout is not None and k=='Class_bafabcc8':base='LevelSingleton<Class_bafabcc8>, BinObject'
        if lifetime_layout is not None:
            dtor_at = set()
            implicit_dtors.add(g)
        if buffer_layout is not None:
            buffer_ctors.add(g)
        if hash_layout is not None:
            hash_ctors.add(g)
        if ui_layout is not None:
            dtor_at = set()
            implicit_dtors.add(g)
        has_strings = layout is not None and any(typ == 'MetaString' for off, typ, name, init in layout)
        if has_strings and not ctor_at:
            string_ctors.add(g)
        if has_strings and layout[0][0] == 0 and layout[0][1] == 'MetaString' and dtor_at == {0x9bab90}:
            # Let C++ destroy the real string member. An external class dtor
            # alias at RString's address is no longer needed or justified.
            dtor_at = set()
            implicit_dtors.add(g)
        constants = constant_construct(im, f['construct'], f['size'], sse=True) if not base and layout is None else None
        native = len(ctor_at) == 1 and constants and \
            constant_construct(im, min(ctor_at), f['size'], member=True, sse=True) == constants
        if native:
            native_ctors[g] = min(ctor_at)
        body = []
        if len(ctor_at) == 1 and not native:
            body.append(f'    {k}();          // rva {min(ctor_at):#x}')
        if len(dtor_at) == 1:
            body.append(f'    ~{k}();         // rva {min(dtor_at):#x}')
        if f['poly']:
            body.append('    const MetaClass* GetClass() const override;')
        if k == 'ViewController':
            body.append('    void PostLoad(); // rva 0xaefdb0')
        zero = zero_construct(im, f['construct'], f['size']) if not base and not ctor_at else None
        scalar_layout = zero and zero[0] == 'members' and layout is not None and \
            len(layout) * 4 == zero[1] == f['size'] and all(
                off == i * 4 and (typ == 'HashValue' or typ in ('u32', 'int', 'float')) and
                init in ('0', '0.0f', '{0x0}') for i, (off, typ, name, init) in enumerate(layout))
        if scalar_layout:
            assignments = ' '.join(f'{name}' + ('.value' if typ == 'HashValue' else '') + ' = 0;'
                                   for off, typ, name, init in layout)
            body.append(f'    {k}() {{ {assignments} }}')
            zero_ctors[g] = zero
        zero_dtor = zero_construct(im, f['destruct'], f['size']) if not base and not dtor_at else None
        if zero_dtor:
            body.append(f'    ~{k}() {{ std::memset(this, 0, {zero_dtor[1]:#x}); }}')
        if element_layout is not None:
            body += element_layout
        elif ui_layout is not None:
            body += ui_layout
        elif hash_layout is not None:
            body += hash_layout
        elif buffer_layout is not None:
            body += buffer_layout
        elif lifetime_layout is not None:
            body += lifetime_layout
        elif cursor_layout is not None:
            body += cursor_layout
        elif placement_layout is not None:
            body += placement_layout
        elif vfx_layout is not None:
            body += vfx_layout
        elif poly_layout is not None:
            body += poly_layout
        elif layout is not None:
            for off, typ, name, init in layout:
                t = typ if typ in MANGLED else '::' + typ
                body.append(f'    {t} {name}' + (f' = {init}' if init is not None and not scalar_layout else '') + f';     // +{off:#x}')
        else:
            n = f['size'] - base_size
            zero = zero_construct(im, f['construct'], n) if not base and not ctor_at else None
            constants = constants if not ctor_at or native else None
            if zero and (zero[0] == 'block' or f['align'] >= 4):
                zero_ctors[g] = zero
                if zero[0] == 'members':
                    body += [f'    u32 unknown{off:02x} = 0;' for off in range(0, zero[1], 4)]
                    if n > zero[1]:
                        body.append(f'    u8 unknown{zero[1]:02x}[{n - zero[1]:#x}];')
                else:
                    body.append(f'    {k}() {{ std::memset(unknown00, 0, {zero[1]:#x}); }}')
                    body.append(f'    u8 unknown00[{n:#x}];')
            elif constants:
                body += constant_members(constants, n, f['align'])
                constant_ctors[g] = constants
            elif n:
                body.append(f'    u8 unknown{base_size:02x}[{n:#x}];')
        al = f' alignas({f["align"]})' if f['align'] > 4 else ''
        defs[g] = ([f'struct{al} {k}' + (f' : {base}' if base else ''), '{'] + body +
                   ['};', f'static_assert(sizeof({k}) == {f["size"]:#x}, "size from the description");', ''])

    def visit(g):
        if g is None or g in seen or g not in defs:
            return
        seen.add(g)
        visit(facts[g]['parent'])
        if gen_ui_elements.MANIFEST.exists() and a.cls[g] in ('UiElementData','UiPositionRect'):
            dependency='UiPositionRect' if a.cls[g]=='UiElementData' else 'AnchorSingle'
            visit(next((dg for dg in defs if a.cls[dg]==dependency),None))
        if a.cls[g] in ('FlexValueVector3','VfxFieldAccelerationDefinitionData','VfxFieldOrbitalDefinitionData',
                        'VfxParentInheritanceParams','VfxTrailDefinitionData') and gen_vfx_runtime.MANIFEST.exists():
            visit(next((dg for dg in defs if a.cls[dg]=='ValueVector3'),None))
        order.append(g)
    for g in sorted(defs, key=lambda g: a.cls[g]):
        visit(g)
    order = [g for g in order if facts[g]['parent'] is None or facts[g]['parent'] in seen]
    out = ['// The classes the reflection describes, as far as the client shows them so far (generated by',
           '// tools/gen_meta.py): base class, size, alignment, virtual or not, and the constructor / destructor where',
           '// the client has them as functions of their own. The members are not laid out yet (unknownXX).',
           '#pragma once', '#include "MetaClasses.h"', '#include "UiResourceRefs.h"', '#include "ReflectedBuffers.h"',
           '#include "ReflectedElementDefaults.h"', '#include <cstring>', '']
    out.insert(out.index('#include <cstring>'),'#include "MetaPlacementSupport.h"')
    if gen_vfx_runtime.HEADER.exists():out.insert(out.index('#include <cstring>'),'#include "VfxRuntimePointers.h"')
    if gen_ui_elements.HEADER.exists():out.insert(out.index('#include <cstring>'),'#include "UiElementOwners.h"')
    if gen_poly_placements.manifest():
        out.insert(out.index('#include <cstring>'), '#include "PolyPlacementGlobals.h"')
    out += [x for g in order for x in defs[g]]
    a.defined = set(order)
    a.laid_out = {g for g in order if memo.get(g) is not None}
    a.zero_ctors = {g: zero_ctors[g] for g in order if g in zero_ctors}
    a.inline_ctors = set(a.zero_ctors) | (set(constant_ctors) & set(order)) | (string_ctors & set(order)) | ((hash_ctors | buffer_ctors | ui_inline_ctors | poly_inline_ctors) & set(order))
    a.implicit_dtors = implicit_dtors & set(order)
    a.native_ctors = {g: native_ctors[g] for g in order if g in native_ctors}
    print(f'bin classes: {len(order)} of {len(facts)} described classes defined')
    return out, 0


def external_template_instances():
    """Explicit callbacks owned by another translation unit must not be instantiated here."""
    owned = set()
    for src in G.M.sources():
        if os.path.basename(src) == 'MetaFunctions.cpp':
            continue
        with open(src, encoding='utf-8') as source:
            for m in re.finditer(r'^template (?:<>\s*)?(?:void\*|void) (Meta\w+)<(\w+)>\(',
                                 source.read(), re.M):
                owned.add((m[1], m[2]))
    return owned


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
            if g in a.inline_ctors and f[key]:
                claims.setdefault(f[key], (fn, k))
        # classes laid out in full: `new K` / `new (p) K` inline
        if (g in a.laid_out or g in a.zero_ctors) and f['create'] and create_stores(im, f['create']) is not None:
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
    owned = external_template_instances()
    claims = {r: c for r, c in claims.items() if r not in im.done and c not in owned}
    sig = {'MetaCreate': 'PAXXZ', 'MetaConstruct': 'XPAX@Z', 'MetaDestroy': 'XPAX@Z', 'MetaDestruct': 'XPAX@Z',
           'MetaVirtual2': 'XPAX@Z'}
    out = ['// The functions a class description points at (Meta.h), for the classes of BinClasses.h whose code the',
           '// placeholder definitions already give (generated by tools/gen_meta.py). Identical code folding gives one',
           '// function to many classes; each address is claimed for one of them.']
    out += [f'// match: {r:x} ??${fn}@U{k}@@@@YA{sig[fn]}' for r, (fn, k) in sorted(claims.items())]
    native_claims = {}
    for g, r in sorted(a.native_ctors.items(), key=lambda item: a.cls[item[0]]):
        native_claims.setdefault(r, a.cls[g])
    out += [f'// match: {r:x} ??0{k}@@QAE@XZ' for r, k in sorted(native_claims.items()) if r not in im.done]
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
            if r in claims and claims[r] != (fn, k) and (fn, k) not in owned:
                same.add(f'// same: {r:x} ??${fn}@U{k}@@@@YA{sig[fn]}')
        if g in a.defined and not f['poly']:
            for key, sym in (('create', f'??0{k}@@QAE@XZ'), ('construct', f'??0{k}@@QAE@XZ'),
                             ('destruct', f'??1{k}@@QAE@XZ'), ('destroy', f'??1{k}@@QAE@XZ')):
                if key in ('destruct', 'destroy') and g in a.implicit_dtors:
                    continue
                o = out_of_line(im, f[key])
                if o and o[2] in im.done:
                    same.add(f'// same: {o[2]:x} {sym}')
    out += sorted(same)
    out += ['#include "BinClasses.h"', '',
            'template <class T> void* MetaCreate() { return new T; }',
            'template <class T> void MetaConstruct(void* p) { new (p) T; }',
            'template <class T> void MetaDestroy(void* p) { delete static_cast<T*>(p); }',
            'template <class T> void MetaDestruct(void* p) { static_cast<T*>(p)->~T(); }',
            'template <class T> void MetaVirtual2(void* p) { static_cast<T*>(p)->Virtual2(); }', '']
    sigs = {'MetaCreate': 'void* MetaCreate<{}>()', 'MetaConstruct': 'void MetaConstruct<{}>(void*)',
            'MetaDestroy': 'void MetaDestroy<{}>(void*)', 'MetaDestruct': 'void MetaDestruct<{}>(void*)',
            'MetaVirtual2': 'void MetaVirtual2<{}>(void*)'}
    instances = {(fn, k) for fn, k in claims.values()}
    aliases = []
    # Instantiate every folded template body as well as each representative.
    # Equal target addresses alone do not prove that the class definition emits it.
    for line in sorted(same):
        m = re.fullmatch(r'// same: ([0-9a-f]+) (\?\?\$(\w+)@U(\w+)@@@@\S+)', line)
        if m:
            aliases.append((int(m[1], 16), m[3], m[4]))
            instances.add((m[3], m[4]))
    out = [line for line in out if not re.match(r'// same: [0-9a-f]+ \?\?\$', line)]
    for g in sorted(a.inline_ctors, key=lambda g: a.cls[g]):
        for key, fn in (('create', 'MetaCreate'), ('construct', 'MetaConstruct')):
            r, k = facts[g][key], a.cls[g]
            if r and r not in claims and (fn, k) not in owned:
                aliases.append((r, fn, k))
                instances.add((fn, k))
    out += [f'template {sigs[fn].format(k)};' for fn, k in sorted(instances)]
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
    # Folded addresses need a real, compiled body for the reflected type.
    if aliases:
        path = os.path.join(G.M.OUT, 'meta_zero_candidates.cpp')
        with open(path, 'w', encoding='utf-8') as candidate:
            candidate.write(NL.join(out).replace('#include "BinClasses.h"',
                                                '#include "../src/gen/BinClasses.h"') + NL)
        obj = G.M.compile_obj(path, G.M.FLAGS)
        verified = 0
        for r, fn, k in sorted(set(aliases)):
            sym = f'??${fn}@U{k}@@@@YA{sig[fn]}'
            result = G.M.compare(path, sym, r, G.M.FLAGS, obj)
            if result[3] is None:
                out.insert(3, f'// same: {r:x} {sym}')
                verified += 1
        print(f'folded template aliases: {verified} of {len(set(aliases))} verified')
        for g, r in a.native_ctors.items():
            sym = f'??0{a.cls[g]}@@QAE@XZ'
            if r not in im.done:
                continue
            # A failed candidate is also in im.done during regeneration. Its
            # constructor must never reappear as an unchecked alias.
            out = [line for line in out if line != f'// same: {r:x} {sym}']
            try:
                if G.M.compare(path, sym, r, G.M.FLAGS, obj)[3] is None:
                    out.insert(3, f'// same: {r:x} {sym}')
            except SystemExit:
                pass
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
