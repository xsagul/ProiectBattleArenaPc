"""Verify the MSVC bound callable's complete bodies, relocation targets and vtable.

The argument remains opaque: matching its reference ABI does not establish its
canonical type or const qualification. This verifier does not claim the bound
method or its original caller as reconstructed source.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import match_func as M
from gen_sources import Image


ROOT = Path(__file__).resolve().parent.parent
EXPECTED = {
    '?_Copy@': (0x2f2780, 35),
    '?_Move@': (0x2f2780, 35),
    '?_Do_call@': (0x2f2a00, 10),
    '?_Target_type@': (0x125630, 5),
    '?_Delete_this@': (0x2f27b0, 21),
    '?_Get@': (0x10aa40, 4),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def vtable_slots(obj, symbol):
    """Read the actual COFF data and symbol relocations, including addends."""
    data = Path(obj).read_bytes()
    symptr, nsym = struct.unpack_from('<II', data, 8)
    strings = symptr + 18 * nsym

    def name(record):
        if record[:4] == b'\0' * 4:
            pos = strings + struct.unpack_from('<I', record, 4)[0]
            return data[pos:data.index(b'\0', pos)].decode()
        return record[:8].rstrip(b'\0').decode()

    records = {}
    index = 0
    while index < nsym:
        record = data[symptr + 18 * index:symptr + 18 * index + 18]
        records[name(record)] = struct.unpack_from('<IhHBB', record, 8)
        index += 1 + record[17]
    require(symbol in records, 'COFF vtable symbol missing')
    value, section, _, _, _ = records[symbol]
    require(section > 0, 'COFF vtable has no data definition')
    header = 20 + struct.unpack_from('<H', data, 16)[0] + 40 * (section - 1)
    size, raw, relptr = struct.unpack_from('<III', data, header + 16)
    count = struct.unpack_from('<H', data, header + 32)[0]
    require(size - value == 24 and count == 6, 'COFF vtable must have six pointers')
    result = {}
    for index in range(count):
        offset, target, kind = struct.unpack_from('<IIH', data, relptr + 10 * index)
        require(kind == 6 and value <= offset < value + 24 and
                (offset - value) % 4 == 0, 'Unexpected COFF vtable relocation')
        slot = (offset - value) // 4
        require(slot not in result, 'Duplicate COFF vtable relocation')
        require(struct.unpack_from('<I', data, raw + offset)[0] == 0,
                'Nonzero COFF vtable relocation addend')
        result[slot] = name(data[symptr + 18 * target:symptr + 18 * target + 18])
    return result


def verify(manifest_path=None):
    manifest_path = Path(manifest_path or ROOT / 'tools/bound_callback_layouts.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(manifest['schema_version'] == 1, 'Unknown manifest schema')
    source = ROOT / manifest['source']
    flags = M.file_flags(str(source))
    require(flags == manifest['flags'], 'Compiler flag drift')
    image = Image()
    obj = M.compile_obj(str(source), flags)
    require(len(manifest['functions']) == len(EXPECTED), 'Function list drift')
    rows = []
    for expected, proof in zip(EXPECTED.items(), manifest['functions']):
        prefix, (rva, size) = expected
        symbol = proof['symbol']
        require(symbol.startswith(prefix) and int(proof['rva'], 16) == rva and
                proof['size'] == size, 'Function identity or full-size drift')
        native = bytes(image.img[rva:rva + size])
        require(hashlib.sha256(native).hexdigest() == proof['native_sha256'],
                f'Native body fingerprint drift at {rva:x}')
        result = M.compare(str(source), symbol, rva, flags, obj=obj)
        require(result[1] == size and result[2] == size and result[3] is None,
                f'Complete body mismatch at {rva:x}: {result[1:4]}\n{result[4]}')
        _, code, _ = M.function_of(obj, symbol)
        targets = [(name, hex(address)) for name, address in
                   M.symbol_addresses(rva, code[:size])]
        require(targets == [tuple(item) for item in proof['symbol_addresses']],
                f'Explicit relocation target mismatch at {rva:x}')
        require(not M.wrong_targets(rva, code[:size]),
                f'Known relocation target mismatch at {rva:x}')
        rows.append({'rva': hex(rva), 'size': size, 'symbol': symbol,
                     'all_bytes_and_targets_identical': True})

    table = manifest['vtable']
    require(int(table['rva'], 16) == 0x157adfc and table['size'] == 24,
            'Native vtable identity drift')
    require(len(table['slots']) == 6, 'Manifest vtable slot count drift')
    slots = vtable_slots(obj, table['symbol'])
    for index, proof in enumerate(table['slots']):
        require(proof['slot'] == index and slots[index] == rows[index]['symbol'] ==
                proof['symbol'], f'COFF vtable slot {index} mismatch')
        native = struct.unpack_from('<I', image.img, 0x157adfc + 4 * index)[0]
        require(native - 0x580000 == int(proof['rva'], 16) ==
                int(rows[index]['rva'], 16), f'Native vtable slot {index} mismatch')
    require(bytes(image.img[0x2f27a3:0x2f27b0]) == b'\xcc' * 13,
            'Native Copy/Move boundary drift')
    creation = manifest['creation']
    require(int(creation['creation_proof_rva'], 16) == 0x2dc73a,
            'Native callable creation identity drift')
    expected_creation = bytes.fromhex(
        '8a44240b83ec288bccc701fcadaf01c74104409d860088410889710c894924')
    require(bytes.fromhex(creation['creation_proof_bytes']) == expected_creation and
            bytes(image.img[0x2dc73a:0x2dc73a + len(expected_creation)]) ==
            expected_creation, 'Native callable construction fingerprint drift')
    return {'source': str(source), 'flags': flags,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'functions': rows, 'unique_function_bytes': 75,
            'vtable_bytes': 24, 'vtable_slots_verified': 6,
            'creation_fingerprint_verified': True,
            'type_limitations': manifest['type_limitations']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    result = verify(args.manifest)
    if args.audit:
        args.audit.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('Verified 6 complete implementations, 75 unique function bytes, '
          '24 vtable bytes / 6 targets, and the native construction fingerprint.')


if __name__ == '__main__':
    main()
