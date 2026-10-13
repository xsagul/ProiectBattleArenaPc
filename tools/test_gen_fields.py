"""The source-order alternatives must preserve every possible encoded byte."""
import unittest

import gen_fields as F


def evaluate(chain, value):
    for op, operand in chain:
        if op in ('xor', 'xor2', 'not'):
            value ^= 255 if op == 'not' else operand
        elif op in ('rev', 'swap', 'rol', 'ror'):
            bits = [(value >> k) & 1 for k in range(8)]
            if op == 'rev':
                bits.reverse()
            elif op == 'swap':
                bits = [bits[k ^ operand] for k in range(8)]
            else:
                shift = operand if op == 'rol' else -operand
                bits = [bits[(k - shift) % 8] for k in range(8)]
            value = sum(bit << k for k, bit in enumerate(bits))
        elif op == 'add':
            value = (value + operand) & 255
        else:
            raise AssertionError(op)
    return value


class EquivalentBitChainTests(unittest.TestCase):
    def test_promoted_reverse_matches_bit_definition_for_every_byte(self):
        for value in range(256):
            product = (((value * 0x0802 & 0x22110) | (value * 0x8020 & 0x88440)) * 0x10101) & 0xffffffff
            self.assertEqual((product >> 16) & 255, int(f'{value:08b}'[::-1], 2))

    def test_high_byte_register_preserves_low_byte_and_pointer(self):
        trace, out = F.run(['mov dl, byte ptr [ecx]', 'mov dh, 1', 'xor dl, 0x5a',
                            'mov byte ptr [eax], dl'], b'', 0x93, {}, {'ecx': F.CURSOR, 'eax': F.OUT})
        self.assertEqual(out, 0xc9)
        self.assertEqual(trace[-1]['edx'], 0x1c9)
        self.assertEqual(trace[-1]['eax'], F.OUT)
        steps = F.chain_of(['mov dl, byte ptr [ecx]', 'mov dh, 1', 'xor dl, 0x5a',
                            'mov byte ptr [eax], dl'], b'', {}, {'ecx': F.CURSOR, 'eax': F.OUT})
        self.assertEqual(steps, [('xor', 0x5a)])

    def test_source_order_regressions(self):
        self.assertIn([('swap', 1), ('xor', 8)], F.equivalent_bit_chains([('xor', 4), ('swap', 1)]))
        self.assertIn([('rev', 0), ('xor', 128)], F.equivalent_bit_chains([('xor', 1), ('rev', 0)]))
        self.assertIn([('ror', 3), ('xor', 32)], F.equivalent_bit_chains([('xor', 1), ('ror', 3)]))

    def test_all_bytes_in_both_directions(self):
        permutations = [('rev', 0), ('swap', 1), ('swap', 2)]
        permutations += [(op, k) for op in ('rol', 'ror') for k in range(1, 8)]
        for permutation in permutations:
            for bias in range(256):
                for original in ([('xor', bias), permutation], [permutation, ('xor', bias)]):
                    reference = [evaluate(original, value) for value in range(256)]
                    for variant in F.equivalent_bit_chains(original):
                        self.assertEqual(reference, [evaluate(variant, value) for value in range(256)])

    def test_composed_chains_and_complements(self):
        chains = [[('not', 0), ('rev', 0), ('swap', 2), ('ror', 3)],
                  [('xor2', 255), ('rol', 2), ('swap', 1), ('xor', 19), ('rev', 0)],
                  [('xor', 4), ('add', 47), ('swap', 1)]]
        for original in chains:
            reference = [evaluate(original, value) for value in range(256)]
            for variant in F.equivalent_bit_chains(original):
                self.assertEqual(reference, [evaluate(variant, value) for value in range(256)])


if __name__ == '__main__':
    unittest.main()
