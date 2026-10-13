"""The Summoner's Rift navigation grid (levels/map11/aipath.aimesh_ngrid in Map11LEVELS.wad.client): which ground
a unit can stand on, and a path finder over it. Format: version 7 (see tools/third_party/LeagueSandbox-GameServer,
GameServerLib/Content/Navigation): header, 48-byte cell records, then one u16 of flags per cell and one u32 region tag.

  navgrid.py           what the grid looks like (size, share of blocked cells)
"""
import heapq
import math
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
WAD = os.path.join(ROOT, 'game', 'DATA', 'FINAL', 'Maps', 'Shipping', 'Map11LEVELS.wad.client')
CACHE = os.path.join(ROOT, 'data', 'exe133', 'map11.ngrid')
if os.environ.get('BA_PATCH') == '1620':
    # 16.20: the grid is in Map11.wad.client under 11 entries (the base map and the dragon-soul terrain variants);
    # the base one = the blocked-cell mask 7 of them share (entry 0xdb3d762553b6ad9), saved here
    CACHE = os.path.join(ROOT, 'data', 'exe1620', 'map11.ngrid')
PATH_IN_WAD = b'levels/map11/aipath.aimesh_ngrid'
HAS_GRASS, NOT_PASSABLE, SEE_THROUGH = 0x1, 0x2, 0x40
_grid = None


def _extract():
    if os.path.exists(CACHE):
        return open(CACHE, 'rb').read()
    import xxhash
    import zstandard
    d = open(WAD, 'rb').read()
    want = xxhash.xxh64(PATH_IN_WAD).intdigest()
    for i in range(struct.unpack_from('<I', d, 0x10c)[0]):
        h, off, csize, usize, kind = struct.unpack_from('<QIIIB', d, 0x110 + i * 32)
        if h == want:
            raw = d[off:off + csize]
            data = zstandard.ZstdDecompressor().decompress(raw, max_output_size=usize) if kind == 3 else raw
            with open(CACHE, 'wb') as f:
                f.write(data)
            return data
    raise FileNotFoundError('aipath.aimesh_ngrid is not in ' + WAD)


