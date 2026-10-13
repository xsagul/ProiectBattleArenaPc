"""Variant search for one nearly matching function: the last stretch between "right logic, almost the client's
instructions" and "the client's bytes", done by the processor instead of by hand.

The function body is parsed into statements; random small rewrites that a programmer would try (statement order,
operand order, compound assignments, a value kept in a local or not, if/else forms, loop forms, local types,
component loops over vectors ...) give variants; every variant is the real source file with that one body replaced,
compiled with Riot's compiler on all cores and scored by how far its instructions are from the client's. The best
ones are rewritten again until one is identical (bytes and targets, tools/match_func.py is the judge) or the time
is up. A rewrite need not keep the meaning: only a variant that IS the client's code is ever accepted.

  permute.py <source.cpp> <rva hex> [--minutes N] [--function TEXT] [--apply] [--seed N]
  permute.py --audit <progress audit json> [--minutes N per function] [--apply]

--function names the definition when the `// match:` line does not sit right above it (text of its first line).
--apply writes the found body into the source file, keeping it only if every claim of that file is still identical.
Work files and the log are in client-src/obj/permute/<source>_<rva>/ (log.jsonl, best.cpp, found.cpp).
"""
import argparse
import copy
import difflib
import json
import os
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
NL = chr(10)

TOKEN = re.compile(r'''\s+|//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_]\w*|0[xX][0-9a-fA-F]+[uUlL]*|'''
                   r'''\d+\.?\d*(?:[eE][-+]?\d+)?[fFuUlL]*|\.\d+[fF]?|->\*?|\+\+|--|<<=|>>=|[-+*/%&|^!=<>]=|&&|\|\||<<|>>|::|.''',
                   re.S)
OPEN, CLOSE = {'(': ')', '[': ']', '{': '}'}, {')', ']', '}'}
PREC = {'*': 50, '/': 50, '%': 50, '+': 40, '-': 40, '<<': 35, '>>': 35, '<': 30, '>': 30, '<=': 30, '>=': 30,
        '==': 25, '!=': 25, '&': 20, '^': 19, '|': 18, '&&': 15, '||': 14}
COMMUTE = {'+': '+', '*': '*', '&': '&', '|': '|', '^': '^', '==': '==', '!=': '!=', '&&': '&&', '||': '||',
           '<': '>', '>': '<', '<=': '>=', '>=': '<='}
INTS = ['int', 'u32', 'unsigned', 'short', 'u16', 'u8', 'char', 'bool', 'long', 'size_t', 'i32', 'i16', 'i8']
KEYWORDS = {'return', 'const', 'auto', 'if', 'else', 'for', 'while', 'new', 'delete', 'sizeof', 'case', 'goto'}
COMPOUND = ['+=', '-=', '*=', '/=', '&=', '|=', '^=', '<<=', '>>=']


def tokens_of(text):
    return [t for t in TOKEN.findall(text) if not t.isspace() and not t.startswith(('//', '/*'))]


def is_word(t):
    return bool(re.match(r'[A-Za-z_]\w*$', t))


def group_end(t, i):
    """Index just after the bracket group that opens at t[i]."""
    depth = 0
    for j in range(i, len(t)):
        if t[j] in OPEN:
            depth += 1
        elif t[j] in CLOSE:
            depth -= 1
            if not depth:
                return j + 1
    raise ValueError('unbalanced')


def group_start(t, j):
    """Index of the bracket that the closing bracket at t[j] closes."""
    depth = 0
    for i in range(j, -1, -1):
        if t[i] in CLOSE:
            depth += 1
        elif t[i] in OPEN:
            depth -= 1
            if not depth:
                return i
    raise ValueError('unbalanced')


# ---- statements: ['block', [stmt...]] | ['if', cond, then, else or None] | ['for', head, body] |
#                  ['while', cond, body] | ['do', body, cond] | ['simple', tokens]

def parse_stmt(t, i):
    if t[i] == '{':
        out, i = [], i + 1
        while t[i] != '}':
            s, i = parse_stmt(t, i)
            out.append(s)
        return ['block', out], i + 1
    if t[i] == 'if' and t[i + 1] == '(':
        e = group_end(t, i + 1)
        then, j = parse_stmt(t, e)
        other = None
        if j < len(t) and t[j] == 'else':
            other, j = parse_stmt(t, j + 1)
        return ['if', t[i + 2:e - 1], then, other], j
    if t[i] in ('for', 'while') and t[i + 1] == '(':
        e = group_end(t, i + 1)
        body, j = parse_stmt(t, e)
        return [t[i], t[i + 2:e - 1], body], j
    if t[i] == 'do':
        body, j = parse_stmt(t, i + 1)
        e = group_end(t, j + 1)
        return ['do', body, t[j + 2:e - 1]], e + 1
    j = i
    while t[j] != ';':
        j = group_end(t, j) if t[j] in OPEN else j + 1
        if t[j - 1] == '}' and t[i] in ('switch', 'try'):
            return ['simple', t[i:j]], j
    return ['simple', t[i:j + 1]], j + 1


