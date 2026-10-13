"""Ownership and authoritative-report restrictions for reflection callbacks."""
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import gen_meta_small as S

class CallbackOwnershipTests(unittest.TestCase):
    def test_only_byte_identical_metadata_dependencies_are_candidates(self):
        detail = 'same bytes, different targets:\n  +0x4: ours names ??$MetaConstruct@UExample@@@@YAPAXPAX@Z, the client has the rebuilt ?k1234@@ there'
        report = {'failures': [dict(source='MetaClasses.cpp', detail=detail),
                               dict(source='Unrelated.cpp', detail=detail),
                               dict(source='MetaClasses.cpp', detail=detail.replace('same bytes', 'different bytes'))]}
        self.assertEqual(S.dependencies(report), [('MetaConstruct', 'Example', 0x1234,
                                                 '??$MetaConstruct@UExample@@@@YAXPAX@Z')])

    def test_undefined_or_non_small_dependencies_are_not_invented(self):
        report = {'failures': [dict(source='MetaClasses.cpp', detail='same bytes, different targets:\n  ours names ??$MetaConstruct@UExample@@@@YAPAXPAX@Z, the client has unknown there')]}
        self.assertEqual(S.dependencies(report), [])

    def test_other_module_instances_prevent_odr_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            gen = pathlib.Path(directory)
            (gen / 'MetaFunctions.cpp').write_text('template void* MetaConstruct<Owned>(void*);\n', encoding='utf-8')
            own = gen / 'MetaSmallTemplates.cpp'
            own.write_text('template <> void* MetaConstruct<Local>(void* p) { return p; }\n', encoding='utf-8')
            with patch.object(S, 'GEN', gen), patch.object(S, 'OUT', own):
                self.assertEqual(S.existing_instances(), {('MetaConstruct', 'Owned')})

    def test_published_callbacks_survive_a_cleaner_future_report(self):
        with tempfile.TemporaryDirectory() as directory:
            own = pathlib.Path(directory) / 'MetaSmallTemplates.cpp'
            own.write_text('// same: ecb40 ??$MetaDestruct@UExample@@@@YAXPAX@Z\n', encoding='utf-8')
            with patch.object(S, 'OUT', own):
                self.assertEqual(S.published_callbacks(), [('MetaDestruct', 'Example', 0xecb40,
                                                          '??$MetaDestruct@UExample@@@@YAXPAX@Z')])

if __name__ == '__main__':
    unittest.main()
