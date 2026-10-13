"""First drafts in batches: open functions of the client handed out as self-contained packets (disassembly, Ghidra
pseudo-C, the names its targets must have), each draft checked by the matcher and, when it is close, finished by
the variant searcher. Nothing here is published: drafts live in client-src/obj/draft/<rva>/.

  draft_batch.py prepare <batch name> <functions per size class> [--seed N] [--sizes 33-64,65-128,129-256]
                                           -> packets + client-src/obj/draft/<batch name>.json
  draft_batch.py check <rva hex> [--permute MINUTES]
                                           compile client-src/obj/draft/<rva>/f.cpp, compare, record the attempt
  draft_batch.py report <batch name>       how the batch stands: identical at which attempt, by size class
"""
import bisect
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402
import packet_emu as P  # noqa: E402

DRAFT = os.path.join(M.OUT, 'draft')
NL = chr(10)
RIOT = (0x60000, 0xbc0000)          # Riot's own code
IMAGE_END = 0x3277000

RULES = '''# Writing a first draft of one client function

Goal: a C++ source file that Riot's compiler turns into exactly the bytes of the client's function. The judge is
`python tools/draft_batch.py check <rva>` (run from the project root); it compiles
`client-src/obj/draft/<rva>/f.cpp` and prints IDENTICAL or the two disassemblies side by side from the first
difference.

The file:
- Compiled as C++17 by MSVC 19.32 for 32-bit x86 with `-O2`, no exception handling, SSE2. Other options only
  with a first line `// flags: -O2 -std:c++17 ...`.
- Must be self-contained: declare the types, functions and globals it uses. `#include "../../../src/types.h"`
  gives u8 u16 u32 u64 i8 i16 i32 i64. Standard headers are available.
- The function is named after its address: a free function `k<rva>` (cdecl unless the code says otherwise), or,
  when it takes `this` in ecx, the member `f` of `struct K<rva>`. Right above the definition put the line
  `// match: <rva> ?k<rva>@@` or `// match: <rva> ?f@K<rva>@@` (hex without 0x, as in the packet).
- Things the function calls or addresses: the packet lists them. Where it says a name is REQUIRED, your code must
  refer to something that gets exactly that symbol (a mangled name: declare the C++ entity that mangles to it,
  e.g. `??2@YAPAXI@Z` is `operator new(size_t)`, `?f@K9bab90@@` is `struct K9bab90 { ... f(...); }`, `?k1234@@`
  is a free function k1234; a plain name: declare it `extern "C"`). Unnamed targets: use the same conventions
  (`k<rva>`, `K<rva>::f`, `g_<virtual address>`), with the calling convention the call site shows (who pops the
  arguments, ecx / edx use).
- Floating-point and string constants must have the client's bytes.

Method that works:
1. Read the disassembly first, the pseudo-C second (it is a reading aid and is often wrong about types).
2. Write the simplest C++ a programmer would have written for that logic; the compiler does the rest.
3. Run the check, read the first difference, change one thing, run again. Usual causes: declaration order of
   locals (register choice), a value read once vs twice, signed vs unsigned, a member of another width, struct
   vs separate scalars, `a = a + b` vs `a += b`, loop written another way, an inlined small helper.
4. At most 6 checks per function. If you are within a few instructions and stuck, run once
   `python tools/draft_batch.py check <rva> --permute 2` (a variant search of 2 minutes that rewrites the body
   for you), then move on whatever the result.

Limits: work only inside `client-src/obj/draft/<rva>/`. Do not edit anything else, do not run other tools of the
project, do not read large project files. Every check is recorded; an honest "not identical, n of m bytes" is a
useful result.
'''


def open_functions():
    """[(rva, size)] of the client functions nothing has rebuilt or identified yet, Riot's range only."""
    starts = sorted(M.starts())
    done = set(M.rebuilt_symbols())
    lib = os.path.join(ROOT, 'client-src', 'lib_functions.tsv')
    for line in open(lib) if os.path.exists(lib) else ():
        if line[0] != '#':
            done.add(int(line.split(chr(9))[0], 16))
    out = []
    for i, s in enumerate(starts[:-1]):
        if s in done or not RIOT[0] <= s < RIOT[1]:
            continue
        e = starts[i + 1]
        while e > s and P.IMG[e - 1] == 0xcc:
            e -= 1
        if e > s:
            out.append((s, e - s))
    return out


