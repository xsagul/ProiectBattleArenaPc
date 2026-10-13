import struct, sys
import packet_emu16 as P
e = P.Emu()
writer, vt, pid = 0xecd9e0, 0x1a18190, 1032
obj = e.alloc(0x200)
e.u.mem_write(obj, struct.pack('<QHHI', P.BASE + vt, pid, 0, 0x400000ae))
data = e.alloc(0x1000); buf = e.alloc(32)
e.u.mem_write(buf, struct.pack('<QII', data, 0, 0x1000))
ret, err = e.call(writer, obj, [buf])
print('ret', ret, 'err', err)
p, n, cap = struct.unpack('<QII', e.u.mem_read(buf, 16))
print('out', n, bytes(e.u.mem_read(p, min(n, 80))).hex())
