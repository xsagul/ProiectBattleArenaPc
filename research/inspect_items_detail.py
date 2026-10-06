import sys
sys.path.append('tools')
import wadx, binx

w = wadx.Wad(r'C:\Users\Sorin\Desktop\lol14.1\DATA\FINAL\Global.wad.client')
h = 0x1d720f4f42640c18
raw = w.read(h)
b = binx.read(raw)

items = {}
for e in b.entries:
    if e.cls == binx.fnv1a("ItemData"):
        item_id = None
        for f in e.fields:
            if f.name == "itemID":
                item_id = f.val
        if item_id:
            items[item_id] = e

print(f"Total ItemData entries found: {len(items)}")

check_ids = [3031, 6610, 6694, 6695, 6696, 6697, 6698, 6699, 6653, 6655, 6657, 2504, 2503, 3078, 3087, 3094, 3036, 4645, 3151]
for iid in check_ids:
    if iid in items:
        e = items[iid]
        d = {f.name: f.val for f in e.fields}
        name = d.get('mDisplayName', '')
        print(f"Item {iid}: {name}")
        for k, v in d.items():
            if 'Mod' in k or 'Passive' in k or 'Spell' in k or 'Effect' in k or 'desc' in k.lower():
                print(f"   {k}: {v}")