def pseudo_c():
    """rva -> Ghidra's pseudo-C of the function (client-src/decomp)."""
    if not hasattr(pseudo_c, 'v'):
        pseudo_c.v = {}
        folder = os.path.join(ROOT, 'client-src', 'decomp')
        for name in sorted(os.listdir(folder)):
            if name.startswith('text_'):
                text = open(os.path.join(folder, name), encoding='utf-8', errors='replace').read()
                for part in re.split(r'^// ---- rva ', text, flags=re.M)[1:]:
                    pseudo_c.v[int(part.split()[0], 16)] = part[part.index(NL) + 1:].strip()
    return pseudo_c.v


def packet(rva, size):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    rebuilt, known = M.rebuilt_symbols(), M.known_names()
    lines, targets = [], {}
    for i in md.disasm(bytes(P.IMG[rva:rva + size]), P.BASE + rva):
        text = f'{i.address - P.BASE:#x}  {i.mnemonic} {i.op_str}'
        for m in re.finditer(r'0x[0-9a-f]{6,8}', i.op_str):
            t = int(m[0], 16) - P.BASE
            if 0x1000 <= t < IMAGE_END and not rva <= t < rva + size:
                names = rebuilt.get(t) or sorted(known.get(t, ()))
                targets[t] = names
                text += f'    ; rva {t:#x}' + (f' = {names[0]}' if names else '')
        lines.append(text)
    tl = []
    for t, names in sorted(targets.items()):
        where = 'code' if t < 0xfab000 else 'read-only data' if t < 0x1752000 else 'data'
        tl.append(f'- rva {t:#x} (virtual address {t + P.BASE:#x}, {where}): ' +
                  (f'REQUIRED name `{names[0]}`' + (f' (also {", ".join(names[1:3])})' if len(names) > 1 else '')
                   if names else 'no name yet'))
    c = pseudo_c().get(rva, '(Ghidra has no function here)')
    return NL.join([f'# Function {rva:x}: {size} bytes at rva {rva:#x}', '',
                    f'Draft file: `client-src/obj/draft/{rva:x}/f.cpp`. Check: `python tools/draft_batch.py check {rva:x}`.',
                    'Rules: `client-src/obj/draft/RULES.md`.', '', '## Disassembly', '', '```'] + lines +
                   ['```', '', '## What it calls or addresses', ''] + (tl or ['(nothing outside itself)']) +
                   ['', '## Ghidra pseudo-C (reading aid)', '', '```c', c, '```', ''])


def prepare(name, per_class, seed, sizes):
    rng = random.Random(seed)
    funcs = [f for f in open_functions() if f[0] in pseudo_c()]
    os.makedirs(DRAFT, exist_ok=True)
    with open(os.path.join(DRAFT, 'RULES.md'), 'w', encoding='utf-8', newline=NL) as f:
        f.write(RULES)
    batch = []
    for lo, hi in sizes:
        pick = rng.sample([f for f in funcs if lo <= f[1] <= hi], per_class)
        for rva, size in sorted(pick):
            folder = os.path.join(DRAFT, f'{rva:x}')
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, 'packet.md'), 'w', encoding='utf-8', newline=NL) as f:
                f.write(packet(rva, size))
            batch.append(dict(rva=f'{rva:x}', size=size, size_class=f'{lo}-{hi}'))
    with open(os.path.join(DRAFT, name + '.json'), 'w', encoding='utf-8', newline=NL) as f:
        json.dump(batch, f, indent=1)
    print(f'{len(batch)} packets in {os.path.relpath(DRAFT, ROOT)} ({name}.json)')


