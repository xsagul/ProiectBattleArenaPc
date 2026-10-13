"""Reject string ownership inferred from overlapping or incomplete metadata."""
import json
import types
import unittest
from unittest.mock import patch
import gen_reflected_lifetimes as L
import gen_reflected_colors as C


class LifetimeEvidenceTests(unittest.TestCase):
    def fixture(self):
        fact=dict(parent=None,poly=False,align=4,size=36,destroy=3,destruct=4)
        events=[('call',9,7,[('imm',10+i),('imm',12*i),('imm',0)]) for i in range(3)]
        analysis=types.SimpleNamespace(cls={7:'StringElements'},names={},followed={7:events})
        image=types.SimpleNamespace(text=lambda rva:f'body-{rva}')
        return image,analysis,fact

    def test_overlapping_strings_unknown_tail_and_indirection_are_rejected(self):
        for case in ('overlap','tail','pointer','no-string'):
            im,a,f=self.fixture();wrapper=(0x10,0)
            if case=='overlap':a.followed[7][1][3][1]=('imm',8)
            if case=='tail':f['size']=40
            if case=='pointer':wrapper=(0x10,1)
            if case=='no-string':wrapper=(7,0)
            with self.subTest(case=case),patch('gen_meta.member_wrapper',return_value=wrapper):
                self.assertIsNone(L.candidate(im,a,f,7))

    def test_changed_release_target_cannot_reuse_saved_lifetime_layout(self):
        im,a,f=self.fixture()
        with patch('gen_meta.member_wrapper',return_value=(0x10,0)):
            row=L.candidate(im,a,f,7)
            manifest=types.SimpleNamespace(exists=lambda:True,read_text=lambda **_:json.dumps([row]))
            with patch.object(L,'MANIFEST',manifest):
                self.assertEqual(len(L.layout_of(im,a,f,7)),3)
                im.text=lambda _: 'release to another allocator'
                with self.assertRaises(ValueError):L.layout_of(im,a,f,7)

    def test_unexplained_byte_gap_is_not_compiler_alignment(self):
        im,a,f=self.fixture();f['size']=16
        a.followed[7]=[('call',9,7,[('imm',10),('imm',0),('imm',0)]),
                       ('call',8,7,[('imm',11),('imm',13),('imm',0)])]
        with patch('gen_meta.member_wrapper',side_effect=lambda _,wrapper:(0x10,0) if wrapper==9 else (3,0)):
            self.assertIsNone(L.candidate(im,a,f,7))

    def test_color_constructor_requires_native_rounding_and_exact_globals(self):
        row=dict(size=20,native_ctor=C.RVA,member=dict(element='UiHashLink'))
        for text in (C.EXPECTED_TEXT.replace('cvtss2si','cvttss2si'),
                     C.EXPECTED_TEXT.replace('0x153f9e0','0x153f9e4')):
            image=types.SimpleNamespace(text=lambda _,text=text:text)
            with self.assertRaises(ValueError):C.helper_declaration(image,C.NAMES[0],row)


if __name__=='__main__':unittest.main()
