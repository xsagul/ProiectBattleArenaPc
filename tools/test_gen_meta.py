"""Conservative extraction of initialization stores from placement constructors."""
import unittest
import types
from unittest.mock import patch

from gen_meta import constant_construct, constant_members, zero_construct, create_stores, hash_pair_layout
import packet_emu as P


class TextImage:
    def __init__(self, body):
        self.body = body
        self.img = bytes(32)

    def text(self, rva):
        return self.body


class HashPairLayoutTests(unittest.TestCase):
    def fixture(self):
        bodies = {
            1: 'push esi\nmov esi, dword ptr [esp + 8]\nmov ecx, esi\ncall 0x9ba240\n'
               'lea ecx, [esi + 0xc]\npop esi\njmp 0x9ba240',
            0x9ba240: 'mov dword ptr [ecx], 0\nmov eax, ecx\nmov dword ptr [ecx + 4], 0\n'
                      'mov dword ptr [ecx + 8], 0x7fffffff\nret'}
        im = types.SimpleNamespace(text=lambda rva: bodies[rva])
        events = [('call',2,7,[('imm',10),('imm',0),('imm',0)]),
                  ('call',2,7,[('imm',11),('imm',12),('imm',0)])]
        a = types.SimpleNamespace(followed={7:events},names={10:'First',11:'Second'})
        f = dict(parent=None,poly=False,align=4,size=24,construct=1)
        return im,a,f,bodies

    def test_native_key_storage_requires_complete_ctor_and_reflection_evidence(self):
        with patch('gen_meta.member_wrapper',return_value=(0x11,0)):
            im,a,f,bodies=self.fixture()
            fields=hash_pair_layout(im,a,f,7)
            self.assertIn('UiHashKey First;',fields[0])
            self.assertIn('UiHashKey Second;',fields[1])
            for key,value in [('parent',8),('poly',True),('size',20),('align',8)]:
                im,a,f,bodies=self.fixture();f[key]=value
                self.assertIsNone(hash_pair_layout(im,a,f,7))
            im,a,f,bodies=self.fixture();a.followed[7][1][3][1]=('imm',4)
            self.assertIsNone(hash_pair_layout(im,a,f,7))
            im,a,f,bodies=self.fixture();a.followed[7][1][3][0]=('ret',11)
            self.assertIsNone(hash_pair_layout(im,a,f,7))
            for rva in (1,0x9ba240):
                im,a,f,bodies=self.fixture();bodies[rva]=bodies[rva].replace('0x9ba240','0x9ba244').replace('0x7fffffff','0')
                self.assertIsNone(hash_pair_layout(im,a,f,7))

    def test_other_reflected_member_type_cannot_claim_native_hash_storage(self):
        im,a,f,_=self.fixture()
        with patch('gen_meta.member_wrapper',return_value=(7,0)):
            self.assertIsNone(hash_pair_layout(im,a,f,7))


class StringCreateTests(unittest.TestCase):
    def image(self, address='0x1b467f0'):
        return TextImage('\n'.join(['push 0x10', 'call 0x9bb8d0', 'add esp, 4', 'test eax, eax',
                                  'je 0x1234', f'mov ecx, dword ptr [{address}]',
                                  'mov dword ptr [eax], ecx', 'mov dword ptr [eax + 4], 0',
                                  'mov dword ptr [eax + 8], 0', 'mov dword ptr [eax + 0xc], 0',
                                  'ret', 'xor eax, eax', 'ret']))

    def test_runtime_empty_string_pointer_stays_a_dependency(self):
        stores = create_stores(self.image(), 0x1000)
        self.assertNotIn(0, stores)
        self.assertEqual(stores, dict.fromkeys(range(4, 16), 0))

    def test_other_runtime_global_is_not_a_string_default(self):
        self.assertIsNone(create_stores(self.image('0x1b467f4'), 0x1000))


