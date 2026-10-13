import json
import types
import unittest
from unittest.mock import patch
import gen_vfx_runtime as V


class VfxRuntimeGuardTests(unittest.TestCase):
    def test_native_helper_global_and_pointer_pointee_drift_are_rejected(self):
        fact=lambda size:dict(size=size,align=4,parent=None,poly=False,create=1,construct=2,destroy=3,destruct=4,v2=0)
        facts={7:fact(16),8:fact(8)}
        a=types.SimpleNamespace(cls={7:'ValueVector3',8:'FlexTypeFloat'},unique={'ValueVector3','FlexTypeFloat'},names={},
            followed={7:[('call',11,7,[('imm',1),('imm',0),('imm',0)]),('call',12,7,[('imm',2),('imm',12),('imm',0)])],
                      8:[('call',13,8,[('imm',3),('imm',0),('imm',0)]),('call',14,8,[('imm',4),('imm',4),('imm',0)])]},
            member_type=lambda code,*_: {11:'Vector3',12:'MetaPointer<VfxAnimatedVector3fVariableData>',13:'u32',14:'float'}[code])
        class Image:
            text=lambda self,rva:f'body-{rva}'
            class Memory:
                changed=False
                def __getitem__(self,slice_):return (b'\1' if self.changed else b'\0')*12
            img=Memory()
        im=Image()
        with patch('gen_meta.member_wrapper',side_effect=lambda _,rva:(rva,0)),patch('gen_meta.container_wrapper',return_value=None), \
             patch('gen_meta.class_facts',return_value=facts):
            saved=[V.metadata(im,a,f,g) for g,f in facts.items()]
            manifest=types.SimpleNamespace(exists=lambda:True,read_text=lambda:json.dumps(saved))
            with patch.object(V,'MANIFEST',manifest):
                self.assertIsNotNone(V.layout_of(im,a,facts[7],7))
                im.text=lambda rva:'changed allocator' if rva==0xa681b0 else f'body-{rva}'
                with self.assertRaises(ValueError):V.layout_of(im,a,facts[7],7)
                im.text=lambda rva:f'body-{rva}';im.img.changed=True
                with self.assertRaises(ValueError):V.layout_of(im,a,facts[7],7)
                im.img.changed=False;a.member_type=lambda *_:'float'
                with self.assertRaises(ValueError):V.layout_of(im,a,facts[7],7)

    def test_matching_prefix_and_wrong_delete_target_are_insufficient(self):
        for length,targets in ((78,[]),(79,[('??3@YAXPAXI@Z',0x999)])):
            with self.subTest(length=length),patch.object(V.M,'rebuilt_symbols',return_value={}), \
                 patch.object(V.M,'compile_obj',return_value='obj'), \
                 patch.object(V.M,'compare',return_value=('dtor',length,length,None,'')), \
                 patch.object(V.M,'function_of',return_value=('dtor',b'code',[])), \
                 patch.object(V.M,'symbol_addresses',return_value=targets),self.assertRaises(ValueError):
                V.verify(None,['probe.cpp'],None)


if __name__=='__main__':unittest.main()