def render(s):
    k = s[0]
    if k == 'block':
        return ['{'] + [x for c in s[1] for x in render(c)] + ['}']
    if k == 'if':
        return ['if', '('] + s[1] + [')'] + render(s[2]) + (['else'] + render(s[3]) if s[3] else [])
    if k in ('for', 'while'):
        return [k, '('] + s[1] + [')'] + render(s[2])
    if k == 'do':
        return ['do'] + render(s[1]) + ['while', '('] + s[2] + [')', ';']
    return list(s[1])


def text_of(tokens):
    """The tokens as source text, one statement per line."""
    out, depth, line, paren = [], 0, [], 0
    for t in tokens:
        if t == '}':
            depth -= 1
        line.append(t)
        paren += (t == '(') - (t == ')')
        if t in ('{', '}') or (t == ';' and not paren):
            out.append('    ' * depth + ' '.join(line))
            line = []
        if t == '{':
            depth += 1
    if line:
        out.append(' '.join(line))
    return NL.join(out)


def blocks_of(s, out=None):
    """Every block of a statement tree (the lists of statements that can be reordered)."""
    out = [] if out is None else out
    if s[0] == 'block':
        out.append(s)
        for c in s[1]:
            blocks_of(c, out)
    elif s[0] == 'if':
        blocks_of(s[2], out)
        if s[3]:
            blocks_of(s[3], out)
    elif s[0] in ('for', 'while'):
        blocks_of(s[2], out)
    elif s[0] == 'do':
        blocks_of(s[1], out)
    return out


def nodes_of(s, kind, out=None):
    out = [] if out is None else out
    if s[0] == kind:
        out.append(s)
    for c in (s[1] if s[0] == 'block' else [x for x in s[1:] if isinstance(x, list) and x and isinstance(x[0], str)
                                           and x[0] in ('block', 'if', 'for', 'while', 'do', 'simple')]):
        nodes_of(c, kind, out)
    return out


def expressions_of(s):
    """Every token list of the tree that holds an expression (simple statements, conditions, loop heads)."""
    out = [x[1] for x in nodes_of(s, 'simple')] + [x[1] for x in nodes_of(s, 'if')]
    out += [x[1] for x in nodes_of(s, 'for')] + [x[1] for x in nodes_of(s, 'while')] + [x[2] for x in nodes_of(s, 'do')]
    return out


def atom_at(t, i):
    """End index of the primary expression that starts at t[i] (name, number or bracket group, with its member
    accesses, calls and subscripts), or None."""
    if i >= len(t):
        return None
    if t[i] == '(':
        j = group_end(t, i)
    elif is_word(t[i]) or re.match(r'[\d.]', t[i]) or t[i][0] in '"\'':
        if t[i] in KEYWORDS:
            return None
        j = i + 1
    else:
        return None
    while j < len(t):
        if t[j] in ('.', '->', '::') and j + 1 < len(t) and is_word(t[j + 1]):
            j += 2
        elif t[j] in ('(', '['):
            j = group_end(t, j)
        else:
            break
    return j


def atom_before(t, j, whole=True):
    """Start index of the primary expression that ends just before t[j], or None. whole=False: the expression may
    go on after t[j] (the object in front of a member access)."""
    i = j
    while i > 0:
        if t[i - 1] in KEYWORDS:
            break
        if t[i - 1] in (')', ']'):
            i = group_start(t, i - 1)
        elif (is_word(t[i - 1]) or re.match(r'[\d.]', t[i - 1])) and (i == j or t[i] in ('.', '->', '::', '(', '[')):
            i -= 1
        elif t[i - 1] in ('.', '->', '::') and i < j:
            i -= 1
        else:
            break
    return i if i < j and (not whole or atom_at(t, i) == j) else None


def prec(t, i):
    return PREC.get(t[i], 0) if 0 <= i < len(t) else 0


# ---- rewrites: each takes the function's top block and a random generator, changes the tree in place and
#      returns True, or returns False when it does not apply

