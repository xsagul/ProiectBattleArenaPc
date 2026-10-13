"""Items and the shop, from the game's own item data (Global.wad's item bin, through the bin cache: no lag).

ItemData: itemID, price (the item's own combine cost), recipeItemLinks (its components), maxStack, the stat fields
(mFlatHPPoolMod, mFlatPhysicalDamageMod, mPercentAttackSpeedMod, flatMPPoolMod ...), sellBackModifier, consumed,
mItemDataAvailability.mInStore, mCategories. An item's total price = its own price + its components' totals.

The live server's forms [measured, Garen's purchases]:
  buy  (client 1135 {item id})   -> 1196 {gold, slot} for every component taken out of the inventory, 1122 {purchases
                                    in this visit}, 63 {gold left, item, price paid, slot, 1, 1}; the new gold and
                                    stats follow in the replication
  sell (client 745 {slot})       -> 1122, 1196 {gold after, slot, 0, 1}
The purchase rule is LoL's: the total price minus the total price of every component owned (searched through the
recipe tree, each owned item used once); the components leave the inventory; the item takes the lowest free slot
(a trinket slot 6); a consumable stacks.
"""
import os

import bin_tree as BT

from . import gamedata as G
from . import packets as P
from .units import dist

SHOP_RANGE = 1250.0
# item stat field -> (the unit's modifier, factor)
STAT = {'mFlatHPPoolMod': ('hp', 1.0), 'flatMPPoolMod': ('par', 1.0), 'mFlatPhysicalDamageMod': ('ad', 1.0),
        'mFlatMagicDamageMod': ('ap', 1.0), 'mFlatArmorMod': ('armor', 1.0), 'mFlatSpellBlockMod': ('mr', 1.0),
        'mPercentAttackSpeedMod': ('as', 1.0), 'mFlatMovementSpeedMod': ('ms', 1.0), 'mPercentMovementSpeedMod': ('ms_pct', 1.0),
        'mFlatCritChanceMod': ('crit', 1.0), 'mAbilityHasteMod': ('haste', 1.0), 'mPercentLifeStealMod': ('lifesteal', 1.0),
        'PercentOmnivampMod': ('omnivamp', 1.0), 'mPercentBaseHPRegenMod': ('hp_regen_pct', 1.0),
        'percentBaseMPRegenMod': ('par_regen_pct', 1.0), 'mFlatHPRegenMod': ('hp_regen', 0.2), 'flatMPRegenMod': ('par_regen', 0.2),
        'mPercentTenacityItemMod': ('tenacity', 1.0), 'mFlatMagicPenetrationMod': ('magic_pen', 1.0),
        'mPercentArmorPenetrationMod': ('armor_pen', 1.0), 'mPercentMagicPenetrationMod': ('magic_pen_pct', 1.0),
        'PhysicalLethality': ('lethality', 1.0), 'mFlatAttackRangeMod': ('range', 1.0)}
TRINKETS = (3340, 3363, 3364, 3330)
# the sell request's slot byte as the client hides it. The client's code where it builds the request (rva 0x2e341c of
# 16.20): neighbouring bits swapped, rotated left by 2, through the byte table at rva 0x1a17e00, ^ 0x9b, - 0x14,
# rotated right by 5 -> this table [both sells of the live recording agree: slot 0 = 0x8c, slot 2 = 0xf3]
SELL_SLOT = {0x8c: 0, 0x3b: 1, 0xf3: 2, 0x67: 3, 0x10: 4, 0xb1: 5, 0x1d: 6, 0x5d: 7, 0xb5: 8}
_items = None


def items():
    """{item id: {'price', 'total', 'comps', 'stats', 'stack', 'in_store', 'consumable', 'sell', 'categories'}}"""
    global _items
    if _items is not None:
        return _items
    ents = BT.entries(os.path.join(G.GAME, 'Global.wad.client'), '{1d720f4f42640c18}')
    out, by_key = {}, {}
    for key, cls, v in ents:
        if cls != 'ItemData' or 'itemID' not in v:
            continue
        iid = int(v['itemID'])
        stats = {}
        for k, x in v.items():
            if k in STAT and isinstance(x, (int, float)):
                stats[k] = float(x)
        cats = [c for c in (v.get('mCategories') or []) if isinstance(c, str)]
        out[iid] = {'id': iid, 'price': int(v.get('price', 0) or 0), 'links': list(v.get('recipeItemLinks') or []),
                    'stats': stats, 'stack': int(v.get('maxStack', 1) or 1),
                    'in_store': bool(((v.get('mItemDataAvailability') or {}).get('mInStore')) or 0),
                    'consumable': 'Consumable' in cats or bool(v.get('consumed')), 'categories': cats,
                    'sell': float(v.get('sellBackModifier', 0.7) or 0.7), 'can_sell': v.get('mCanBeSold', 1) != 0,
                    'level': int(v.get('mRequiredLevel', 0) or 0)}
        by_key[key] = iid
    for it in out.values():
        it['comps'] = [by_key[k] for k in it.pop('links') if k in by_key]

    def total(i, depth=0):
        it = out.get(i)
        if it is None or depth > 8:
            return 0
        if 'total' not in it:
            it['total'] = it['price'] + sum(total(c, depth + 1) for c in it['comps'])
        return it['total']
    for i in out:
        total(i)
    _items = out
    return out


