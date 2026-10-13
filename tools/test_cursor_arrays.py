"""A reflected list descriptor does not prove a dynamic-buffer representation."""
import json
import types
import unittest
from unittest.mock import patch
import gen_cursor_arrays as C


class FixedCursorArrayTests(unittest.TestCase):
    def fixture(self):
        name='CursorDataCaptureCooldownContext'
        row=dict(name=name,member=dict(name='mData',element='CursorData',stride=56),
                 native_ctor=1,native_dtor=2,native_dtor_body='seven element destruction loop')
        image=types.SimpleNamespace(text=lambda _: 'seven element construction loop')
        analysis=types.SimpleNamespace(cls={7:name})
        fact=dict(size=392)
        return image,analysis,fact,row

    def test_element_extent_count_and_complete_methods_are_required(self):
        for case in ('count','stride','constructor','destructor'):
            im,a,f,row=self.fixture()
            if case=='count':f['size']=168
            if case=='stride':row['member']['stride']=12
            if case=='constructor':row['native_ctor']=None
            if case=='destructor':row['native_dtor']=None
            with self.subTest(case=case),patch.object(C.B,'candidate',return_value=row):
                self.assertIsNone(C.candidate(im,a,f,7))

    def test_changed_native_loop_cannot_reuse_saved_array_layout(self):
        im,a,f,row=self.fixture()
        with patch.object(C.B,'candidate',return_value=row):
            saved=C.candidate(im,a,f,7)
            serialized=json.dumps([saved])
            manifest=types.SimpleNamespace(exists=lambda:True,read_text=lambda **_:serialized)
            with patch.object(C,'MANIFEST',manifest):
                self.assertIn('[7]',C.layout_of(im,a,f,7)[0])
                row['native_dtor_body']='three element destruction loop'
                with self.assertRaises(ValueError):C.layout_of(im,a,f,7)


if __name__=='__main__':unittest.main()
