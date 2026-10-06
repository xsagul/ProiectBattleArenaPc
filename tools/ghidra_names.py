"""Everything we know by name about the 13.3 client's code, for the Ghidra workspace (client-src/names.tsv:
rva <tab> kind <tab> name, kind = func | label).

Sources (all measured, see docs/MIGRARE_12.23.md): client-src/functions.txt (every function start, unnamed),
client-src/handler_table.txt (packet id -> handler), data/exe133/packet_table.txt (server->client packet classes:
constructor, vtable, reader), data/exe133/c2s_classes.txt (client->server classes: constructor, writer, vtable),
client-src/import_table.txt (the 430 import slots), and MANUAL below (functions found by hand, each with where it was
established). No guesses: a function whose role is only suspected gets no name.

  ghidra_names.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SRC = os.path.join(ROOT, 'client-src')
EXE = os.path.join(ROOT, 'data', 'exe133')

MANUAL = [
    # transport (docs: "Transportul complet", 2026-10-04)
    (0x2ef720, 'func_with_sendto', 'Net_SendTo'),
    (0x2ed590, 'func_with_recvfrom', 'Net_RecvFrom'),
    (0x2eb010, 'func_with_socket', 'Net_Socket'),
    (0x2e4a80, 'creates LNP_Send thread', 'LNP_StartSendThread'),
    (0x2ef8e0, 'send thread', 'LNP_SendThread'),
    (0x2efe50, 'datagram writer', 'LNP_WriteDatagram'),
    (0x2de720, 'CRC-32 of a datagram', 'LNP_Crc32'),
    (0x9c4f80, 'Blowfish CFB', 'Blowfish_Cfb'),
    (0x2ed8f0, 'receive thread', 'LNP_ReceiveThread'),
    (0x2dceb0, 'datagram reader', 'LNP_ReadDatagram'),
    (0x351480, 'reads [Network] of game.cfg', 'Config_ReadNetwork'),
    (0x2edff0, 'sets up the 7 channels', 'LNP_SetupChannels'),
    (0x2e0cd0, 'app queue observer', 'LNP_AppQueueObserver'),
    (0x370810, 'per-frame network pump', 'Net_PerFrame'),
    # game listeners and packets
    (0x3554e0, 'connection listener (574, 545, 603 ...)', 'Listener_Connection'),
    (0x355f80, 'game listener (552, 595, 518 ...)', 'Listener_Game'),
    (0x364850, '574: the local player slot', 'Game_SetLocalPlayerSlot'),
    (0x3630c0, 'Game Server Connection Established', 'Game_OnConnected'),
    (0x365650, '79: create hero', 'OnPacket79_CreateHero'),
    (0x813050, '49: cast info reader', 'CastInfo_Read'),
    (0x146910, 'C2S reader stub (xor al,al)', 'C2S_ReaderStub'),
    (0x29d4f0, '552 handler (verified 10-06)', 'OnPacket552_Waypoints'),
    (0x29dc10, '552: one unit entry', 'Waypoints_ApplyEntry'),
    (0x19e900, 'rejects a path older than the unit\'s last value (+0x41c)', 'MoveSync_AcceptIfNotOlder'),
    (0x688c80, 'builds C2S 567 (shop item list)', 'Shop_SendSelection'),
    # replication (docs: "Pachetul 595")
    (0x19ccc0, 'registers a replicated class', 'Replication_RegisterClass'),
    (0x1a2ff0, 'replication manager', 'Replication_Manager'),
    (0x17a490, 'hero replicated values', 'Replication_HeroClass'),
    (0x1cdd20, 'lane minion replicated values', 'Replication_LaneMinionClass'),
    (0x1ce2a0, 'turret replicated values', 'Replication_TurretClass'),
    (0x770d60, 'structure replicated values', 'Replication_StructureClass'),
    (0x2e9090, 'map object net id CRC', 'MapObject_NetIdCrc'),
    (0x9d42e0, 'pool free', 'Pool_Free'),
]
LABELS = [
    (0xfb357c, 'C2S_Base_vtable'),
    (0x156ffb8, 'FieldDecode_Table552'),
]


def main():
    rows = []
    for x in open(os.path.join(SRC, 'functions.txt')).read().split():
        rows.append((int(x, 16), 'func', ''))
    for line in open(os.path.join(EXE, 'packet_table.txt')):
        if line.startswith('#'):
            continue
        p = line.split()
        pid, ctor, vt, des = int(p[0]), int(p[2], 16), int(p[3], 16), int(p[4], 16)
        if ctor:
            rows.append((ctor, 'func', f'S2C_{pid}_Construct'))
        if des:
            rows.append((des, 'func', f'S2C_{pid}_Read'))
        if vt:
            rows.append((vt, 'label', f'S2C_{pid}_vtable'))
    for line in open(os.path.join(SRC, 'handler_table.txt')):
        if line.startswith('#') or not line.strip():
            continue
        p = line.split()
        pid, h = int(p[0]), int(p[1], 16)
        rows.append((h, 'func', f'OnPacket{pid}'))
    for line in open(os.path.join(EXE, 'c2s_classes.txt')):
        p = line.split()
        pid, ctor, wr, vt = int(p[0]), int(p[1], 16), int(p[2], 16), int(p[4], 16)
        rows.append((ctor, 'func', f'C2S_{pid}_Construct'))
        rows.append((wr, 'func', f'C2S_{pid}_Write'))
        rows.append((vt, 'label', f'C2S_{pid}_vtable'))
    for line in open(os.path.join(SRC, 'import_table.txt')):
        if line.startswith('#') or not line.strip():
            continue
        rva, mod, fn = line.split()[:3]
        rows.append((int(rva, 16), 'label', f'imp_{mod.split(".")[0]}_{fn}'))
    for rva, why, name in MANUAL:
        rows.append((rva, 'func', name))
    for rva, name in LABELS:
        rows.append((rva, 'label', name))
    # one name per address (a handler shared by many ids keeps the first; manual names win)
    best = {}
    for rva, kind, name in rows:
        key = (rva, kind)
        if name and (key not in best or not best[key] or any(rva == m[0] for m in MANUAL)):
            best[key] = name
        else:
            best.setdefault(key, name)
    with open(os.path.join(SRC, 'names.tsv'), 'w') as f:
        for (rva, kind), name in sorted(best.items()):
            f.write(f'{rva:x}\t{kind}\t{name}\n')
    named = sum(1 for v in best.values() if v)
    print(len(best), 'entries,', named, 'named ->', os.path.join(SRC, 'names.tsv'))


if __name__ == '__main__':
    main()
