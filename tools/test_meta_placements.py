"""Reject metadata drift and short prefixes in native placement closures."""
import copy
import json
import types
import unittest
from unittest.mock import patch
import gen_meta_placements as P


class PlacementEvidenceTests(unittest.TestCase):
    def test_saved_layout_rejects_changed_size_member_offset_and_native_body(self):
        facts=dict(size=40,align=4,parent=None,poly=False,create=1,construct=2,
                   destroy=3,destruct=4,v2=0)
        analysis=types.SimpleNamespace(cls={7:'CollectiblesEsportsTeamData'},
                                      followed={7:[('call',9,7,[('imm',4)])]})
        image=types.SimpleNamespace(text=lambda rva:f'body-{rva}')
        with patch('gen_meta.container_wrapper',return_value=None),patch('gen_meta.member_wrapper',return_value=(16,0)):
            row=P.evidence(image,analysis,facts,7)
            manifest=types.SimpleNamespace(exists=lambda:True,read_text=lambda:json.dumps([row]))
            with patch.object(P,'MANIFEST',manifest):
                self.assertIsNotNone(P.layout_of(image,analysis,facts,7))
                for kind in ('size','offset','body','native-helper'):
                    im,a,f=copy.deepcopy((image,analysis,facts))
                    if kind=='size':f['size']=44
                    if kind=='offset':a.followed[7][0][3][0]=('imm',8)
                    if kind=='body':im.text=lambda rva:'changed target'
                    if kind=='native-helper':im.text=lambda rva:'changed registry' if rva==0x63c7c0 else f'body-{rva}'
                    with self.subTest(kind=kind),self.assertRaises(ValueError):
                        P.layout_of(im,a,f,7)

    def test_identical_prefix_is_insufficient_and_wrong_target_is_rejected(self):
        for length,targets in ((8,[]),(9,[('vptr',123)])):
            with self.subTest(length=length),patch.object(P.M,'compile_obj',return_value='obj'), \
                 patch.object(P.M,'compare',return_value=('ctor',length,length,None,'')), \
                 patch.object(P.M,'function_of',return_value=('ctor',b'code',[])), \
                 patch.object(P.M,'symbol_addresses',return_value=targets),self.assertRaises(ValueError):
                P.check('candidate.cpp','ctor',0xa21cf0,{'vptr':456})


if __name__=='__main__':unittest.main()
