"""Explains one draw of a GPU sponge capture: the shader permutation's defines, the blend / depth / raster state, and
every constant of the bound constant buffers by the name the shader itself gives it.

  python tools/sponge/explain_draw.py <tag dir> <draw index> [frame index]

The constant names come from the captured shader's own reflection data (the "Buffer Definitions" of its disassembly),
so each value is read exactly as the shader reads it.
"""
import ctypes
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import read_sponge as rs  # noqa: E402

BLEND = {1: 'ZERO', 2: 'ONE', 3: 'SRC_COLOR', 4: 'INV_SRC_COLOR', 5: 'SRC_ALPHA', 6: 'INV_SRC_ALPHA', 7: 'DEST_ALPHA', 8: 'INV_DEST_ALPHA',
         9: 'DEST_COLOR', 10: 'INV_DEST_COLOR', 11: 'SRC_ALPHA_SAT', 14: 'BLEND_FACTOR', 15: 'INV_BLEND_FACTOR'}
OP = {1: 'ADD', 2: 'SUBTRACT', 3: 'REV_SUBTRACT', 4: 'MIN', 5: 'MAX'}
CMP = {1: 'NEVER', 2: 'LESS', 3: 'EQUAL', 4: 'LESS_EQUAL', 5: 'GREATER', 6: 'NOT_EQUAL', 7: 'GREATER_EQUAL', 8: 'ALWAYS'}


def disassemble(blob):
    dll = ctypes.WinDLL('d3dcompiler_47.dll')
    out = ctypes.c_void_p()
    if dll.D3DDisassemble(blob, len(blob), 0, None, ctypes.byref(out)) != 0 or not out.value:
        return ''
    vt = ctypes.cast(ctypes.cast(out, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    get_ptr = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(vt[3])
    get_size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(vt[4])
    return ctypes.string_at(get_ptr(out), get_size(out)).decode('latin-1').rstrip('\0')


def layout(asm):
    """({cbuffer name: [(variable, type, offset, size, unused)]}, {cbuffer name: slot}) from a disassembly's comments."""
    buffers, slots, cur = {}, {}, None
    for line in asm.split('\n'):
        m = re.match(r'//\s+cbuffer (\S+)', line)
        if m:
            cur = m.group(1)
            buffers[cur] = []
            continue
        m = re.match(r'//\s+(\S+) (\S+?)(\[\d+\])?;\s+// Offset:\s+(\d+) Size:\s+(\d+)( \[unused\])?', line)
        if m and cur:
            buffers[cur].append((m.group(2) + (m.group(3) or ''), m.group(1), int(m.group(4)), int(m.group(5)), bool(m.group(6))))
            continue
        m = re.match(r'//\s+(\S+)\s+cbuffer\s+NA\s+NA\s+cb(\d+)', line)
        if m:
            slots[m.group(1)] = int(m.group(2))
    return buffers, slots


def main():
    tag, want = sys.argv[1], int(sys.argv[2])
    objs = rs.Objects(os.path.join(tag, 'objects.bin'))
    index = json.load(open(rs.INDEX)) if os.path.exists(rs.INDEX) else {}
    tex_index = json.load(open(rs.TEX_INDEX)) if os.path.exists(rs.TEX_INDEX) else {}
    frames = sorted(f for f in os.listdir(tag) if f.startswith('frame_') and f.endswith('.bin'))
    frame = frames[int(sys.argv[3]) if len(sys.argv) > 3 else 0]
    for i, head, d, cbs in rs.draws(os.path.join(tag, frame)):
        if i != want:
            continue
        print('%s n=%d instances=%d start=%d' % (['DrawIndexed', 'Draw', 'DrawIndexedInstanced', 'DrawInstanced'][head[0]], head[1], head[2], head[3]))
        for stage in ('vs', 'ps'):
            sh = objs.shaders.get(d[stage])
            if not sh:
                continue
            e = index.get(sh[1], {})
            print('%s: %s[%s]  defines: %s' % (stage, e.get('shader', sh[1]).split('/shaders/')[-1], e.get('index', '?'),
                                               ' '.join('%s=%s' % tuple(x) for x in e.get('defines', []) if x) or '-'))
        for slot, view in enumerate(d['ps_srv']):
            t = objs.textures.get(objs.srv.get(view))
            if t:
                e = tex_index.get(t['hash'])
                print('  t%-2d %s %dx%d format %d' % (slot, e['path'] if e else ('render target' if not t['has'] else t['hash']), t['w'], t['h'], t['fmt']))
        st = objs.states.get(d['blend'])
        if st:
            b = st[1]
            en, src, dst, op, srca, dsta, opa = struct.unpack_from('<7I', b, 8)
            mask = b[36]
            print('blend: %s  color %s %s %s  alpha %s %s %s  write mask %#x' % ('on' if en else 'off', BLEND.get(src, src), OP.get(op, op), BLEND.get(dst, dst),
                                                                               BLEND.get(srca, srca), OP.get(opa, opa), BLEND.get(dsta, dsta), mask))
        st = objs.states.get(d['depth'])
        if st:
            den, dmask, dfunc, sen = struct.unpack_from('<4I', st[1], 0)
            print('depth: test %s  write %s  func %s  stencil %s' % ('on' if den else 'off', 'on' if dmask else 'off', CMP.get(dfunc, dfunc), 'on' if sen else 'off'))
        st = objs.states.get(d['raster'])
        if st:
            fill, cull, front, bias = struct.unpack_from('<IIIi', st[1], 0)
            clamp, slope = struct.unpack_from('<ff', st[1], 16)
            print('raster: %s cull %s  depth bias %d slope %.3f' % ({2: 'wireframe', 3: 'solid'}.get(fill, fill), {1: 'none', 2: 'front', 3: 'back'}.get(cull, cull), bias, slope))
        for stage in ('vs', 'ps'):
            sh = objs.shaders.get(d[stage])
            path = os.path.join(tag, 'shaders', sh[1] + '.dxbc') if sh else ''
            if not sh or not os.path.exists(path):
                continue
            buffers, slots = layout(disassemble(open(path, 'rb').read()))
            for name, fields in buffers.items():
                slot = slots.get(name)
                if slot is None:
                    continue
                obj = d[stage + '_cb'][slot]
                data = cbs.get(obj) or (objs.buffers.get(obj, {}).get('init'))
                print('%s cb%d %s%s' % (stage, slot, name, '' if data else '  (no data seen)'))
                if not data:
                    continue
                for var, typ, off, size, unused in fields:
                    if unused or var.startswith('BONES'):
                        continue
                    n = min(size, len(data) - off) // 4
                    if n <= 0:
                        continue
                    vals = struct.unpack_from('<%df' % n, data, off)
                    if n > 16:
                        vals = vals[:16]
                    rows = [' '.join('%.5g' % v for v in vals[k:k + 4]) for k in range(0, len(vals), 4)]
                    print('   %-34s %s' % (var, ('\n' + ' ' * 38).join(rows)))
        break


if __name__ == '__main__':
    main()