class Grid:
    def __init__(self, data):
        if data[0] != 7:
            raise ValueError(f'navigation grid version {data[0]}, only 7 is read')
        self.min_x, _, self.min_z = struct.unpack_from('<3f', data, 3)
        self.max_x, _, self.max_z = struct.unpack_from('<3f', data, 15)
        self.size, self.nx, self.nz = struct.unpack_from('<fII', data, 27)
        n = self.nx * self.nz
        at = 39 + 48 * n
        self.flags = struct.unpack_from(f'<{n}H', data, at)
        self.blocked = bytearray(1 if f & NOT_PASSABLE else 0 for f in self.flags)
        # what stops sight: a wall cell that is not marked 'see through' (the structures' footprints, pit edges)
        self.opaque = bytearray(1 if (f & NOT_PASSABLE) and not (f & SEE_THROUGH) else 0 for f in self.flags)
        self._brush = None
        self.data = data

    def cell(self, x, z):
        cx, cz = int((x - self.min_x) // self.size), int((z - self.min_z) // self.size)
        return cx, cz

    def height(self, x, z):
        """the ground's height there: the first float of the cell's record (lane 53.7, river -70, fountain 183.6:
        the heights Riot's server writes into its casts at those places in the replay)"""
        cx, cz = self.cell(x, z)
        cx, cz = max(0, min(self.nx - 1, cx)), max(0, min(self.nz - 1, cz))
        return struct.unpack_from('<f', self.data, 39 + 48 * (cz * self.nx + cx))[0]

    def is_blocked(self, x, z):
        cx, cz = self.cell(x, z)
        if not (0 <= cx < self.nx and 0 <= cz < self.nz):
            return True
        return bool(self.blocked[cz * self.nx + cx])

    def line_clear(self, a, b, step=None):
        """no blocked cell on the straight line a -> b (sampled every half cell)"""
        step = step or self.size / 2
        d = math.dist(a, b)
        n = max(1, int(d / step))
        for i in range(n + 1):
            f = i / n
            if self.is_blocked(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f):
                return False
        return True

    def sight_clear(self, ax, az, bx, bz):
        """nothing that stops sight strictly between two places (sampled every 0.6 cell)"""
        dx, dz = bx - ax, bz - az
        n = int(max(abs(dx), abs(dz)) / 30.0) + 1
        inv = 1.0 / self.size
        x, z = (ax - self.min_x) * inv, (az - self.min_z) * inv
        sx, sz = dx * inv / n, dz * inv / n
        op, nx, nz = self.opaque, self.nx, self.nz
        for i in range(1, n):
            cx, cz = int(x + sx * i), int(z + sz * i)
            if 0 <= cx < nx and 0 <= cz < nz and op[cz * nx + cx]:
                return False
        return True

    def brush(self):
        """a number per cell: the patch of brush it is part of (0 = open ground); grass cells that touch, also by a
        corner, are one patch"""
        if self._brush is None:
            nx, nz, flags = self.nx, self.nz, self.flags
            label = [0] * (nx * nz)
            count = 0
            for start in range(nx * nz):
                if not (flags[start] & HAS_GRASS) or label[start]:
                    continue
                count += 1
                label[start] = count
                todo = [start]
                while todo:
                    c = todo.pop()
                    cx, cz = c % nx, c // nx
                    for ox in (-1, 0, 1):
                        for oz in (-1, 0, 1):
                            px, pz = cx + ox, cz + oz
                            if 0 <= px < nx and 0 <= pz < nz:
                                k = pz * nx + px
                                if (flags[k] & HAS_GRASS) and not label[k]:
                                    label[k] = count
                                    todo.append(k)
            self._brush = label
            self.brush_patches = count
        return self._brush

    def nearest_free(self, x, z, limit=12):
        """the free cell centre nearest to a point (rings of cells around it)"""
        cx, cz = self.cell(x, z)
        for r in range(limit + 1):
            best = None
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    if max(abs(dx), abs(dz)) != r:
                        continue
                    px, pz = cx + dx, cz + dz
                    if 0 <= px < self.nx and 0 <= pz < self.nz and not self.blocked[pz * self.nx + px]:
                        c = (self.min_x + (px + 0.5) * self.size, self.min_z + (pz + 0.5) * self.size)
                        d = math.dist(c, (x, z))
                        if best is None or d < best[0]:
                            best = (d, c)
            if best:
                return best[1]
        return None

    def path(self, a, b):
        """A* over the cells (8 neighbours, no corner cutting, the distance to go weighted 1.2 so the search stays
        narrow), then string pulling: the corners that remain are the points a unit walks through in straight lines.
        None when there is no way. Paths between the same coarse places are remembered."""
        a, b = self.nearest_free(*a), self.nearest_free(*b)
        if a is None or b is None:
            return None
        if self.line_clear(a, b):
            return [a, b]
        s, g = self.cell(*a), self.cell(*b)
        key = (s, g)
        memo = self.__dict__.setdefault('_memo', {})
        cells = memo.get(key)
        if cells is None:
            cells = self._search(s, g)
            if len(memo) > 4000:
                memo.clear()
            memo[key] = cells
        if cells is None:
            return None
        pts = [a] + [(self.min_x + (c % self.nx + 0.5) * self.size, self.min_z + (c // self.nx + 0.5) * self.size)
                     for c in cells[1:-1]] + [b]
        out, i = [pts[0]], 0
        n = len(pts)
        while i < n - 1:
            # the farthest point in a straight clear line: tried from far to near in halving steps
            j = n - 1
            lo = i + 1
            while j > lo and not self.line_clear(pts[i], pts[j]):
                j = lo + (j - lo) // 2 if j - lo > 8 else j - 1
            out.append(pts[j])
            i = j
        return out

    def _search(self, s, g):
        nx, nz, blocked = self.nx, self.nz, self.blocked
        start, goal = s[1] * nx + s[0], g[1] * nx + g[0]
        if start == goal:
            return [start, goal]
        gx, gz = g
        INF = 1e18
        best = {start: 0.0}
        came = {}
        heap = [(0.0, start)]
        push, pop = heapq.heappush, heapq.heappop
        steps = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142))
        closed = set()
        while heap:
            _, cur = pop(heap)
            if cur == goal:
                break
            if cur in closed:
                continue
            closed.add(cur)
            cx, cz = cur % nx, cur // nx
            bc = best[cur]
            for dx, dz, w in steps:
                px, pz = cx + dx, cz + dz
                if px < 0 or pz < 0 or px >= nx or pz >= nz:
                    continue
                p = pz * nx + px
                if blocked[p] or p in closed:
                    continue
                if dx and dz and (blocked[cz * nx + px] or blocked[pz * nx + cx]):
                    continue
                c = bc + w
                if c < best.get(p, INF):
                    best[p] = c
                    came[p] = cur
                    ddx, ddz = gx - px, gz - pz
                    if ddx < 0:
                        ddx = -ddx
                    if ddz < 0:
                        ddz = -ddz
                    h = (ddx + ddz) - 0.5858 * (ddx if ddx < ddz else ddz)        # octile distance
                    push(heap, (c + 1.2 * h, p))
        if goal not in came:
            return None
        cells = [goal]
        while cells[-1] != start:
            cells.append(came[cells[-1]])
        cells.reverse()
        return cells


def grid():
    global _grid
    if _grid is None:
        _grid = Grid(_extract())
    return _grid


if __name__ == '__main__':
    g = grid()
    print(f'{g.nx} x {g.nz} cells of {g.size}, x {g.min_x:.0f}..{g.max_x:.0f}, z {g.min_z:.0f}..{g.max_z:.0f}; '
          f'{sum(g.blocked)} of {len(g.blocked)} cells not passable')