def swap_adjacent(top, rng):
    blocks = [b for b in blocks_of(top) if len(b[1]) > 1]
    if not blocks:
        return False
    b = rng.choice(blocks)[1]
    i = rng.randrange(len(b) - 1)
    b[i], b[i + 1] = b[i + 1], b[i]
    return True


def move_statement(top, rng):
    blocks = [b for b in blocks_of(top) if len(b[1]) > 2]
    if not blocks:
        return False
    b = rng.choice(blocks)[1]
    i = rng.randrange(len(b))
    s = b.pop(i)
    b.insert(rng.choice([j for j in range(len(b) + 1) if j != i]), s)
    return True


def swap_operands(top, rng):
    spots = []
    for t in expressions_of(top):
        for i, x in enumerate(t):
            if x in COMMUTE and 0 < i < len(t) - 1:
                a, b = atom_before(t, i), atom_at(t, i + 1)
                if a is not None and b is not None and prec(t, a - 1) < PREC[x] and prec(t, b) <= PREC[x] \
                        and (a == 0 or t[a - 1] not in ('.', '->', '::', '<')):
                    spots.append((t, a, i, b))
    if not spots:
        return False
    t, a, i, b = rng.choice(spots)
    t[a:b] = t[i + 1:b] + [COMMUTE[t[i]]] + t[a:i]
    return True


def compound_assign(top, rng):
    spots = []
    for s in nodes_of(top, 'simple'):
        t = s[1]
        for op in COMPOUND:
            if op in t and atom_at(t, 0) == t.index(op):
                spots.append((s, 'open', op))
        if '=' in t:
            e = t.index('=')
            lhs = t[:e]
            if atom_at(t, 0) == e and t[e + 1:e + 1 + len(lhs)] == lhs and e + 1 + len(lhs) < len(t) - 1 \
                    and t[e + 1 + len(lhs)] + '=' in COMPOUND:
                spots.append((s, 'close', t[e + 1 + len(lhs)]))
    if not spots:
        return False
    s, how, op = rng.choice(spots)
    t = s[1]
    if how == 'open':
        e = t.index(op)
        rhs = t[e + 1:-1]
        whole = atom_at(rhs, 0) == len(rhs)
        new = [op[:-1]] + (rhs if whole else ['('] + rhs + [')'])
        s[1] = t[:e] + ['='] + (t[:e] + new if rng.random() < 0.7 or op[:-1] not in '+*&|^' else
                               (rhs if whole else ['('] + rhs + [')']) + [op[:-1]] + t[:e]) + [';']
    else:
        e = t.index('=')
        s[1] = t[:e] + [op + '='] + t[e + 2 + e:]
    return True


def step_form(top, rng):
    """x++ / ++x / x += 1 (and the same with --) wherever one stands alone."""
    spots = []
    for t in expressions_of(top):
        for i, x in enumerate(t):
            if x in ('++', '--'):
                if atom_at(t, i + 1) is not None and (i == 0 or t[i - 1] in (';', ',', '(')):
                    spots.append((t, 'pre', i, atom_at(t, i + 1)))
                a = atom_before(t, i)
                if a is not None and (a == 0 or t[a - 1] in (';', ',')) and (i + 1 == len(t) or t[i + 1] in (';', ',', ')')):
                    spots.append((t, 'post', a, i + 1))
    if not spots:
        return False
    t, how, a, b = rng.choice(spots)
    op = t[a] if how == 'pre' else t[b - 1]
    name = t[a + 1:b] if how == 'pre' else t[a:b - 1]
    t[a:b] = rng.choice([[op] + name, name + [op], name + [op[0] + '=', '1']])
    return True


def negate(cond):
    if cond[:2] == ['!', '('] and group_end(cond, 1) == len(cond):
        return cond[2:-1]
    return ['!', '('] + cond + [')']


def swap_branches(top, rng):
    spots = [s for s in nodes_of(top, 'if') if s[3]]
    if not spots:
        return False
    s = rng.choice(spots)
    s[1], s[2], s[3] = negate(s[1]), s[3], s[2]
    return True


def split_and(top, rng):
    spots = []
    for s in nodes_of(top, 'if'):
        depth = 0
        for i, x in enumerate(s[1]):
            depth += (x in OPEN) - (x in CLOSE)
            if x == '&&' and not depth and not s[3] and '||' not in s[1]:
                spots.append((s, i))
        if not s[3] and s[2][0] == 'if' and not s[2][3]:
            spots.append((s, None))
        if not s[3] and s[2][0] == 'block' and len(s[2][1]) == 1 and s[2][1][0][0] == 'if' and not s[2][1][0][3]:
            spots.append((s, -1))
    if not spots:
        return False
    s, i = rng.choice(spots)
    if i is None or i == -1:
        inner = s[2] if i is None else s[2][1][0]
        s[1], s[2] = ['('] + s[1] + [')', '&&', '('] + inner[1] + [')'], inner[2]
    else:
        s[1], s[2] = s[1][:i], ['if', s[1][i + 1:], s[2], None]
    return True