class ZeroConstructTests(unittest.TestCase):
    def extract(self, body, size=80):
        return zero_construct(TextImage('\n'.join(body)), 0x1000, size)

    def test_partial_block_preserves_uncleared_tail(self):
        self.assertEqual(self.extract([
            'mov eax, dword ptr [esp + 4]', 'xorps xmm0, xmm0',
            'movups xmmword ptr [eax], xmm0', 'movups xmmword ptr [eax + 0x10], xmm0',
            'movq qword ptr [eax + 0x20], xmm0', 'ret']), ('block', 40))

    def test_scalar_members_remain_distinct_from_block(self):
        body = ['mov eax, dword ptr [esp + 4]']
        body += ['mov dword ptr [eax], 0']
        body += [f'mov dword ptr [eax + {off:#x}], 0' for off in range(4, 28, 4)]
        body += ['ret']
        self.assertEqual(self.extract(body, 28), ('members', 28))
        self.assertIsNone(self.extract(body, 24))

    def test_index_tail_after_return_is_not_part_of_constructor(self):
        self.assertEqual(self.extract([
            'mov eax, dword ptr [esp + 4]', 'mov dword ptr [eax], 0', 'ret',
            'push 0x98', 'call 0x1234', 'ret']), ('members', 4))

    def test_side_effects_holes_overlaps_and_nonzero_stores_are_rejected(self):
        for stores in ([
                'call 0x1234'], [
                'mov dword ptr [eax + 4], 0'], [
                'mov dword ptr [eax], 0', 'mov dword ptr [eax], 0'], [
                'mov dword ptr [eax], 1'], [
                'movq qword ptr [eax], xmm0']):
            with self.subTest(stores=stores):
                self.assertIsNone(self.extract(['mov eax, dword ptr [esp + 4]', *stores, 'ret']))


class ConstantConstructTests(unittest.TestCase):
    def extract(self, body, size=16):
        return constant_construct(TextImage('\n'.join([
            'mov eax, dword ptr [esp + 4]', *body, 'ret'])), 0x1000, size)

    def test_mixed_widths_and_padding_preserve_unwritten_bytes(self):
        self.assertEqual(self.extract([
            'xor ecx, ecx', 'mov dword ptr [eax], 0xffffffff',
            'mov word ptr [eax + 4], cx', 'mov byte ptr [eax + 8], 5']),
            [(0, 4, 0xffffffff), (4, 2, 0), (8, 1, 5)])

    def test_unknown_registers_addresses_overlaps_and_bounds_rejected(self):
        for body in ([
                'mov word ptr [eax], cx'], [
                'xor ecx, ecx', 'mov word ptr [eax], ecx'], [
                f'mov dword ptr [eax], {P.BASE + 8:#x}'], [
                'mov dword ptr [eax], 0', 'mov word ptr [eax + 2], 0'], [
                'mov dword ptr [eax + 0xe], 0'], [
                'mov dword ptr [eax], 0x100000000'], [
                'call 0x1234']):
            with self.subTest(body=body):
                self.assertIsNone(self.extract(body))

    def test_one_byte_alignment_does_not_round_up_three_byte_object(self):
        fields = constant_members([(0, 2, 0x101), (2, 1, 0)], 3, 1)
        self.assertEqual(len(fields), 3)
        self.assertTrue(all('u8 ' in field for field in fields))
        self.assertFalse(any('[' in field for field in fields))

    def test_native_constructor_stores_agree_with_placement_constructor(self):
        native = TextImage('\n'.join([
            'mov dword ptr [ecx], 0', 'mov eax, ecx',
            'mov dword ptr [ecx + 4], 5', 'ret']))
        self.assertEqual(constant_construct(native, 0x1000, 8, member=True),
                         self.extract(['mov dword ptr [eax], 0',
                                       'mov dword ptr [eax + 4], 5'], 8))
        native.body = 'xor ecx, ecx\nmov eax, ecx\nmov dword ptr [ecx], 0\nret'
        self.assertIsNone(constant_construct(native, 0x1000, 8, member=True))

    def test_mixed_vector_scalar_initializer_keeps_gaps(self):
        image = TextImage('\n'.join([
            'mov eax, dword ptr [esp + 4]', 'xor ecx, ecx', 'xorps xmm0, xmm0',
            'movups xmmword ptr [eax], xmm0', 'mov byte ptr [eax + 0x10], 0',
            'mov word ptr [eax + 0x12], cx', 'mov dword ptr [eax + 0x14], 0xffffffff', 'ret']))
        self.assertIsNone(constant_construct(image, 0x1000, 24))
        self.assertEqual(constant_construct(image, 0x1000, 24, sse=True),
                         [(0, 16, 0), (16, 1, 0), (18, 2, 0), (20, 4, 0xffffffff)])
        image.body = image.body.replace('xorps xmm0, xmm0\n', '')
        self.assertIsNone(constant_construct(image, 0x1000, 24, sse=True))

    def test_vector3_grouping_preserves_twelve_initialized_bytes(self):
        image = TextImage('\n'.join([
            'mov eax, dword ptr [esp + 4]', 'xorps xmm0, xmm0', 'xor ecx, ecx',
            'movq qword ptr [eax], xmm0', 'mov dword ptr [eax + 8], 0', 'ret']))
        stores = constant_construct(image, 0x1000, 16, sse=True)
        self.assertEqual(stores, [(0, 12, 0)])
        self.assertEqual(constant_members(stores, 16, 4),
                         ['    ::Vector3 unknown00 = {};', '    u8 unknown0c[0x4];'])


if __name__ == '__main__':
    unittest.main()
