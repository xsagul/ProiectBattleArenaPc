"""Only complete, metadata-backed default-string stores can become member initialization."""
import unittest
from gen_meta_ctors import member_initializers,thin_base_inline_prefix,exact_base_call
from unittest.mock import patch


class StringMemberInitializers(unittest.TestCase):
    body = ('    *(int*)(((int)this + 16)) = *(int*)((int)&g_1b467f0);\n'
            '    *(int*)(((int)this + 20)) = 0;\n'
            '    *(int*)(((int)this + 24)) = 0;\n')
    info = {'Child': {'parent': 'Base', 'strings': []},
            'Base': {'parent': None, 'strings': [16]}}

    def test_inherited_real_string_member_supplies_all_three_stores(self):
        self.assertEqual(member_initializers(self.body, 'Child', self.info), '')

    def test_missing_default_store_retains_explicit_body(self):
        body = self.body.replace('+ 24)) = 0', '+ 24)) = 1')
        self.assertEqual(member_initializers(body, 'Child', self.info), body)

    def test_opaque_storage_does_not_imply_a_string_lifetime(self):
        self.assertEqual(member_initializers(self.body, 'Opaque', {}), self.body)


class InlinedThinBaseTests(unittest.TestCase):
    def test_typed_base_call_requires_this_correct_type_and_proven_no_args(self):
        line='    (int)(new ((void*)(int)this) Base);'
        with patch('gen_small.NATIVE_CALLS',{0x10:('Base','Base',0,'BinClasses.h')}):
            self.assertTrue(exact_base_call(line,0x10,'Base'))
            self.assertFalse(exact_base_call(line.replace('(int)this','(int)this + 4'),0x10,'Base'))
            self.assertFalse(exact_base_call(line.replace('Base);','Base(1));'),0x10,'Base'))
            self.assertFalse(exact_base_call(line,0x10,'Other'))
            self.assertFalse(exact_base_call(line,0x11,'Base'))
        with patch('gen_small.NATIVE_CALLS',{0x10:('Base','Base',1,'BinClasses.h')}):
            self.assertFalse(exact_base_call(line,0x10,'Base'))

    def test_inlined_ancestor_can_replace_a_base_that_only_sets_vptr(self):
        prefix='    *(int*)(((int)this + 4)) = 0;\n'
        own='    *(int*)((int)this) = (int)&g_1234;\n'
        info={'Thin':dict(parent='Ancestor',rva=0x20),'Ancestor':dict(parent=None,rva=0x10)}
        bodies={0x10:dict(body=prefix),0x20:dict(body='    ((K10*)(int)this)->f();\n'+own)}
        self.assertEqual(thin_base_inline_prefix(prefix+own,'Thin',info,bodies),(own,0x10))
        bodies[0x20]['body']+='    *(int*)(((int)this + 8)) = 1;\n'
        self.assertIsNone(thin_base_inline_prefix(prefix+own,'Thin',info,bodies))

    def test_flattened_parent_requires_only_ancestor_prefix_and_one_vptr_store(self):
        prefix='    *(int*)(((int)this + 4)) = 0;\n'
        vptr='    *(int*)((int)this) = (int)&g_1234;\n'
        info={'Thin':dict(parent='Ancestor',rva=0x20),'Ancestor':dict(parent=None,rva=0x10)}
        bodies={0x10:dict(body=prefix),0x20:dict(body=prefix+vptr)}
        self.assertEqual(thin_base_inline_prefix(prefix+vptr,'Thin',info,bodies),(vptr,0x10))
        bodies[0x20]['body']+='    *(int*)(((int)this + 8)) = 1;\n'
        self.assertIsNone(thin_base_inline_prefix(prefix+vptr,'Thin',info,bodies))


if __name__ == '__main__':
    unittest.main()
