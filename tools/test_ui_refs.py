"""Reject UI layouts without the exact native callback and reflected-member evidence."""
import types
import unittest
import gen_ui_refs as U

class UiLayoutTests(unittest.TestCase):
    def fixture(self):
        row=U.load_layouts()['AbilityPrompt'];g=1
        fact=dict(size=60,align=4,poly=False,parent=None,destruct=0x576830)
        events=[('call',9,g,[('imm',U.field_hash(m['name'])),('imm',int(m['offset'],16)),('imm',0)]) for m in row['members']]
        a=types.SimpleNamespace(cls={g:'AbilityPrompt'},unique={'AbilityPrompt'},facts={g:fact},followed={g:events},wrapper_type=lambda _: 'HashValue')
        im=types.SimpleNamespace(text=lambda _:U.callback_text(2))
        return im,a,fact,g

    def test_unproved_type_is_not_extended(self):
        im,a,f,g=self.fixture();a.cls[g]='UnknownType'
        self.assertIsNone(U.layout_of(im,a,f,g))

    def test_exact_members_and_tail_are_preserved(self):
        im,a,f,g=self.fixture();body=U.layout_of(im,a,f,g)
        self.assertEqual(len(body),3)
        self.assertIn('UiHashLink AnimLink;',body[0])
        self.assertIn('UiHashLink TextLink;',body[1])
        self.assertIn('unknown30[0xc]',body[2])

    def test_wrong_metadata_or_extent_is_rejected(self):
        for property,value in (('size',64),('align',8),('poly',True),('destruct',0x576390)):
            im,a,f,g=self.fixture();f[property]=value
            with self.subTest(property=property),self.assertRaises(ValueError):
                U.layout_of(im,a,f,g)

    def test_reflected_hash_and_callback_targets_must_match(self):
        im,a,f,g=self.fixture();a.followed[g][0][3][0]=('imm',0)
        with self.assertRaises(ValueError):U.layout_of(im,a,f,g)
        im,a,f,g=self.fixture();im.text=lambda _ :U.callback_text(2).replace('0xae14d0','0xae17c0')
        with self.assertRaises(ValueError):U.layout_of(im,a,f,g)

    def test_tail_padding_is_not_zero_filled(self):
        text = ('mov byte ptr [edi + 0x30], 0\n'
                'mov dword ptr [edi + 0x34], 0\nmov dword ptr [edi + 0x38], 0')
        stores = U.constructor_tail_stores(text, 0x30, 0x3c)
        written = {off+i for off,width,_ in stores for i in range(width)}
        self.assertTrue({0x31,0x32,0x33}.isdisjoint(written))
        self.assertEqual(len(written),9)

    def test_invalid_tail_stores_are_rejected(self):
        cases = ['mov dword ptr [edi + 0x2f], 0',
                 'mov dword ptr [edi + 0x39], 0',
                 'mov word ptr [edi + 0x30], 0\nmov byte ptr [edi + 0x31], 0',
                 'mov byte ptr [edi + 0x30], 0x100']
        for text in cases:
            with self.subTest(text=text),self.assertRaises(ValueError):
                U.constructor_tail_stores(text,0x30,0x3c)

if __name__=='__main__':unittest.main()
