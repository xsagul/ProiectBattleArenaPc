"""The 13.3 items: price, stacks, recipe and stat mods, from the game's own data.

  global/items/items.bin in DATA/FINAL/Global.wad.client (ItemData: itemID, price = the item's own combine cost,
  maxStack, mFlat* / mPercent* stat mods, mDataValues) and the recipes / total prices of the client's game data
  (rcp-be-lol-game-data v1/items.json: from, priceTotal, inStore). Cached in data/exe133/items133.json.

  items133.py [item id ...]       builds the cache and shows those items
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
CACHE = os.path.join(ROOT, 'data', 'exe133', 'items133.json')
BAINFO = os.path.join(ROOT, 'tools', 'bin', 'bainfo.exe')
GLOBAL = r'C:\Users\Sorin\Desktop\ProiectBattleArenaPc\game\DATA\FINAL\Global.wad.client'
GAME_DATA = os.path.join(ROOT, 'data', 'lcu', '13.3', 'plugins', 'rcp-be-lol-game-data', 'global', 'default', 'v1', 'items.json')
_items = None


def build():
    out = subprocess.run([BAINFO, 'bin', GLOBAL, 'global/items/items.bin', '', os.path.join(ROOT, 'data', 'hashes')],
                         capture_output=True, text=True).stdout.splitlines()
    items, cur = {}, None
    for line in out:
        if re.match(r'^\S', line):
            cur = {} if '(ItemData)' in line else None
            continue
        if cur is None:
            continue
        m = re.match(r'^  (\w+): (.*)$', line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if k == 'itemID':
            items[int(v)] = cur
            cur['id'] = int(v)
        elif k in ('price', 'maxStack'):
            cur[k] = int(float(v))
        elif re.match(r'^(mFlat|mPercent|mAbilityHaste)', k):
            try:
                cur.setdefault('stats', {})[k] = float(v)
            except ValueError:
                pass
    for d in json.load(open(GAME_DATA, encoding='utf8')):
        it = items.setdefault(d['id'], {'id': d['id']})
        it.update(name=d['name'], priceTotal=d['priceTotal'], comps=d['from'], inStore=d['inStore'],
                  consumable='Consumable' in d.get('categories', []))
        it.setdefault('price', d['price'])
        it.setdefault('maxStack', d.get('maxStacks', 1))
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
        """the component owned (one copy, not used yet) -> its value, else its own components'"""
        for slot, iid in owned.items():
            if iid == comp and slot not in used:
                used.append(slot)
                return db.get(comp, {}).get('priceTotal', 0)
        return sum(take(c) for c in db.get(comp, {}).get('comps', []))
    discount = sum(take(c) for c in it.get('comps', []))
    cost = it.get('priceTotal', it.get('price', 0)) - discount
    if cost > gold + 1e-6:
        return 'not enough gold'
    trinket = 'Trinket' in it.get('name', '') or item_id in (3340, 3363, 3364)
    if trinket:
        return cost, used, 6
    free = [i for i in range(6) if inventory[i] is None or i in used]
    if not free:
        return 'inventory full'
    return cost, used, min(free)


if __name__ == '__main__':
    db = build()
    print(len(db), 'items')
    for x in sys.argv[1:]:
        print(json.dumps(db.get(int(x)), indent=1))
