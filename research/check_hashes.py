import sys
sys.path.append('tools')
import wadx, struct, xxhash

def fnv1a(s):
    h = 0x811c9dc5
    for b in s.lower().encode('utf-8'):
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    return h

champs = ['Garen', 'Lux', 'Ashe', 'Tryndamere', 'Zed']
for c in champs:
    path = f'C:\\Users\\Sorin\\Desktop\\lol14.1\\DATA\\FINAL\\Champions\\{c}.wad.client'
    w = wadx.Wad(path)
    bin_path = f'data/characters/{c.lower()}/{c.lower()}.bin'
    h = xxhash.xxh64(bin_path.encode('ascii')).intdigest()
    data = w.read(h)
    
    dv_le = struct.pack('<I', fnv1a("DataValues"))
    mdv_le = struct.pack('<I', fnv1a("mDataValues"))
    name_le = struct.pack('<I', fnv1a("name"))
    mname_le = struct.pack('<I', fnv1a("mName"))
    vals_le = struct.pack('<I', fnv1a("values"))
    mvals_le = struct.pack('<I', fnv1a("mValues"))
    
    print(f'{c}: DataValues={dv_le in data}, mDataValues={mdv_le in data}, name={name_le in data}, mName={mname_le in data}, values={vals_le in data}, mValues={mvals_le in data}')
