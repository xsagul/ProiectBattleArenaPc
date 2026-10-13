"""Which client the learners work on: BA_PATCH=1620 -> packet_emu16 (64-bit, 16.20), else packet_emu (13.3).
Both modules offer the same names: Emu, table, packets, plain_fields, BASE, BUF, HEAP, RES, ROFL, and the small
helpers that hide the register differences (ip, retval, getbits_call, fn_of, WIRE_SKIP, PTR, GETBITS*)."""
import importlib
import os

P = importlib.import_module('packet_emu16' if os.environ.get('BA_PATCH', '133').replace('.', '') == '1620' else 'packet_emu')
