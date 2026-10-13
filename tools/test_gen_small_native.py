"""Known destructor ABIs must not turn EAX leftovers or local cleanup into arguments."""
import struct
import unittest

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import gen_small as S


class TinyImage:
    def __init__(self, code):
        self.md = Cs(CS_ARCH_X86, CS_MODE_32)
        self.md.detail = True
        self.img = bytearray(0x2000)
        self.img[0x1000:0x1000 + len(code)] = code
        self.end = 0x1000 + len(code)
        self.named = {0xae14d0: {'canonical destructor'}}
        self.rebuilt = {}

    def code(self, rva):
        return list(self.md.disasm(self.img[rva:self.end], rva))

    def convention(self, rva):
        raise AssertionError('The measured native ABI must take precedence.')


def call(at):
    return b'\xe8' + struct.pack('<i', 0xae14d0 - (at + 5))


class NativeDestructorTests(unittest.TestCase):
    def test_owned_string_constructor_consumes_typed_pointer_argument(self):
        prefix=bytes.fromhex('ff7424088b4c2408')
        code=prefix+b'\xe8'+struct.pack('<i',0x9b78e0-0x100d)+b'\xc3'
        f=S.Lifter(TinyImage(code),0x1000).run()
        self.assertEqual([len(s[4]) for s in f.stmts if s[0]=='call'],[1])
        self.assertEqual(f.ret[0][0],'call')
        signatures={0x1000:S.signature(f,'int'),0x9b78e0:S.callee_signature(0x9b78e0,True,4,'thiscall')}
        rendered=S.render(dict(lifted={0x1000:f},sigs=signatures,users={}),0x1000,{})
        self.assertIsNotNone(rendered)
        self.assertIn('MetaString((const char*)a1)', '\n'.join(rendered['lines']))

    def test_native_constructor_call_uses_placement_pointer_as_eax_result(self):
        code = b'\x8b\x4c\x24\x04\xe8' + struct.pack('<i', 0x5894b0-0x1009) + b'\xc3'
        f = S.Lifter(TinyImage(code),0x1000).run()
        self.assertEqual(f.ret[0][0],'call')
        signatures={0x1000:S.signature(f,'int'),
                    0x5894b0:S.callee_signature(0x5894b0,True,0,'thiscall')}
        context=dict(lifted={0x1000:f},sigs=signatures,users={})
        rendered=S.render(context,0x1000,{})
        self.assertIsNotNone(rendered)
        self.assertIn('(int)(new ((void*)a0) UiHashLinkTriple)', '\n'.join(rendered['lines']))

    def test_copy_constructor_uses_real_const_reference(self):
        prefix=bytes.fromhex('ff7424088b4c2408')
        code=prefix+b'\xe8'+struct.pack('<i',0x9b7840-0x100d)+b'\xc3'
        f=S.Lifter(TinyImage(code),0x1000).run()
        sigs={0x1000:S.signature(f,'int'),0x9b7840:S.callee_signature(0x9b7840,True,4,'thiscall')}
        rendered=S.render(dict(lifted={0x1000:f},sigs=sigs,users={}),0x1000,{})
        self.assertIsNotNone(rendered)
        self.assertIn('MetaString(*(const MetaString*)a1)', '\n'.join(rendered['lines']))

    def test_direct_call_does_not_return_eax_leftovers(self):
        f = S.Lifter(TinyImage(b'\x8b\x4c\x24\x04' + call(0x1004) + b'\xc2\x04\x00'), 0x1000).run()
        self.assertIsNone(f.ret)
        self.assertEqual([len(s[4]) for s in f.stmts if s[0] == 'call'], [0])

    def test_tail_call_returns_void(self):
        code = b'\x83\xc1\x0c\xe9' + struct.pack('<i', 0xae14d0 - 0x1008)
        f = S.Lifter(TinyImage(code), 0x1000).run()
        self.assertIsNotNone(f.tail)
        self.assertIsNone(f.ret)
        self.assertEqual(S.signature(f, 'int')['ret'], 'void')

    def test_pop_ecx_after_call_restores_local_without_adding_argument(self):
        code = b'\x51\x8b\x4c\x24\x08' + call(0x1005) + b'\x59\xc2\x04\x00'
        f = S.Lifter(TinyImage(code), 0x1000).run()
        self.assertEqual([len(s[4]) for s in f.stmts if s[0] == 'call'], [0])
        self.assertIsNone(f.ret)

    def test_store_of_clobbered_eax_cannot_be_rendered_as_cpp(self):
        code = b'\x8b\x4c\x24\x04' + call(0x1004) + b'\x8b\x54\x24\x04\x89\x02\xc2\x04\x00'
        f = S.Lifter(TinyImage(code), 0x1000).run()
        sigs = {0x1000: S.signature(f, 'int'),
                0xae14d0: S.callee_signature(0xae14d0, True, 0, 'thiscall')}
        analysis = dict(lifted={0x1000: f}, sigs=sigs, users={})
        self.assertIsNone(S.render(analysis, 0x1000, {}))


if __name__ == '__main__':
    unittest.main()
