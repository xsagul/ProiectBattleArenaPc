"""COFF reader regressions: boundaries, relocation metadata and recompilation at the same object path.

Run with python -m unittest discover -s tools -p test_match_func.py.
The fixture uses one shared code section, an EH funclet, an external call and a read-only literal.
"""
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import match_func as M


def object_bytes(first_opcode=0xe8):
    code = bytes([first_opcode]) + b'\0' * 4 + b'\xb8' + b'\0' * 4 + b'\xc3\xc3\xc3'
    literal = b'yes\0'
    raw = 20 + 2 * 40
    reloc = raw + len(code) + len(literal)
    symptr = reloc + 2 * 10
    symbols = [('First', 0, 1, 0x20), ('FirstTwin', 12, 1, 0x20),
               ('__unwindfunclet$hidden', 11, 1, 0x20), ('_callee', 0, 0, 0x20), ('Literal', 0, 2, 0)]
    strings, records = bytearray(b'\0' * 4), bytearray()
    for name, value, section, kind in symbols:
        encoded = name.encode('ascii')
        if len(encoded) > 8:
            encoded = struct.pack('<II', 0, len(strings))
            strings.extend(name.encode('ascii') + b'\0')
        records.extend(encoded.ljust(8, b'\0') + struct.pack('<IhHBB', value, section, kind, 2, 0))
    struct.pack_into('<I', strings, 0, len(strings))
    header = struct.pack('<HHIIIHH', 0x14c, 2, 0, symptr, len(symbols), 0, 0)
    text = struct.pack('<8sIIIIIIHHI', b'.text', 0, 0, len(code), raw, reloc, 0, 2, 0, 0x60000020)
    data = struct.pack('<8sIIIIIIHHI', b'.rdata', 0, 0, len(literal), raw + len(code), 0, 0, 0, 0, 0x40001040)
    return header + text + data + code + literal + struct.pack('<IIHIIH', 1, 3, 0x14, 6, 4, 6) + records + strings


class StraightReturnTests(unittest.TestCase):
    BODY = bytes.fromhex('8b442404c70000000000c3')

    def test_consecutive_unindexed_function_is_not_a_reachable_tail(self):
        import packet_emu as P
        with patch.object(M, 'function_of', return_value=('Leaf', self.BODY, set())), \
                patch.object(M, 'starts', return_value=set()), \
                patch.object(M, 'wrong_targets', return_value=[]), \
                patch.object(P, 'IMG', self.BODY + bytes.fromhex('6898000000e800000000c3')):
            self.assertIsNone(M.compare('fixture.cpp', 'Leaf', 0, [], 'fixture.obj')[3])

    def test_branch_call_second_return_and_partial_instruction_rejected(self):
        for body in (bytes.fromhex('85c0740631c0c3'), bytes.fromhex('e800000000c3'),
                     self.BODY + self.BODY, self.BODY + b'\x8b'):
            with self.subTest(body=body):
                self.assertFalse(M.straight_return(body))

    def test_leaf_boundary_proof_still_requires_matching_bytes_and_targets(self):
        import packet_emu as P
        with patch.object(M, 'function_of', return_value=('Leaf', self.BODY, set())), \
                patch.object(M, 'starts', return_value=set()), \
                patch.object(P, 'IMG', self.BODY + bytes.fromhex('6898000000c3')), \
                patch.object(M, 'wrong_targets', return_value=[(5, 'ours', 'client')]):
            self.assertEqual(M.compare('fixture.cpp', 'Leaf', 0, [], 'fixture.obj')[3], 5)
        with patch.object(M, 'function_of', return_value=('Leaf', self.BODY, set())), \
                patch.object(P, 'IMG', self.BODY[:6] + b'\x01' + self.BODY[7:] + b'\x68' * 64):
            self.assertEqual(M.compare('fixture.cpp', 'Leaf', 0, [], 'fixture.obj')[3], 6)


class CoffReaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        M._coff_object.cache_clear()
        self.obj = Path(self.directory.name) / 'fixture.obj'
        self.obj.write_bytes(object_bytes())

    def test_exact_symbol_and_funclet_boundary(self):
        name, code, rel = M.function_of(str(self.obj), 'First')
        self.assertEqual(name, 'First')
        self.assertEqual(len(code), 11)  # the unselectable EH funclet still ends this function
        self.assertEqual(rel, {1, 2, 3, 4, 6, 7, 8, 9})
        with self.assertRaisesRegex(SystemExit, '2 functions contain'):
            M.function_of(str(self.obj), 'Fir')
        with self.assertRaisesRegex(SystemExit, '0 functions contain'):
            M.function_of(str(self.obj), '__unwindfunclet')
        with self.assertRaisesRegex(SystemExit, '0 functions contain'):
            M.function_of(str(self.obj), 'absent')

    def test_relocation_state_is_restored_for_each_selection(self):
        M.function_of(str(self.obj), 'First')
        self.assertEqual(M.TARGETS, {1: (0x14, '_callee'), 6: (6, 'Literal')})
        self.assertEqual(M.CONSTANTS, {6: b'yes\0'})
        M.function_of(str(self.obj), 'FirstTwin')
        self.assertEqual(M.TARGETS, {})
        self.assertEqual(M.CONSTANTS, {})
        M.function_of(str(self.obj), 'First')
        self.assertEqual(M.CONSTANTS, {6: b'yes\0'})

    def test_overwritten_object_with_same_length_invalidates_metadata(self):
        before = M.function_of(str(self.obj), 'First')
        modified = self.obj.stat().st_mtime_ns
        self.obj.write_bytes(object_bytes(first_opcode=0x90))
        os.utime(self.obj, ns=(modified + 1_000_000, modified + 1_000_000))
        after = M.function_of(str(self.obj), 'First')
        self.assertNotEqual(before[1], after[1])
        self.assertEqual(after[1][0], 0x90)

    def test_packet_table_labels_require_the_exact_cpp_class(self):
        self.assertTrue(M.same_thing('??_7C2S_Base@@6B@', {'C2S_Base_vtable'}))
        self.assertTrue(M.same_thing('??_7C2S_782@@6B@', {'C2S_782_vtable'}))
        self.assertFalse(M.same_thing('??_7C2S_781@@6B@', {'C2S_782_vtable'}))
        self.assertFalse(M.same_thing('??_7S2C_782@@6B@', {'C2S_782_vtable'}))
        self.assertFalse(M.same_thing('??_7Try_13ca80_0@@6B@', {'C2S_782_vtable'}))


if __name__ == '__main__':
    unittest.main()
