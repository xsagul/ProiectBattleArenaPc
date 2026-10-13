import struct
import unittest
from historical_pdb import records,fieldlist


def record(kind,body):return struct.pack('<HH',len(body)+2,kind)+body


class HistoricalPdbReaderTests(unittest.TestCase):
    def test_truncated_records_are_rejected(self):
        for data in (b'\0',struct.pack('<HH',12,0x110e)+b'abc'):
            with self.subTest(data=data),self.assertRaises(ValueError):list(records(data))

    def test_field_padding_and_continuations_preserve_numeric_offsets(self):
        member=struct.pack('<HHIH',0x150d,3,0x40,0)+b'x\0'
        second=struct.pack('<HHIHI',0x150d,3,0x40,0x8004,0x10000)+b'large\0'
        main=record(0x1203,member+struct.pack('<HHI',0x1404,0,0x1001))
        tail=record(0x1203,second+b'\xf2\xf1')
        result=fieldlist({0x1000:(0x1203,main),0x1001:(0x1203,tail)},0x1000)
        self.assertEqual([(x['name'],x['offset']) for x in result],[('x',0),('large',0x10000)])

    def test_unknown_leaf_and_cyclic_continuation_cannot_claim_complete_fields(self):
        unknown=record(0x1203,struct.pack('<H',0x7777))
        cycle=record(0x1203,struct.pack('<HHI',0x1404,0,0x1000))
        for data in (unknown,cycle):
            with self.subTest(data=data),self.assertRaises(ValueError):fieldlist({0x1000:(0x1203,data)},0x1000)


if __name__=='__main__':unittest.main()