def early_return(top, rng):
    b = top[1]
    if not b:
        return False
    last = b[-1]
    if last[0] == 'if' and not last[3] and top is not None:
        body = last[2][1] if last[2][0] == 'block' else [last[2]]
        b[-1:] = [['if', negate(last[1]), ['simple', ['return', ';']], None]] + body
        return True
    for i, s in enumerate(b[:-1]):
        if s[0] == 'if' and not s[3] and render(s[2]) in (['return', ';'], ['{', 'return', ';', '}']):
            b[i:] = [['if', negate(s[1]), ['block', b[i + 1:]], None]]
            return True
    return False


def extract_local(top, rng):
    spots = []
    for b in blocks_of(top):
        for n, s in enumerate(b[1]):
            t = s[1] if s[0] in ('simple', 'if', 'while') else None
            if not t:
                continue
            start = t.index('=') + 1 if s[0] == 'simple' and '=' in t else 0
            for i in range(start, len(t)):
                if i and (t[i - 1] in ('.', '->', '::') or is_word(t[i - 1])):
                    continue
                j = atom_at(t, i)
                if j is not None and j - i > 1 and t[j:j + 1] not in (['='], ['++'], ['--']) \
                        and not (t[j:j + 1] and t[j] in COMPOUND):
                    spots.append((b, n, t, i, j))
    if not spots:
        return False
    b, n, t, i, j = rng.choice(spots)
    name = f'local{rng.randrange(1000)}'
    how = rng.choice([['auto'], ['const', 'auto'], ['auto', '&'], ['const', 'auto', '&']])
    decl = ['simple', how + [name, '='] + t[i:j] + [';']]
    t[i:j] = [name]
    b[1].insert(n, decl)
    return True


def declaration(t):
    """(type tokens, name, initialiser tokens or None) of a simple statement that declares one local."""
    for k in range(1, min(6, len(t) - 1)):
        if is_word(t[k]) and t[k + 1] in ('=', ';') and all(is_word(x) or x in ('*', '&', '::') for x in t[:k]) \
                and t[0] not in ('return', 'delete', 'goto', 'case') and is_word(t[k - 1]) | (t[k - 1] in '*&'):
            return t[:k], t[k], (t[k + 2:-1] if t[k + 1] == '=' else None)
    return None


def inline_local(top, rng):
    spots = []
    for b in blocks_of(top):
        for n, s in enumerate(b[1]):
            d = declaration(s[1]) if s[0] == 'simple' else None
            if d and d[2]:
                rest = [x for c in b[1][n + 1:] for x in render(c)]
                if rest.count(d[1]) == 1:
                    spots.append((b, n, d))
    if not spots:
        return False
    b, n, d = rng.choice(spots)
    del b[1][n]
    for t in [x for c in b[1][n:] for x in expressions_of(c)]:
        if d[1] in t:
            i = t.index(d[1])
            t[i:i + 1] = ['('] + d[2] + [')']
            return True
    return False


def retype_local(top, rng):
    spots = []
    for s in nodes_of(top, 'simple') + [['simple', f[1]] for f in nodes_of(top, 'for')]:
        for i, x in enumerate(s[1][:3]):
            if x in INTS and i + 1 < len(s[1]) and is_word(s[1][i + 1]):
                spots.append((s[1], i))
    if not spots:
        return False
    t, i = rng.choice(spots)
    t[i] = rng.choice([x for x in INTS if x != t[i]])
    return True


def toggle_const(top, rng):
    spots = [s for s in nodes_of(top, 'simple') if declaration(s[1]) and declaration(s[1])[2]]
    if not spots:
        return False
    s = rng.choice(spots)
    s[1] = s[1][1:] if s[1][0] == 'const' else ['const'] + s[1]
    return True


def split_declaration(top, rng):
    spots = []
    for b in blocks_of(top):
        for n, s in enumerate(b[1]):
            d = declaration(s[1]) if s[0] == 'simple' else None
            if d and d[2] and 'const' not in d[0] and '&' not in d[0] and 'auto' not in d[0]:
                spots.append((b, n, d))
    if not spots:
        return False
    b, n, d = rng.choice(spots)
    b[1][n:n + 1] = [['simple', d[0] + [d[1], ';']], ['simple', [d[1], '='] + d[2] + [';']]]
    if rng.random() < 0.5:
        b[1].insert(0, b[1].pop(n))
    return True