def check(rva, permute_minutes=0):
    folder = os.path.join(DRAFT, f'{rva:x}')
    src = os.path.join(folder, 'f.cpp')
    record_path = os.path.join(folder, 'result.json')
    record = json.load(open(record_path)) if os.path.exists(record_path) else dict(attempts=[])

    def note(**what):
        record['attempts'].append(what)
        with open(record_path, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=1)

    if not os.path.exists(src):
        raise SystemExit(f'no draft yet: {src}')
    text = open(src, encoding='utf-8').read()
    m = re.search(rf'^// match: {rva:x} (\S+)', text, re.M)
    if not m:
        raise SystemExit(f'the draft needs a line "// match: {rva:x} ?k{rva:x}@@" (or ?f@K{rva:x}@@) above the function')
    flags = M.file_flags(src)
    try:
        obj = M.compile_obj(src, flags)
        symbol, n, same, first, detail = M.compare(src, m[1], rva, flags, obj)
    except SystemExit as e:
        note(result='does not compile or symbol missing')
        print('NOT COMPILED / SYMBOL NOT FOUND' + NL + str(e)[:3000])
        return False
    if first is None:
        note(result='identical', bytes=n)
        print(f'IDENTICAL: {symbol}, {n} bytes')
        return True
    note(result='different', bytes=n, identical_bytes=same, first=first)
    print(f'not identical: {symbol}, {n} bytes, {same} identical, first difference at +{first:#x}')
    print(NL.join(detail.split(NL)[:70]))
    if permute_minutes:
        import permute
        try:
            tokens = permute.search(src, rva, permute_minutes, quiet=True)
        except SystemExit as e:
            print('variant search not possible: ' + str(e)[:300])
            return False
        if tokens and permute.apply(src, rva, tokens):
            note(result='identical', bytes=n, by='variant search')
            print('IDENTICAL after the variant search; f.cpp now holds the found body')
            return True
        note(result='variant search found nothing')
    return False


def report(name):
    batch = json.load(open(os.path.join(DRAFT, name + '.json')))
    rows, classes = [], {}
    for b in batch:
        path = os.path.join(DRAFT, b['rva'], 'result.json')
        attempts = json.load(open(path))['attempts'] if os.path.exists(path) else []
        checks = [a for a in attempts if a['result'] != 'variant search found nothing']
        won = next((i for i, a in enumerate(attempts) if a['result'] == 'identical'), None)
        state = 'no draft' if not attempts else 'open'
        if won is not None:
            state = 'by the variant search' if attempts[won].get('by') else \
                'first check' if won == 0 else 'later check'
        best = max((a.get('identical_bytes', 0) for a in attempts), default=0)
        rows.append((b['rva'], b['size'], b['size_class'], state, len(checks), best))
        c = classes.setdefault(b['size_class'], {})
        c[state] = c.get(state, 0) + 1
    for r in rows:
        print(f'{r[0]:>8} {r[1]:5} B  {r[3]:<22} checks {r[4]}' + (f'  best {r[5]}/{r[1]}' if r[3] == 'open' else ''))
    print()
    total = {}
    for cls, c in classes.items():
        print(f'{cls:>9}: ' + ', '.join(f'{k} {v}' for k, v in sorted(c.items())))
        for k, v in c.items():
            total[k] = total.get(k, 0) + v
    done = sum(v for k, v in total.items() if k not in ('open', 'no draft'))
    size_done = sum(r[1] for r in rows if r[3] not in ('open', 'no draft'))
    print(f'identical: {done} of {len(rows)} functions, {size_done} of {sum(r[1] for r in rows)} bytes; {total}')


def main():
    a = sys.argv[1:]
    if a[:1] == ['prepare'] and len(a) >= 3:
        seed = int(a[a.index('--seed') + 1]) if '--seed' in a else 0
        sizes = a[a.index('--sizes') + 1] if '--sizes' in a else '33-64,65-128,129-256'
        prepare(a[1], int(a[2]), seed, [tuple(int(x) for x in s.split('-')) for s in sizes.split(',')])
    elif a[:1] == ['check'] and len(a) >= 2:
        minutes = float(a[a.index('--permute') + 1]) if '--permute' in a else 0
        sys.exit(0 if check(int(a[1], 16), minutes) else 1)
    elif a[:1] == ['report'] and len(a) >= 2:
        report(a[1])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
