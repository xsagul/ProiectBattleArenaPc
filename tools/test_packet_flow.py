from types import SimpleNamespace
import unittest
from unittest.mock import patch

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import gen_packet_multi as P


class PacketFlowTests(unittest.TestCase):
    def image(self, code, starts):
        return SimpleNamespace(img=bytes(code), starts=starts, md=Cs(CS_ARCH_X86, CS_MODE_32))

    def test_follow_branch_across_unnamed_index_entry(self):
        # jz 8; mov al,1; ret 8; int3; xor al,al; ret 8. Entry 8 is an internal failure block.
        im = self.image([0x74, 6, 0xb0, 1, 0xc2, 8, 0, 0xcc, 0x32, 0xc0, 0xc2, 8, 0, 0xcc], [0, 8, 14])
        with patch.object(P.M, 'known_names', return_value={0: {'Read'}, 14: {'Next'}}):
            ins = P.packet_instructions(im, 0)
        self.assertEqual(max(i.address + i.size for i in ins), 13)
        self.assertEqual([i.address for i in ins], [0, 2, 4, 8, 10])

    def test_calls_do_not_expand_the_body(self):
        im = self.image([0xe8, 0x20, 0, 0, 0, 0xc3, 0xcc], [0, 7])
        with patch.object(P.M, 'known_names', return_value={7: {'Next'}}):
            ins = P.packet_instructions(im, 0)
        self.assertEqual([i.address for i in ins], [0, 5])

    def test_conditional_branch_crossing_named_boundary_is_rejected(self):
        im = self.image([0x74, 6, 0xc3, 0xcc, 0xcc, 0xcc, 0xcc, 0xcc, 0xc3], [0, 8])
        with patch.object(P.M, 'known_names', return_value={8: {'Next'}}):
            self.assertIsNone(P.packet_instructions(im, 0))

    def test_loop_terminates_and_indirect_jump_is_unsupported(self):
        im = self.image([0x75, 0xfe, 0xc3], [0, 3])
        with patch.object(P.M, 'known_names', return_value={3: {'Next'}}):
            self.assertEqual([i.address for i in P.packet_instructions(im, 0)], [0, 2])
        im = self.image([0xff, 0xe0], [0, 2])
        with patch.object(P.M, 'known_names', return_value={2: {'Next'}}):
            self.assertIsNone(P.packet_instructions(im, 0))


if __name__ == '__main__':
    unittest.main()