def loop_form(top, rng):
    spots = []
    for b in blocks_of(top):
        for n, s in enumerate(b[1]):
            if s[0] == 'for' and s[1].count(';') == 2 and 'continue' not in render(s[2]):
                spots.append((b, n, 'for'))
            if s[0] == 'while':
                spots.append((b, n, 'while'))
    if not spots:
        return False
    b, n, kind = rng.choice(spots)
    s = b[1][n]
    if kind == 'for':
        i, j = s[1].index(';'), len(s[1]) - 1 - s[1][::-1].index(';')
        init, cond, step = s[1][:i], s[1][i + 1:j], s[1][j + 1:]
        body = (s[2][1] if s[2][0] == 'block' else [s[2]]) + ([['simple', step + [';']]] if step else [])
        b[1][n:n + 1] = [['block', ([['simple', init + [';']]] if init else []) +
                          [['while', cond or ['true'], ['block', body]]]]]
    else:
        b[1][n] = ['for', [';'] + s[1] + [';'], s[2]]
    return True


def ternary_form(top, rng):
    spots = []
    for b in blocks_of(top):
        for n, s in enumerate(b[1]):
            if s[0] == 'simple' and '?' in s[1] and '=' in s[1] and s[1].index('=') < s[1].index('?') \
                    and ':' in s[1] and not declaration(s[1]):
                spots.append((b, n, 'open'))
            if s[0] == 'if' and s[3] and s[2][0] == s[3][0] == 'simple' and '=' in s[2][1] and '=' in s[3][1] \
                    and s[2][1][:s[2][1].index('=')] == s[3][1][:s[3][1].index('=')]:
                spots.append((b, n, 'close'))
    if not spots:
        return False
    b, n, how = rng.choice(spots)
    s = b[1][n]
    if how == 'open':
        t = s[1]
        e, q = t.index('='), t.index('?')
        depth, c = 0, None
        for i in range(q + 1, len(t)):
            depth += (t[i] in OPEN or t[i] == '?') - (t[i] in CLOSE)
            if t[i] == ':' and not depth:
                c = i
                break
            if t[i] == ':':
                depth -= 1
        if c is None:
            return False
        b[1][n] = ['if', t[e + 1:q], ['simple', t[:e + 1] + t[q + 1:c] + [';']],
                   ['simple', t[:e + 1] + t[c + 1:-1] + [';']]]
    else:
        e = s[2][1].index('=')
        b[1][n] = ['simple', s[2][1][:e + 1] + ['('] + s[1] + [')', '?'] + s[2][1][e + 1:-1] + [':'] +
                   s[3][1][e + 1:-1] + [';']]
    return True


def component_loop(top, rng):
    """`a.x op= s; a.y op= s;` (.. z, w) -> `for (int i = 0; i < n; ++i) (&a.x)[i] op= s;`: Riot's vector code is
    written over components (measured on the UI slice calculators)."""
    spots = []
    for b in blocks_of(top):
        for n, s in enumerate(b[1]):
            if s[0] != 'simple' or ['.', 'x'] not in [s[1][i:i + 2] for i in range(len(s[1]) - 1)]:
                continue
            count = 1
            for letter in 'yzw':
                want = [letter if x == 'x' and i and s[1][i - 1] == '.' else x for i, x in enumerate(s[1])]
                if n + count < len(b[1]) and b[1][n + count][0] == 'simple' and b[1][n + count][1] == want:
                    count += 1
                else:
                    break
            if count > 1:
                spots.append((b, n, count))
    if not spots:
        return False
    b, n, count = rng.choice(spots)
    t = list(b[1][n][1])
    i = len(t) - 1
    while i > 0:
        if t[i] == 'x' and t[i - 1] == '.':
            a = atom_before(t, i - 1, whole=False)
            if a is None:
                return False
            t[a:i + 1] = ['(', '&'] + t[a:i + 1] + [')', '[', 'i', ']']
            i = a
        i -= 1
    b[1][n:n + count] = [['for', ['int', 'i', '=', '0', ';', 'i', '<', str(count), ';', '++', 'i'], ['simple', t]]]
    return True


