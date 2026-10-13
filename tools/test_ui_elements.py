import json
import types
import unittest
from unittest.mock import patch
import gen_ui_elements as U


class UiElementProofTests(unittest.TestCase):
    def test_matching_prefix_and_wrong_target_cannot_publish(self):
        for length, targets in ((110, []), (111, [('??2@YAPAXI@Z', 0x999)])):
            with self.subTest(length=length), patch.object(U.M, 'rebuilt_symbols', return_value={}), \
                 patch.object(U.M, 'compile_obj', return_value='obj'), \
                 patch.object(U.M, 'compare', return_value=('ctor', length, length, None, '')), \
                 patch.object(U.M, 'function_of', return_value=('ctor', b'code', [])), \
                 patch.object(U.M, 'symbol_addresses', return_value=targets), self.assertRaises(ValueError):
                U.verify([types.SimpleNamespace(name='probe.cpp')])

    def test_external_release_body_and_default_global_drift_are_rejected(self):
        fact = dict(size=4, align=4, parent=None, poly=True, create=0, construct=0, destroy=1, destruct=2, v2=3)
        a = types.SimpleNamespace(cls={7:'AnchorBase'}, unique={'AnchorBase'}, followed={}, names={})
        class Memory:
            changed = False
            def __getitem__(self, section):
                return (b'\1' if self.changed else b'\0') * (section.stop-section.start)
        im = types.SimpleNamespace(text=lambda rva:f'body-{rva}', img=Memory())
        saved = U.metadata(im, a, fact, 7)
        manifest = types.SimpleNamespace(exists=lambda:True, read_text=lambda **_:json.dumps([saved]))
        with patch.object(U, 'MANIFEST', manifest):
            self.assertEqual(U.layout_of(im, a, fact, 7), [])
            im.text = lambda rva:'different release' if rva==0xaaa4c0 else f'body-{rva}'
            with self.assertRaises(ValueError):
                U.layout_of(im, a, fact, 7)
            im.text = lambda rva:f'body-{rva}'
            im.img.changed = True
            with self.assertRaises(ValueError):
                U.layout_of(im, a, fact, 7)


if __name__ == '__main__':
    unittest.main()
