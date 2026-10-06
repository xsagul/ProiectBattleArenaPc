"""Reads what the GPU sponge (tools/sponge/d3d11_proxy.c) recorded: research/sponge/<tag>/objects.bin + frame_*.bin.

  python tools/sponge/read_sponge.py <tag dir> [summary | draws <frame> [from] [count] | cb <frame> <draw> | textures]

Each draw comes with the exact bytes of the constant buffers bound to it at that moment (the last Map / Update before
the draw), so the shader's inputs are known number for number.
"""
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, '..', '..', 'research', 'sponge', 'shader_index_133.json')
TEX_INDEX = os.path.join(HERE, '..', '..', 'research', 'sponge', 'texture_index_133.json')

REC_SHADER, REC_TEX2D, REC_BUFFER, REC_BLEND, REC_DEPTH, REC_RASTER, REC_SAMPLER, REC_LAYOUT, REC_SRV = range(1, 10)
REC_FRAME, REC_WRITE, REC_DRAW, REC_TOPOLOGY, REC_TARGETS, REC_CLEAR, REC_RTV = 20, 21, 22, 23, 24, 25, 10
STAGES = ['vs', 'ps', 'gs', 'hs', 'ds', 'cs']


def records(path):
    data = open(path, 'rb').read()
    at = 0
    while at + 8 <= len(data):
        t, n = struct.unpack_from('<II', data, at)
        if at + 8 + n > len(data):
            break  # the file was copied while the game was still writing it
        yield t, data[at + 8:at + 8 + n]
        at += 8 + n


class Objects:
    def __init__(self, path):
        self.shaders, self.textures, self.buffers, self.srv, self.states, self.layouts, self.views = {}, {}, {}, {}, {}, {}, {}
        for t, b in records(path):
            if t == REC_SHADER:
                obj, stage, h, size = struct.unpack_from('<IIQI', b)
                self.shaders[obj] = (STAGES[stage], '%016x' % h, size)
            elif t == REC_TEX2D:
                obj = struct.unpack_from('<I', b)[0]
                w, h, mips, arr, fmt = struct.unpack_from('<5I', b, 4)
                usage, bind = struct.unpack_from('<II', b, 4 + 28)
                has = struct.unpack_from('<I', b, 48)[0]
                hsh, nbytes = struct.unpack_from('<QI', b, 56)
                self.textures[obj] = dict(w=w, h=h, mips=mips, fmt=fmt, usage=usage, bind=bind, has=has, hash='%016x' % hsh, bytes=nbytes)
            elif t == REC_BUFFER:
                obj, width, usage, bind, cpu, misc, stride, has = struct.unpack_from('<8I', b)
                self.buffers[obj] = dict(width=width, usage=usage, bind=bind, stride=stride, init=b[40:] if len(b) > 40 else None)
            elif t == REC_RTV:
                view, res, kind = struct.unpack_from('<3I', b)
                self.views[view] = (res, kind)
            elif t == REC_SRV:
                view, res, fmt, dim = struct.unpack_from('<4I', b)
                self.srv[view] = res
            elif t in (REC_BLEND, REC_DEPTH, REC_RASTER, REC_SAMPLER):
                obj = struct.unpack_from('<I', b)[0]
                self.states[obj] = (t, b[4:])
            elif t == REC_LAYOUT:
                obj, n = struct.unpack_from('<II', b)
                els = []
                for i in range(n):
                    o = 8 + i * 56
                    sem = b[o:o + 32].split(b'\0')[0].decode()
                    idx, fmt, slot, off, cls, step = struct.unpack_from('<6I', b, o + 32)
                    els.append((sem, idx, fmt, slot, off))
                self.layouts[obj] = els


# Bound (d3d11_proxy.c), 32-bit pointers: 8 ptrs, 4 u32, vs_cb[14], ps_cb[14], ps_srv[16], vs_srv[8], ps_samp[16], vb[8],
# vb_stride[8], vb_offset[8], blend_factor[4], viewport(6 floats)
BOUND = struct.Struct('<8I4I14I14I16I8I16I8I8I8I4f6f')


def draws(path):
    """(draw index, draw head, bound dict, {cb object: bytes at that moment}) for each draw of a frame."""
    content = {}
    n = 0
    for t, b in records(path):
        if t == REC_WRITE:
            res, off, size = struct.unpack_from('<III', b)
            cur = bytearray(content.get(res, b''))
            if len(cur) < off + size:
                cur.extend(b'\0' * (off + size - len(cur)))
            cur[off:off + size] = b[12:12 + size]
            content[res] = bytes(cur)
        elif t == REC_DRAW:
            head = struct.unpack_from('<6I', b)
            v = BOUND.unpack_from(b, 24)
            d = dict(vs=v[0], ps=v[1], gs=v[2], layout=v[3], blend=v[4], depth=v[5], raster=v[6], ib=v[7], ib_format=v[8], topology=v[10],
                     vs_cb=v[12:26], ps_cb=v[26:40], ps_srv=v[40:56], vs_srv=v[56:64], ps_samp=v[64:80], vb=v[80:88], vb_stride=v[88:96],
                     viewport=v[124:130])
            yield n, head, d, {c: content.get(c) for c in set(d['vs_cb'] + d['ps_cb']) if c}
            n += 1


