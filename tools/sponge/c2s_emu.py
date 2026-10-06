"""Run the 13.3 client's own writer for a client-to-server packet in the emulator (packet_emu's machine).

  c2s_emu.py <ctor rva> <writer rva>     the wire bytes of a freshly constructed packet
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packet_emu as P


GETPTD = 0xf7f84c   # the CRT's per-thread data (rand() keeps its seed at +0x18): answered with a block of our own


def machine():
    from unicorn import UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
    e = P.Emu()
    ptd = e.alloc(0x400)

    def getptd(u, addr, size, data):
        esp = u.reg_read(UC_X86_REG_ESP)
        u.reg_write(UC_X86_REG_EAX, ptd)
        u.reg_write(UC_X86_REG_EIP, struct.unpack('<I', u.mem_read(esp, 4))[0])
        u.reg_write(UC_X86_REG_ESP, esp + 4)
    e.u.hook_add(UC_HOOK_CODE, getptd, begin=P.BASE + GETPTD, end=P.BASE + GETPTD)
    return e


def write(ctor, writer, size=0x200, patch=None, emu=None):
    e = emu or machine()
    obj = e.alloc(size)
    _, err = e.call(ctor, obj, [])
    if err:
        raise RuntimeError('ctor: ' + err)
    if patch:
        patch(e, obj)
    data = e.alloc(0x1000)
    buf = e.alloc(16)
    e.u.mem_write(buf, struct.pack('<III', data, 0, 0x1000))
    _, err = e.call(writer, obj, [buf])
    if err:
        raise RuntimeError('writer: ' + err)
    p, n, _ = struct.unpack('<III', e.u.mem_read(buf, 12))
    return bytes(e.u.mem_read(p, n)), obj, e


if __name__ == '__main__':
    out, obj, e = write(int(sys.argv[1], 16), int(sys.argv[2], 16))
    print(len(out), out.hex())
    print('object', bytes(e.u.mem_read(obj, 0x60)).hex())
