import unittest

import code_coverage as C


class ByteCoverageTests(unittest.TestCase):
    def test_verified_trap_instruction_restores_false_padding(self):
        inventory = C.inventory([(0, 4), (5, 8)], {0: 8, 20: 3}, (0, 10))
        self.assertEqual(inventory, [(0, 8)])
        parts, rest = C.partition(inventory, [{0: 8}])
        self.assertEqual(C.length(parts[0]), 8)
        self.assertEqual(rest, [])

    def test_reader_crosses_false_index_boundary(self):
        parts, rest = C.partition([(0, 304), (304, 656), (656, 700)], [{0: 656}])
        self.assertEqual(parts, [[(0, 656)]])
        self.assertEqual(rest, [(656, 700)])
        self.assertEqual(C.entries_with_uncovered_bytes([(0, 304), (304, 656), (656, 700)], rest), 1)

    def test_short_match_keeps_unmatched_tail(self):
        parts, rest = C.partition([(0, 230)], [{0: 5}])
        self.assertEqual(parts, [[(0, 5)]])
        self.assertEqual(rest, [(5, 230)])
        self.assertEqual(C.entries_with_uncovered_bytes([(0, 230)], rest), 1)

    def test_unindexed_function_and_category_overlap(self):
        parts, rest = C.partition([(0, 100)], [{20: 30}, {35: 40}])
        self.assertEqual(parts, [[(20, 50)], [(50, 75)]])
        self.assertEqual(rest, [(0, 20), (75, 100)])
        self.assertEqual(sum(C.length(p) for p in parts) + C.length(rest), 100)

    def test_padding_and_outside_bytes_are_not_code(self):
        parts, rest = C.partition([(10, 20), (30, 50)], [{5: 30}])
        self.assertEqual(parts, [[(10, 20), (30, 35)]])
        self.assertEqual(rest, [(35, 50)])
        self.assertEqual(sum(C.length(p) for p in parts) + C.length(rest), 30)

    def test_nested_and_touching_ranges(self):
        parts, rest = C.partition([(0, 60)], [{0: 40, 10: 5, 40: 20}])
        self.assertEqual(parts, [[(0, 60)]])
        self.assertEqual(rest, [])


if __name__ == '__main__':
    unittest.main()