def spread_aggregate(top, rng):
    """`a = {e1, e2, ..};` -> `a.x = e1; a.y = e2; ..` (a vector assigned as a whole or member by member)."""
    spots = []
    for b in blocks_of(top):
        for n, s in enumerate(b[1]):
            t = s[1] if s[0] == 'simple' else []
            if '=' in t and t[t.index('=') + 1:t.index('=') + 2] == ['{'] and t[-2:] == ['}', ';'] \
                    and atom_at(t, 0) == t.index('=') and not declaration(t):
                spots.append((b, n))
    if not spots:
        return False
    b, n = rng.choice(spots)
    t = b[1][n][1]
    e = t.index('=')
    parts, depth, last = [], 0, e + 2
    for i in range(e + 2, len(t) - 1):
        depth += (t[i] in OPEN) - (t[i] in CLOSE)
        if (t[i] == ',' and not depth) or i == len(t) - 2:
            parts.append(t[last:i])
            last = i + 1
    if not 2 <= len(parts) <= 4:
        return False
    b[1][n:n + 1] = [['simple', t[:e] + ['.', letter, '='] + part + [';']] for letter, part in zip('xyzw', parts)]
    return True


REWRITES = [(spread_aggregate, 2), (swap_adjacent, 6), (move_statement, 3), (swap_operands, 6), (compound_assign, 3), (step_form, 1),
            (swap_branches, 3), (split_and, 2), (early_return, 1), (extract_local, 6), (inline_local, 4),
            (retype_local, 2), (toggle_const, 1), (split_declaration, 2), (loop_form, 2), (ternary_form, 2),
            (component_loop, 2)]


def mutate(top, rng):
    """A copy of the tree with one to three rewrites applied, and their names."""
    tree, done = copy.deepcopy(top), []
    for _ in range(rng.choice([1, 1, 1, 2, 2, 3])):
        for _ in range(8):
            f = rng.choices([r[0] for r in REWRITES], [r[1] for r in REWRITES])[0]
            try:
                if f(tree, rng):
                    done.append(f.__name__)
                    break
            except (ValueError, IndexError):
                tree = copy.deepcopy(top)
    return tree, done


# ---- the function inside its source file

def locate(src_text, rva, function=None):
    """(symbol text, index of the body's `{`, index after its `}`) of the definition a `// match: <rva>` line
    claims. The definition is the one right below that line, else the one named by the symbol, else `function`."""
    m = re.search(rf'^// match: {rva:x} (\S+).*$', src_text, re.M)
    if not m:
        raise SystemExit(f'no "// match: {rva:x}" line in the source')
    symbol = m[1]
    at = None
    if function:
        at = src_text.index(function)
    else:
        rest = src_text[m.end():]
        k = re.match(r'(?:\s*//[^\n]*\n)*\s*', rest).end()
        if rest[k:k + 1] not in ('', '#') and re.match(r'[\w~:<>*&\s,]+\(', rest[k:]):
            at = m.end() + k
        else:
            parts = re.match(r'\?+\$?(\w+)@(?:(\w+)@)?', symbol)
            name = parts and (f'{parts[2]}::{parts[1]}' if parts[2] else parts[1])
            names = ([name] if name else []) + ([parts[1]] if parts and parts[2] else [])
            for name in names:
                # the first place that names it and goes on to a body: a declaration ends in `;` before any `{`
                for hit in re.finditer(rf'^[^\n;{{}}]*\b{re.escape(name)}\s*\(', src_text, re.M):
                    close = src_text.find(')', hit.end())
                    brace, semi = src_text.find('{', close), src_text.find(';', close)
                    if brace >= 0 and (semi < 0 or brace < semi):
                        at = hit.start()
                        break
                if at is not None:
                    break
            if at is None:
                raise SystemExit('cannot find the definition: pass --function "<text of its first line>"')
    paren = src_text.index('(', at)
    depth, i = 0, paren
    while True:
        depth += (src_text[i] == '(') - (src_text[i] == ')')
        i += 1
        if not depth:
            break
    start = src_text.index('{', i)
    if ';' in src_text[i:start]:
        raise SystemExit('the definition found is only a declaration: pass --function')
    depth, j = 0, start
    while True:
        depth += (src_text[j] == '{') - (src_text[j] == '}')
        j += 1
        if not depth:
            break
    return symbol, start, j


# ---- compile and score

