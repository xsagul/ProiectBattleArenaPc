"""A serialized list tag cannot alone establish a twelve-byte native owner."""
import json
import types
import unittest
from unittest.mock import patch
import gen_reflected_buffers as B


class ReflectedBufferEvidenceTests(unittest.TestCase):
    def fixture(self):
        fact=dict(parent=None,poly=False,align=4,size=12,create=1,construct=2,destroy=3,destruct=4)
        event=('call',9,7,[('imm',10),('imm',0),('imm',0)])
        analysis=types.SimpleNamespace(cls={7:'ProvedList'},names={10:'Values'},followed={7:[event]})
        bodies={rva:f'complete-body-{rva}' for rva in range(1,5)}
        image=types.SimpleNamespace(text=lambda rva:bodies[rva])
        descriptor=dict(code=0x80,slot=5,of=None,stores={4:(1,0xa),8:(4,4)})
        return image,analysis,fact,descriptor,bodies

    def test_missing_callback_and_incompatible_runtime_extent_are_rejected(self):
        for key,value in [('parent',8),('poly',True),('align',8),('size',8),('destroy',0)]:
            image,analysis,fact,descriptor,_=self.fixture();fact[key]=value
            with self.subTest(key=key),patch('gen_meta.container_wrapper',return_value=descriptor):
                self.assertIsNone(B.candidate(image,analysis,fact,7))

    def test_element_size_reference_kind_and_member_offset_need_evidence(self):
        for case in ('stride','of','map','offset','two-members'):
            image,analysis,fact,descriptor,_=self.fixture()
            if case=='stride':descriptor['stores'][8]=(4,8)
            if case=='of':descriptor['of']=('imm',0x1234)
            if case=='map':descriptor['code']=0x86
            if case=='offset':analysis.followed[7][0][3][1]=('imm',4)
            if case=='two-members':analysis.followed[7].append(analysis.followed[7][0])
            with self.subTest(case=case),patch('gen_meta.container_wrapper',return_value=descriptor):
                self.assertIsNone(B.candidate(image,analysis,fact,7))

    def test_changed_destructor_cannot_reuse_a_previously_proved_layout(self):
        image,analysis,fact,descriptor,bodies=self.fixture()
        with patch('gen_meta.container_wrapper',return_value=descriptor):
            saved=B.candidate(image,analysis,fact,7)
            manifest=types.SimpleNamespace(exists=lambda:True,read_text=lambda **_:json.dumps([saved]))
            with patch.object(B,'MANIFEST',manifest):
                self.assertIn('ReflectedBuffer<float> Values;',B.layout_of(image,analysis,fact,7)[0])
                bodies[4]='a different ownership condition or cleanup target'
                with self.assertRaises(ValueError):B.layout_of(image,analysis,fact,7)


if __name__=='__main__':unittest.main()