def main():
    tag = sys.argv[1]
    cmd = sys.argv[2] if len(sys.argv) > 2 else 'summary'
    objs = Objects(os.path.join(tag, 'objects.bin'))
    index = json.load(open(INDEX)) if os.path.exists(INDEX) else {}
    tex_index = json.load(open(TEX_INDEX)) if os.path.exists(TEX_INDEX) else {}

    def tex_name(view):
        t = objs.textures.get(objs.srv.get(view))
        if not t:
            return '?'
        e = tex_index.get(t['hash'])
        if e:
            return e['path'].split('/')[-1] + ('' if e['mip'] == 0 else '@mip%d' % e['mip'])
        return '%dx%d:%s' % (t['w'], t['h'], t['hash'][:8]) if t['has'] else 'rt%dx%d' % (t['w'], t['h'])

    def shader_name(obj):
        if obj not in objs.shaders:
            return '-' if not obj else '?%x' % obj
        stage, h, _ = objs.shaders[obj]
        e = index.get(h)
        if not e:
            return '%s:%s' % (stage, h)
        name = e['shader'].split('/shaders/')[-1]
        return '%s[%d]' % (name, e['index'])

    frames = sorted(f for f in os.listdir(tag) if f.startswith('frame_'))
    if cmd == 'summary':
        print('%d shaders, %d textures, %d buffers, %d views, %d states' % (len(objs.shaders), len(objs.textures), len(objs.buffers), len(objs.srv),
                                                                              len(objs.states)))
        for f in frames[:1]:
            pairs = collections.Counter()
            nd = 0
            for i, head, d, cbs in draws(os.path.join(tag, f)):
                nd += 1
                pairs[(shader_name(d['vs']), shader_name(d['ps']))] += 1
            print(f, nd, 'draws')
            for (vs, ps), c in pairs.most_common(60):
                print('  %5d  %-55s %s' % (c, vs, ps))
    elif cmd == 'passes':
        # render target changes and clears, with the draws in between grouped by shader pair
        f = os.path.join(tag, frames[int(sys.argv[3]) if len(sys.argv) > 3 else 0])
        content = {}
        group = collections.Counter()
        def flush():
            for (vs, ps), c in group.items():
                print('      %4d x %-50s %s' % (c, vs, ps))
            group.clear()
        def tex_name(view):
            res, kind = objs.views.get(view, (0, 0))
            t = objs.textures.get(res)
            return ('%dx%d f%d' % (t['w'], t['h'], t['fmt'])) if t else ('swapchain?' if view else '-')
        for t, b in records(f):
            if t == REC_TARGETS:
                flush()
                v = struct.unpack_from('<10I', b)
                print('targets:', ', '.join(tex_name(x) for x in v[1:1 + v[0]]), '| depth', tex_name(v[9]) if v[9] else '-')
            elif t == REC_CLEAR:
                view, kind = struct.unpack_from('<II', b)
                print('   clear', 'color' if kind == 0 else 'depth', tex_name(view), struct.unpack_from('<4f', b, 8) if kind == 0 else struct.unpack_from('<f', b, 8))
            elif t == REC_DRAW:
                v = BOUND.unpack_from(b, 24)
                group[(shader_name(v[0]), shader_name(v[1]))] += 1
        flush()
    elif cmd == 'draws':
        f = frames[int(sys.argv[3])]
        start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        count = int(sys.argv[5]) if len(sys.argv) > 5 else 50
        for i, head, d, cbs in draws(os.path.join(tag, f)):
            if i < start:
                continue
            if i >= start + count:
                break
            tex = [tex_name(s) for s in d['ps_srv'] if s]
            print('%5d %s n=%d inst=%d  vs %s  ps %s  tex %s' % (i, ['DrawIndexed', 'Draw', 'DrawIndexedInst', 'DrawInst'][head[0]], head[1], head[2],
                                                               shader_name(d['vs']), shader_name(d['ps']), ' '.join(tex)))
    elif cmd == 'cb':
        f = frames[int(sys.argv[3])]
        want = int(sys.argv[4])
        for i, head, d, cbs in draws(os.path.join(tag, f)):
            if i != want:
                continue
            print('vs', shader_name(d['vs']), 'ps', shader_name(d['ps']))
            for stage in ('vs_cb', 'ps_cb'):
                for slot, c in enumerate(d[stage]):
                    if not c:
                        continue
                    data = cbs.get(c) or (objs.buffers.get(c, {}).get('init'))
                    if not data:
                        print(stage, slot, 'no data seen')
                        continue
                    fl = struct.unpack_from('<%df' % (len(data) // 4), data)
                    print('%s b%d (%d bytes):' % (stage, slot, len(data)))
                    for r in range(0, min(len(fl), 4 * 64), 4):
                        print('   c%-3d %s' % (r // 4, ' '.join('%11.5f' % x for x in fl[r:r + 4])))
            break


if __name__ == '__main__':
    main()