def price(item_id, inventory):
    """-> (cost, slots of the owned components used) by LoL's rule"""
    db = items()
    it = db[item_id]
    owned = {i: s for i, s in enumerate(inventory) if s is not None}
    used = []

    def take(comp):
        for slot, iid in owned.items():
            if iid == comp and slot not in used:
                used.append(slot)
                return db.get(comp, {}).get('total', 0)
        return sum(take(c) for c in db.get(comp, {}).get('comps', []))
    discount = sum(take(c) for c in it['comps'])
    return it['total'] - discount, used


class Shop:
    def __init__(self, game):
        self.g = game
        self.db = items()
        self.visits = {}                 # hero net -> purchases in this visit (1122's number)
        self.undo = {}                   # hero net -> [(inventory, stacks, gold)] of this visit, newest last
        self.spots = [tuple(s['pos']) for s in game.data.get('shops', [])]

    def in_range(self, hero):
        if not hero.alive:
            return True                  # a dead champion may shop
        return dist(hero.pos, hero.home) <= SHOP_RANGE or any(dist(hero.pos, s) <= SHOP_RANGE for s in self.spots)

    def buy(self, hero, item_id, anywhere=False):
        g = self.g
        it = self.db.get(item_id)
        if it is None or not it['in_store'] or item_id > 9999:
            return f'{hero.name} buy {item_id}: not sold here'
        if not anywhere and not self.in_range(hero):
            return f'{hero.name} buy {item_id}: not at the shop'
        inv = hero.inventory
        cost, used = price(item_id, inv)
        if cost > hero.gold + 1e-6:
            return f'{hero.name} buy {item_id}: not enough gold ({hero.gold:.0f} < {cost})'
        self.undo.setdefault(hero.net, []).append((list(inv), list(hero.item_stacks), hero.gold))
        trinket = item_id in TRINKETS or 'Trinket' in it['categories']
        stack_slot = next((i for i, s in enumerate(inv) if s == item_id and hero.item_stacks[i] < it['stack']), None) if it['stack'] > 1 else None
        if stack_slot is not None:
            slot = stack_slot
        elif trinket:
            slot = 6
        else:
            free = [i for i in range(6) if inv[i] is None or i in used]
            if not free:
                return f'{hero.name} buy {item_id}: inventory full'
            slot = min(free)
        hero.gold -= cost
        for s in used:
            inv[s] = None
            hero.item_stacks[s] = 0
            g.q.append((1, 1196, hero.net, g.pk.enc(1196, {'+0x10': P.f32(hero.gold), '+0x14': f'{s:02x}', '+0x15': '00', '+0x16': '00'})))
        inv[slot] = item_id
        hero.item_stacks[slot] = hero.item_stacks[slot] + 1 if stack_slot is not None else 1
        n = self.visits[hero.net] = self.visits.get(hero.net, 0) + 1
        pid, v = g.pk.form('item_bought')
        v['+0x10'] = P.f32(hero.gold)
        # [m] +0x71 = how many the slot holds now (2 for a second potion), +0x68 a flag that is always 1 here,
        # +0x30 the item's charges (not kept by us)
        v['+0x18'].update({'+0x18': P.u32(item_id), '+0x30': '0000', '+0x68': '01', '+0x6c': P.f32(float(cost)),
                           '+0x70': f'{slot:02x}', '+0x71': f'{min(hero.item_stacks[slot], 255):02x}'})
        v.update({'+0x90': '01', '+0x91': '01'})
        if getattr(g, 'pets', None) is not None:
            g.pets.bought(hero, item_id, slot)           # the jungle item's treats (before its 63)
        g.q.append((1, 1122, hero.net, g.pk.enc(1122, {'+0x10': f'{min(n, 255):02x}'})))
        g.q.append((1, pid, hero.net, g.pk.enc(pid, v)))
        self.apply(hero)
        hero.set_many({'mGold': hero.gold})
        return f'{hero.name} buys {item_id} for {cost} into slot {slot} (gold left {hero.gold:.0f})'

    def sell(self, hero, slot, anywhere=False):
        g = self.g
        inv = hero.inventory
        if not 0 <= slot <= 6 or inv[slot] is None or (not anywhere and not self.in_range(hero)):
            return f'{hero.name} sell slot {slot}: nothing to sell'
        it = self.db[inv[slot]]
        back = round(it['total'] * it['sell'])
        self.undo.setdefault(hero.net, []).append((list(inv), list(hero.item_stacks), hero.gold))
        hero.gold += back
        hero.item_stacks[slot] -= 1
        if hero.item_stacks[slot] <= 0:
            inv[slot] = None
        n = self.visits[hero.net] = self.visits.get(hero.net, 0) + 1
        g.q.append((1, 1122, hero.net, g.pk.enc(1122, {'+0x10': f'{min(n, 255):02x}'})))
        g.q.append((1, 1196, hero.net, g.pk.enc(1196, {'+0x10': P.f32(hero.gold), '+0x14': f'{slot:02x}', '+0x15': '00', '+0x16': '01'})))
        self.apply(hero)
        hero.set_many({'mGold': hero.gold})
        return f'{hero.name} sells slot {slot} for {back}'

    def other(self, hero, pid, body):
        from . import c2s
        if pid == c2s.SELL and body:
            v = c2s.generic(pid, body)
            b = v[0x10][0] if v else body[0]
            slot = SELL_SLOT.get(b)
            if slot is None:
                return f'{hero.name} sell request with slot byte {b:#04x}: this slot byte is not known yet'
            return self.sell(hero, slot)
        if pid == c2s.UNDO:
            return self.undo_last(hero)
        return f'shop request {pid} ({body.hex()}) not handled'

    def undo_last(self, hero):
        """the last purchase or sale of this shop visit taken back: the inventory and the gold as they were. The
        client is told slot by slot with the packets a purchase uses: 1196 (a slot emptied), 63 (an item in a slot)
        [a: the live recording's two undo requests show no packet of their own]"""
        g = self.g
        stack = self.undo.get(hero.net)
        if not stack or not self.in_range(hero):
            return f'{hero.name} undo: nothing to take back'
        inv, stacks, gold = stack.pop()
        now = list(hero.inventory)
        hero.inventory[:] = inv
        hero.item_stacks[:] = stacks
        hero.gold = gold
        n = self.visits[hero.net] = self.visits.get(hero.net, 0) + 1
        g.q.append((1, 1122, hero.net, g.pk.enc(1122, {'+0x10': f'{min(n, 255):02x}'})))
        for slot, (was, will) in enumerate(zip(now, inv)):
            if was == will and (will is None or hero.item_stacks[slot] == stacks[slot]):
                continue
            if was is not None:
                g.q.append((1, 1196, hero.net, g.pk.enc(1196, {'+0x10': P.f32(gold), '+0x14': f'{slot:02x}', '+0x15': '00', '+0x16': '00'})))
            if will is not None:
                pid, v = g.pk.form('item_bought')
                v['+0x10'] = P.f32(gold)
                v['+0x18'].update({'+0x18': P.u32(will), '+0x30': '0000', '+0x68': '01', '+0x6c': P.f32(float(self.db[will]['total'])),
                                   '+0x70': f'{slot:02x}', '+0x71': f'{max(1, min(stacks[slot], 255)):02x}'})
                v.update({'+0x90': '01', '+0x91': '01'})
                g.q.append((1, pid, hero.net, g.pk.enc(pid, v)))
        self.apply(hero)
        hero.set_many({'mGold': hero.gold})
        return f'{hero.name} takes back the last shop action (gold {hero.gold:.0f})'

    def apply(self, hero):
        """the champion's modifiers from everything it carries"""
        mods = {}
        for slot, iid in enumerate(hero.inventory):
            if iid is None:
                continue
            for k, x in self.db[iid]['stats'].items():
                name, f = STAT[k]
                mods[name] = mods.get(name, 0.0) + x * f
        hero.add_mods('items', mods)
        hero.set_many({'mHP': hero.hp, 'mPAR': min(hero.par, hero.max_par)})

    def tick(self, t, dt):
        for h in self.g.heroes:
            if h.net in self.visits and h.alive and not self.in_range(h):
                del self.visits[h.net]
                self.undo.pop(h.net, None)           # what was bought stays bought once the shop is left


def setup(game, session=None):
    game.shop = Shop(game)
    game.systems.append(game.shop.tick)
