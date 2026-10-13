import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import search as S


class SearchGuards(unittest.TestCase):
    def test_body_boundary_ignores_literals_and_comments(self):
        source='{ const char* s="}"; /* } */ if (s) { } // }\n } tail'
        self.assertEqual(source[S.matching_brace(source,0)+1:],' tail')

    def test_reference_parameters_are_never_copied_into_lambda(self):
        source='C::C(const R& other) { value=other.value; }'
        case=dict(seed=source,body_span=(source.index('{'),source.rindex('}')),
            function=dict(member=True,constructor=True,parameters=[dict(name='other',capture='reference')],member_fields=['value']))
        rows=S.proposals(case)
        for row in rows[1:]:
            self.assertIn('&other',row['source'])
            self.assertNotIn('[this, other]',row['source'])

    def test_holdout_results_do_not_train_prior(self):
        history=S.History(':memory:')
        proposal=dict(name='lambda_value',family='lambda_capture')
        result=dict(exact=True,quality=1)
        history.store('holdout',dict(id='held',learning_use='evaluation_only'),proposal,'register',result)
        self.assertEqual(history.rank('register',proposal),0.5)
        history.store('train',dict(id='train',learning_use='training'),proposal,'register',result)
        self.assertGreater(history.rank('register',proposal),0.5)
        self.assertEqual(history.cached('holdout'),result)

    def test_same_bytes_with_wrong_target_are_not_success(self):
        S.BASE.joinpath('runs').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=S.BASE/'runs') as name:
            case=dict(symbol='test',rva=0x1000,expected_size=1,expected_targets={'callee':0x2000})
            with patch.object(S.M,'compile_obj',return_value='fixture.obj'), \
                 patch.object(S.M,'compare',return_value=('test',1,1,None,'')), \
                 patch.object(S.M,'function_of',return_value=('test',b'\xc3',set())), \
                 patch.object(S.M,'symbol_addresses',return_value=[('callee',0x3000)]):
                result=S.evaluate(case,dict(source='void test(){}'),pathlib.Path(name))
            self.assertFalse(result['exact'])
            self.assertEqual(result['failure_class'],'relocation_targets')

    def test_artifacts_cannot_be_written_to_production(self):
        with self.assertRaisesRegex(ValueError,'experimental directory'):
            S.run(S.BASE/'cases/owned_case.json',S.ROOT/'client-src/src',S.History(':memory:'))

    def test_expected_complete_extent_is_mandatory(self):
        self.assertEqual(S.classify(b'\xc3',b'\xc3\xc3',('leaf',1,1,None,''),True),'extent_mismatch')


if __name__=='__main__':unittest.main()
