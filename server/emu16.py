"""Run the 16.20 client's own packet code on bytes of our choice (Unicorn, 64-bit), as packet_emu.py did for 13.3.

    emu16.py read <id> <hex wire bytes after the id>     create the packet object and run its reader
    emu16.py replay <file.rofl> [n]                      run the reader on the first n blocks (wire = a6 + body)

The image is a dump of the running client (data/exe1620/exe_image_t0.bin). The factory (rva 0xe678c0) makes the
object, vtable slot 1 is the reader: reader(object, &cursor, end) -> al. The allocator and free are replaced.
"""
import os, struct, sys
import unicorn
from unicorn import x86_const as X

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(HERE, '..', 'data', 'exe1620', 'exe_image_t0.bin')
FACTORY, ALLOC, FREE = 0xe678c0, 0x1125b70, 0x1125ba0
STACK, HEAP, EXIT, TEB = 0x7000_0000_0000, 0x6000_0000_0000, 0x7100_0000_0000, 0x7200_0000_0000
HEAP_SIZE = 0x400_0000


class Emu:
    def __init__(self, image=IMAGE):
        self.img = open(image, 'rb').read()
        self.base = int(open(image[:-4] + '_pages.txt').readline().split()[1], 16)
        mu = self.mu = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_64)
        size = (len(self.img) + 0xfff) & ~0xfff
        mu.mem_map(self.base, size)
        mu.mem_write(self.base, self.img)
        mu.mem_map(STACK, 0x100000)
        mu.mem_map(HEAP, HEAP_SIZE)
        mu.mem_map(EXIT, 0x1000)
        mu.mem_map(TEB, 0x10000)
        mu.reg_write(X.UC_X86_REG_GS_BASE, TEB)
        # thread-local storage: gs:[0x58] -> slot array -> one block for every slot; +0x150 is the epoch that
        # "initialise once" checks compare with their guard: a high value says everything is initialised already
        mu.mem_write(TEB + 0x58, struct.pack('<Q', TEB + 0x1000))
        mu.mem_write(TEB + 0x1000, struct.pack('<Q', TEB + 0x2000) * 128)
        mu.mem_write(TEB + 0x2000 + 0x150, struct.pack('<I', 0x7fffffff))
        self.heap = HEAP + 0x1000
        self.notes = []
        for rva, fn in ((ALLOC, self._alloc), (FREE, self._free)):
            mu.hook_add(unicorn.UC_HOOK_CODE, fn, begin=self.base + rva, end=self.base + rva)
        mu.hook_add(unicorn.UC_HOOK_MEM_UNMAPPED, self._unmapped)

    # replaced functions: answer and return to the caller
    def _ret(self, value):
        mu = self.mu
        sp = mu.reg_read(X.UC_X86_REG_RSP)
        mu.reg_write(X.UC_X86_REG_RAX, value)
        mu.reg_write(X.UC_X86_REG_RIP, struct.unpack('<Q', mu.mem_read(sp, 8))[0])
        mu.reg_write(X.UC_X86_REG_RSP, sp + 8)

    def _alloc(self, mu, addr, size, _):
        self._ret(self.alloc(mu.reg_read(X.UC_X86_REG_RCX)))

    def _free(self, mu, addr, size, _):
        self._ret(0)

    def _unmapped(self, mu, access, addr, size, value, _):
        self.notes.append(f'unmapped access {addr:#x} at rva {mu.reg_read(X.UC_X86_REG_RIP) - self.base:#x}')
        return False

    def alloc(self, n):
        p = self.heap
        self.heap += (n + 0x1f) & ~0xf
        assert self.heap < HEAP + HEAP_SIZE
        return p

    def put(self, data):
        p = self.alloc(len(data) + 16)
        self.mu.mem_write(p, bytes(data))
        return p

    def u64(self, a):
        return struct.unpack('<Q', self.mu.mem_read(a, 8))[0]

    def call(self, addr, *args, count=5_000_000):
        mu = self.mu
        sp = STACK + 0xf0000
        mu.mem_write(sp, struct.pack('<Q', EXIT))
        mu.reg_write(X.UC_X86_REG_RSP, sp)
        for reg, v in zip((X.UC_X86_REG_RCX, X.UC_X86_REG_RDX, X.UC_X86_REG_R8, X.UC_X86_REG_R9), args):
            mu.reg_write(reg, v)
        try:
            mu.emu_start(addr, EXIT, count=count)
        except unicorn.UcError as e:
            self.notes.append(f'{e} at rva {mu.reg_read(X.UC_X86_REG_RIP) - self.base:#x}')
            return None
        if mu.reg_read(X.UC_X86_REG_RIP) != EXIT:
            self.notes.append('instruction budget used up')
            return None
        return mu.reg_read(X.UC_X86_REG_RAX)

    def new_packet(self, pid):
        out = self.put(bytes(8))
        self.call(self.base + FACTORY, out, pid)
        return self.u64(out)

    def read_packet(self, pid, wire):
        """wire = the bytes after the packet id. -> (object address or 0, bytes consumed, reader's answer, object size guess)"""
        self.notes = []
        obj = self.new_packet(pid)
        if not obj:
            return 0, 0, None
        buf = self.put(wire)
        cur = self.put(struct.pack('<Q', buf))
        reader = self.u64(self.u64(obj) + 8)
        ans = self.call(reader, obj, cur, buf + len(wire))
        return obj, self.u64(cur) - buf, None if ans is None else ans & 0xff


def main():
    e = Emu()
    if sys.argv[1] == 'read':
        pid, wire = int(sys.argv[2]), bytes.fromhex(sys.argv[3])
        obj, used, ans = e.read_packet(pid, wire)
        print(f'id {pid}: object {obj:#x} consumed {used} of {len(wire)} answer {ans} {e.notes}')
        if obj:
            print(bytes(e.mu.mem_read(obj, 0x60)).hex())
    else:
        import rofl2
        r = rofl2.Rofl2(sys.argv[2])
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        good = bad = 0
        for k, (rec, (t, ch, pid, objid, body)) in enumerate(rofl2.stream(r, kinds=(3, 2, 1))):
            if k >= n:
                break
            wire = b'\xa6' + body
            obj, used, ans = e.read_packet(pid, wire)
            ok = ans == 1 and used == len(wire)
            good += ok
            bad += not ok
            if not ok or k < 6:
                print(f'{k:5} id {pid:5} netid {objid:08x} len {len(body):5}: consumed {used} answer {ans} {e.notes[:2]}')
        print(f'{good} read to the last byte, {bad} not')


if __name__ == '__main__':
    main()