class Judge:
    def __init__(self, src, rva, function=None):
        import match_func as M
        import packet_emu as P
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        self.M, self.src, self.rva = M, os.path.abspath(src), rva
        self.text = open(src, encoding='utf-8').read()
        self.symbol, self.a, self.b = locate(self.text, rva, function)
        line = re.search(rf'^// match: {rva:x} \S+(.*)$', self.text, re.M)
        self.flags = line[1].split() or M.file_flags(src)
        self.cl, vc_include = M.compiler_of(src)
        include = [vc_include] + [os.path.join(M.SDK, d) for d in ('ucrt', 'shared', 'um')]
        self.env = dict(os.environ, INCLUDE=';'.join(os.path.abspath(d) for d in include if os.path.isdir(d)))
        self.dir = os.path.join(M.OUT, 'permute', f'{os.path.splitext(os.path.basename(src))[0]}_{rva:x}')
        os.makedirs(self.dir, exist_ok=True)
        self.md = Cs(CS_ARCH_X86, CS_MODE_32)
        starts = sorted(M.starts())
        import bisect
        end = starts[bisect.bisect_right(starts, rva)]
        theirs = bytes(P.IMG[rva:end])
        while theirs and theirs[-1] == 0xcc:
            theirs = theirs[:-1]
        self.theirs = theirs
        self.their_lines = self.lines(theirs)
        self.top = parse_stmt(tokens_of(self.text[self.a:self.b]), 0)[0]

    def lines(self, code):
        """Instructions as text with everything a relocation or the load address changes taken out."""
        out = []
        for i in self.md.disasm(code, 0):
            ops = i.op_str
            if i.mnemonic == 'call' or (i.mnemonic == 'jmp' and ops.startswith('0x') and not 0 <= int(ops, 16) < len(code)):
                ops = 'T' if ops.startswith('0x') else ops
            ops = re.sub(r'0x[0-9a-f]{6,}', 'A', ops)
            out.append(f'{i.mnemonic} {ops}')
        return out

    def source_with(self, body_tokens):
        return self.text[:self.a] + NL + text_of(body_tokens) + NL + self.text[self.b:]

    def compile(self, n, body_tokens):
        """(score, bytes or None) of variant n; score None when it does not compile."""
        path = os.path.join(self.dir, f'v{n}.cpp')
        obj = path[:-4] + '.obj'
        with open(path, 'w', encoding='utf-8', newline=NL) as f:
            f.write(self.source_with(body_tokens))
        r = subprocess.run([self.cl, '/nologo', '/c', *self.flags, '/I' + os.path.dirname(self.src), '/Fo' + obj, path],
                           capture_output=True, text=True, env=self.env, cwd=ROOT)
        return path, obj, r.returncode == 0

    def score(self, obj):
        try:
            _, ours, rel = self.M.function_of(obj, self.symbol)
        except SystemExit:
            return None, None
        while ours and ours[-1] in (0xcc, 0x90) and len(ours) - 1 not in rel:
            ours = ours[:-1]
        masked = bytes(self.theirs[i] if i in rel and i < len(self.theirs) else b for i, b in enumerate(ours))
        if masked == self.theirs:
            return 0, ours
        a, b = self.lines(masked), self.their_lines
        same = sum(x.size for x in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
        return max(len(a), len(b)) - same + abs(len(ours) - len(self.theirs)) / 1000 + 0.0001, ours

    def exact(self, path, obj):
        return self.M.compare(path, self.symbol, self.rva, self.flags, obj)[3] is None


def search(src, rva, minutes=10, function=None, seed=0, workers=None, quiet=False):
    """Body tokens of a variant identical to the client, or None; writes best.cpp / found.cpp and log.jsonl."""
    judge = Judge(src, rva, function)
    rng = random.Random(seed)
    workers = workers or os.cpu_count() or 4
    log = open(os.path.join(judge.dir, 'log.jsonl'), 'a', encoding='utf-8')
    base = render(judge.top)
    path, obj, ok = judge.compile(0, base)
    if not ok:
        raise SystemExit('the source does not compile after re-rendering its body (preprocessor lines or a '
                         'constructor initialiser list with braces inside the function?)')
    s0, _ = judge.score(obj)
    if s0 is None:
        raise SystemExit(f'symbol {judge.symbol} is not in the object')
    if s0 == 0 and judge.exact(path, obj):
        print(f'{judge.symbol}: already identical')
        return base
    pool = [(s0, 0, judge.top)]
    seen = {' '.join(base)}
    best, tried, failed, t0, n = s0, 0, 0, time.time(), 0
    if not quiet:
        print(f'{judge.symbol} at {rva:x}: start {s0:.3f} instructions away, {workers} compilers')
    with ThreadPoolExecutor(workers) as pool_exec:
        while time.time() - t0 < minutes * 60:
            batch = []
            for _ in range(workers * 2):
                weights = [1 / (1 + (p[0] - pool[0][0])) ** 2 for p in pool]
                parent = rng.choices(pool, weights)[0]
                tree, done = mutate(parent[2], rng)
                tokens = render(tree)
                key = ' '.join(tokens)
                if done and key not in seen:
                    seen.add(key)
                    n += 1
                    batch.append((n, tree, tokens, done))
            if not batch:
                failed += 1
                if failed > 200:
                    break
                continue
            results = list(pool_exec.map(lambda item: judge.compile(item[0], item[2]), batch))
            for (k, tree, tokens, done), (path, obj, ok) in zip(batch, results):
                tried += 1
                score = judge.score(obj)[0] if ok else None
                if score == 0 and not judge.exact(path, obj):
                    score = 0.5             # the client's bytes with another call target
                if score is not None and score <= pool[-1][0] + 2:
                    pool.append((score, k, tree))
                if score is not None and score < best:
                    best = score
                    log.write(json.dumps(dict(t=round(time.time() - t0, 1), tried=tried, score=score, rewrites=done)) + NL)
                    log.flush()
                    with open(os.path.join(judge.dir, 'best.cpp'), 'w', encoding='utf-8', newline=NL) as f:
                        f.write(judge.source_with(tokens))
                    if not quiet:
                        print(f'  {time.time() - t0:7.1f}s  {tried:6} tried  best {score:.3f}  {"+".join(done)}')
                if score == 0:
                    with open(os.path.join(judge.dir, 'found.cpp'), 'w', encoding='utf-8', newline=NL) as f:
                        f.write(judge.source_with(tokens))
                    print(f'{judge.symbol}: IDENTICAL after {tried} variants, {time.time() - t0:.0f} s '
                          f'-> {os.path.relpath(os.path.join(judge.dir, "found.cpp"), ROOT)}')
                    clean(judge.dir)
                    return tokens
                for x in (path, obj):
                    if os.path.exists(x):
                        os.remove(x)
            pool.sort(key=lambda p: (p[0], -p[1]))
            del pool[24:]
    clean(judge.dir)
    print(f'{judge.symbol}: not found; {tried} variants in {time.time() - t0:.0f} s, best {best:.3f} '
          f'instructions away (start {s0:.3f})')
    return None


def clean(directory):
    for name in os.listdir(directory):
        if re.fullmatch(r'v\d+\.(cpp|obj)', name):
            os.remove(os.path.join(directory, name))


def apply(src, rva, tokens, function=None):
    """Put the found body into the source; keep it only if every claim of the file is still identical."""
    import match_func as M
    old = open(src, encoding='utf-8').read()
    _, a, b = locate(old, rva, function)
    with open(src, 'w', encoding='utf-8', newline=NL) as f:
        f.write(old[:a] + text_of(tokens) + old[b:])
    flags = M.file_flags(src)
    obj = M.compile_obj(src, flags)
    bad = []
    for m in re.finditer(r'^// (?:match|same): ([0-9a-f]+) (\S+)(.*)$', open(src, encoding='utf-8').read(), re.M):
        f2 = m[3].split() or flags
        o = obj if f2 == flags else M.compile_obj(src, f2)
        if M.compare(src, m[2], int(m[1], 16), f2, o)[3] is not None:
            bad.append(m[1])
    if bad:
        with open(src, 'w', encoding='utf-8', newline=NL) as f:
            f.write(old)
        print(f'  not applied: with this body the claims {bad} of the file are not identical any more')
        return False
    print(f'  applied to {os.path.relpath(src, ROOT)}: all its claims identical')
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', nargs='?')
    ap.add_argument('rva', nargs='?')
    ap.add_argument('--audit')
    ap.add_argument('--minutes', type=float, default=10)
    ap.add_argument('--function')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--workers', type=int)
    args = ap.parse_args()
    jobs = []
    if args.audit:
        for f in json.load(open(args.audit))['failures']:
            if not str(f['detail']).startswith('same bytes, different targets'):
                jobs.append((f['source'], int(f['rva'], 16)))
    elif args.source and args.rva:
        jobs.append((args.source, int(args.rva, 16)))
    else:
        ap.error('give a source and an rva, or --audit')
    for src, rva in jobs:
        try:
            tokens = search(src, rva, args.minutes, args.function, args.seed, args.workers)
        except SystemExit as e:
            print(f'{os.path.basename(src)} {rva:x}: skipped: {str(e)[:200]}')
            continue
        if tokens and args.apply:
            apply(src, rva, tokens, args.function)


if __name__ == '__main__':
    main()
