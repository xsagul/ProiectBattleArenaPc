"""The format condition can be reused as a value only while its byte is unchanged."""
import unittest
import gen_packet_scalars as S

class FormatConstantTests(unittest.TestCase):
    def test_equal_format_survives_pointer_setup(self):
        self.assertEqual(S.constant_store(['lea edx, [ecx + 0xa]', 'lea esi, [edx + 1]',
                                          'mov byte ptr [edx], al'], 1, 1), 1)

    def test_format_value_requires_proved_condition(self):
        self.assertIsNone(S.constant_store(['mov byte ptr [esi], al'], 1))

    def test_format_clobber_is_rejected(self):
        for instruction in ('mov al, cl', 'mov ax, 7', 'lea eax, [esi + 1]',
                            'xor eax, eax', 'call 0x123456', 'pop eax', 'mul ecx'):
            with self.subTest(instruction=instruction):
                self.assertIsNone(S.constant_store([instruction, 'mov byte ptr [esi], al'], 1, 1))

    def test_immediate_constant_is_independent_of_format(self):
        self.assertEqual(S.constant_store(['mov byte ptr [esi], 0xff'], 1, 1), 255)
        self.assertEqual(S.constant_store(['mov dword ptr [esi], 0xffffffff'], 4, 1), 0xffffffff)

if __name__ == '__main__':
    unittest.main()
