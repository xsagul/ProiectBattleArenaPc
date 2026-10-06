"""Reads the page layouts out of a client plugin's script (data/lcu/<patch>/plugins/<plugin>/global/default/<plugin>.js).

Riot's out-of-game client is made of Ember components; each component's layout (its .hbs template) ships compiled into
the plugin's script as data: Ember.HTMLBars.template({id, block: '<JSON>'}) where the JSON lists the statements of the
template (open-element, static-attr, dynamic-attr, text, append, block ...). This turns each one back into readable
Handlebars text, so the pages can be rebuilt with the same elements, classes and texts:

    python tools/lcu_templates.py <plugin>          writes data/lcu141/templates/<plugin>/<component>.hbs

The component's name is taken from the template-path comment Riot's build leaves in each template.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PATCH = os.environ.get('LCU_PATCH', '14.1')         # LCU_PATCH=13.3 for the 13.3 client's plugins
PLUGINS = os.path.join(ROOT, 'data', 'lcu', PATCH, 'plugins')
OUT = os.path.join(ROOT, 'data', 'lcu' + PATCH.replace('.', ''), 'templates')


def path(p):
    if isinstance(p, str):
        return p
    return '.'.join('this' if x is None else str(x) for x in p)


def expr(e):
    if isinstance(e, str):
        return json.dumps(e)
    if e is None:
        return 'null'
    if isinstance(e, (int, float, bool)):
        return json.dumps(e)
    kind = e[0]
    if kind in ('unknown', 'get'):
        return path(e[1])
    if kind == 'arg':
        return '@' + path(e[1])
    if kind == 'helper':
        return '(' + ' '.join([path(e[1])] + args(e[2], e[3] if len(e) > 3 else None)) + ')'
    if kind == 'concat':
        return '"' + ''.join(p if isinstance(p, str) else '{{' + expr(p).strip('()') + '}}' for p in e[1]) + '"'
    if kind == 'has-block':
        return '(has-block)'
    if kind == 'undefined':
        return 'undefined'
    return json.dumps(e)


def args(params, hash_):
    out = [expr(p) for p in (params or [])]
    if hash_:
        keys, values = (hash_[0], hash_[1]) if len(hash_) == 2 and isinstance(hash_[0], list) else (hash_[0::2], hash_[1::2])
        out += [f'{k}={expr(v)}' for k, v in zip(keys, values)]
    return out


def render(statements, blocks, depth=0):
    out = []
    pad = lambda: '  ' * depth  # noqa: E731
    open_tag = None
    for st in statements:
        kind = st[0]
        if kind == 'text':
            t = st[1].strip()
            if t:
                out.append(pad() + t)
        elif kind == 'comment':
            if not st[1].startswith('#ember-component'):
                out.append(pad() + '<!--' + st[1] + '-->')
        elif kind == 'open-element':
            open_tag = ['<' + st[1]]
        elif kind == 'static-attr':
            (open_tag if open_tag is not None else out).append(f' {st[1]}={json.dumps(st[2])}')
        elif kind == 'dynamic-attr':
            v = expr(st[2])
            (open_tag if open_tag is not None else out).append(f' {st[1]}={v if v.startswith(chr(34)) else "{{" + v.strip("()") + "}}"}')
        elif kind == 'modifier':
            (open_tag if open_tag is not None else out).append(' {{' + ' '.join([path(st[1])] + args(st[2] if len(st) > 2 else None, st[3] if len(st) > 3 else None)) + '}}')
        elif kind == 'flush-element':
            out.append(pad() + ''.join(open_tag) + '>')
            open_tag = None
            depth += 1
        elif kind == 'close-element':
            depth = max(0, depth - 1)
            out.append(pad() + '</>')
        elif kind == 'append':
            v = expr(st[1])
            out.append(pad() + ('{{{' if len(st) > 2 and st[2] else '{{') + v.strip('()') + ('}}}' if len(st) > 2 and st[2] else '}}'))
        elif kind == 'block':
            head = ' '.join([path(st[1])] + args(st[2] if len(st) > 2 else None, st[3] if len(st) > 3 else None))
            def blk(i):
                return blocks[i] if isinstance(i, int) and 0 <= i < len(blocks) else None
            body = blk(st[4]) if len(st) > 4 else None
            inverse = blk(st[5]) if len(st) > 5 else None
            locs = (' as |' + ' '.join(body.get('locals', [])) + '|') if body and body.get('locals') else ''
            out.append(pad() + '{{#' + head + locs + '}}')
            if body:
                out += render(body['statements'], blocks, depth + 1)
            if inverse:
                out.append(pad() + '{{else}}')
                out += render(inverse['statements'], blocks, depth + 1)
            out.append(pad() + '{{/' + path(st[1]) + '}}')
        elif kind == 'yield':
            out.append(pad() + '{{yield ' + ' '.join(expr(p) for p in ((st[2] if len(st) > 2 else None) or [])) + '}}')
        else:
            out.append(pad() + '{{!' + json.dumps(st) + '}}')
    return out


def write_block(block, tid, out_dir, seen):
    """names a decoded template after its template-path comment and writes it as Handlebars text"""
    name = tid.replace('/', '_')
    for st in block.get('statements', []):
        if st[0] == 'comment' and st[1].startswith('#ember-component'):
            tp = re.search(r'template-path="([^"]*)"', st[1])
            if tp:
                parts = re.split(r'[\\/]+', tp.group(1))
                if 'src' in parts:
                    parts = parts[parts.index('src') + 1:]
                name = '.'.join(p for p in parts if p not in ('app',))
                name = re.sub(r'\.hbs$', '', name)
            break
    k = seen.get(name, 0)
    seen[name] = k + 1
    if k:
        name += f'.{k}'
    try:
        lines = render(block.get('statements', []), block.get('blocks', []))
    except Exception as e:  # noqa: BLE001
        print('  could not render', name, repr(e))
        return
    with open(os.path.join(out_dir, name + '.hbs'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    plugin = sys.argv[1]
    src = os.path.join(PLUGINS, plugin, 'global', 'default', plugin + '.js')
    s = open(src, encoding='utf-8', errors='replace').read()
    out_dir = os.path.join(OUT, plugin)
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    seen = {}
    # a third spelling (13.3 rcp-fe-ember-libs): {"id":"..","block":"<the JSON as a double-quoted script string>"}
    for m in re.finditer(r'HTMLBars\.template\(\{"id":"([^"]+)","block":"', s):
        start = m.end()
        i = start
        while True:
            j = s.index('"', i)
            back = 0
            while s[j - 1 - back] == '\\':
                back += 1
            if back % 2 == 0:
                break
            i = j + 1
        try:
            block = json.loads(json.loads('"' + s[start:j] + '"'))
        except json.JSONDecodeError as e:
            print('unreadable template', m.group(1), e)
            continue
        write_block(block, m.group(1), out_dir, seen)
        n += 1
    for m in re.finditer(r"HTMLBars\.template\(\{id:[\"']([^\"']+)[\"'],block:'", s):   # 14.1: id:"..", 13.3: id:'..'
        start = m.end()
        # the block is a single-quoted script string: ends at the first unescaped quote
        i = start
        while True:
            j = s.index("'", i)
            back = 0
            while s[j - 1 - back] == '\\':
                back += 1
            if back % 2 == 0:
                break
            i = j + 1
        raw = s[start:j]
        # undo the script string's escapes (\\ -> \, \' -> '), leaving the JSON's own
        text = re.sub(r"\\(.)", lambda mm: mm.group(1) if mm.group(1) in "\\'" else mm.group(0), raw)
        try:
            block = json.loads(text)
        except json.JSONDecodeError:
            try:
                block = json.loads(raw)
            except json.JSONDecodeError as e:
                print('unreadable template', m.group(1), e)
                continue
        write_block(block, m.group(1), out_dir, seen)
        n += 1
    print(plugin, n, 'templates ->', out_dir)


if __name__ == '__main__':
    main()
