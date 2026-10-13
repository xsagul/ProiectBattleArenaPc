"""The 16.20 items: price, stacks, recipe, stats, from the game's own data (game16 Global.wad, the items bin
{1d720f4f42640c18} - the same entry as in 14.1; read with bainfo -> data/exe1620/items_bin.txt).

  ItemData: itemID, price (the item's own combine cost), maxStack, mFlat* / mPercent* stat mods, recipeItemLinks
  (the components, as their entry hashes), mItemDataAvailability.mInStore, mCategories
  total price = own price + the components' total prices (computed here)

  items16.py [item id ...]     builds data/exe1620/items16.json and shows those items
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
DUMP = os.path.join(ROOT, 'data', 'exe1620', 'items_bin.txt')
CACHE = os.path.join(ROOT, 'data', 'exe1620', 'items16.json')
WAD = os.path.join(ROOT, 'game16', 'DATA', 'FINAL', 'Global.wad.client')
_items = None


def build():
    if not os.path.exists(DUMP):
        out = subprocess.run([os.path.join(ROOT, 'tools', 'bin', 'bainfo.exe'), 'bin', WAD, '{1d720f4f42640c18}', '',
                              os.path.join(ROOT, 'data', 'hashes')], capture_output=True, text=True).stdout
        open(DUMP, 'w').write(out)
    items, by_key, cur, key, field = {}, {}, None, None, None
    for line in open(DUMP, encoding='utf-8', errors='replace'):
        line = line.rstrip('\n')
        m = re.match(r'^(\{[0-9a-f]+\}) \((\w+)\)$', line)
        if m:
            cur = {'comps_keys': [], 'categories': [], 'stats': {}} if m.group(2) == 'ItemData' else None
            key = m.group(1)
            field = None
            continue
        if cur is None:
            continue
        m = re.match(r'^  (\w+): ?(.*)$', line)
        if m:
            field, v = m.group(1), m.group(2).strip()
            if field == 'itemID':
                cur['id'] = int(v)
                items[int(v)] = cur
                by_key[key] = int(v)
            elif field in ('price', 'maxStack'):
                cur[field] = int(float(v))
            elif re.match(r'^(mFlat|mPercent|mAbilityHaste|Percent|Flat)', field):
                try:
                    cur['stats'][field] = float(v)
                except ValueError:
                    pass
            elif field == 'mDisplayName':
                cur['name'] = v.strip('"')
            continue
        m = re.match(r'^    (\{[0-9a-f]+\})$', line)
        if m and field == 'recipeItemLinks':
            cur['comps_keys'].append(m.group(1))
        m = re.match(r'^    "(\w+)"$', line)
        if m and field == 'mCategories':
            cur['categories'].append(m.group(1))
        m = re.match(r'^    mInStore: (\d)', line)
        if m:
            cur['inStore'] = m.group(1) == '1'
    for it in items.values():
        it['comps'] = [by_key[k] for k in it.pop('comps_keys') if k in by_key]
        it.setdefault('price', 0)
        it.setdefault('maxStack', 1)
        it.setdefault('inStore', False)
        it['consumable'] = 'Consumable' in it['categories']

    def total(i, depth=0):
        it = items.get(i)
        if not it or depth > 8:
            return 0
        if 'priceTotal' not in it:
            it['priceTotal'] = it['price'] + sum(total(c, depth + 1) for c in it['comps'])
        return it['priceTotal']
    for i in items:
        total(i)
    json.dump({str(k): v for k, v in items.items()}, open(CACHE, 'w'), indent=0)
    return items


def items():
    global _items
    if _items is None:
        if not os.path.exists(CACHE):
            build()
        _items = {int(k): v for k, v in json.load(open(CACHE)).items()}
    return _items


def purchase(item_id, inventory, gold):
    """LoL's purchase rule: the total price minus the total price of every component already owned (searched
    through the recipe tree, each owned item used once), the components taken out of the inventory.
    inventory: [item id or None] x 7 (slot 6 = trinket). -> (cost, slots to empty, slot for the new item) or a
    reason string"""
    db = items()
    it = db.get(item_id)
    if not it or not it.get('inStore', True):
        return 'not sold'
    owned = {i: s for i, s in enumerate(inventory) if s is not None}
    used = []

    def take(comp):
        for slot, iid in owned.items():
            if iid == comp and slot not in used:
                used.append(slot)
                return db.get(comp, {}).get('priceTotal', 0)
        return sum(take(c) for c in db.get(comp, {}).get('comps', []))
    discount = sum(take(c) for c in it.get('comps', []))
    cost = it.get('priceTotal', it.get('price', 0)) - discount
    if cost > gold + 1e-6:
        return 'not enough gold'
    if 'Trinket' in it.get('categories', []) or item_id in (3340, 3363, 3364):
        return cost, used, 6
    free = [i for i in range(6) if inventory[i] is None or i in used]
    if not free:
        return 'inventory full'
    return cost, used, min(free)


if __name__ == '__main__':
    db = build()
    print(len(db), 'items,', sum(1 for i in db.values() if i.get('inStore')), 'in the store')
    for x in sys.argv[1:]:
        print(json.dumps(db.get(int(x)), indent=1))
