"""The shop of our 16.20 server: the player's buy request (client 1135) answered as the live server does.

Measured on data/live/4013831789: 1135 = [header][+0x10 a constant 79][+0x14 the item id, varint] (codec/c2s_1135.json,
varint tables completed by c2s16.repair_varints); the answer in the same tick: 1122 {+0x10 the purchases since the
champion came to the shop} and 63 {+0x10 gold left, +0x18 {+0x18 item id, +0x68 stacks, +0x6c the item's total
price}, +0x70 the inventory slot (0..5, 6 = trinket), +0x90 1, +0x91 1}, then the champion's gold and stats in a
replication. The client takes the recipe's components out of the inventory itself (no packet for them live).
Prices, recipes and stats: items16.py (game16's own item data); the purchase rule: LoL's (items16.purchase).
"""
import copy
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import items16   # noqa: E402

BUY_REQUEST = 1135
SHOP_RANGE = 1200.0          # from the fountain [approximation]
# item stat mods -> the replicated values they add to [names: repl16 AIHero]
STAT_TO_REPL = {'mFlatPhysicalDamageMod': 'mFlatPhysicalDamageMod', 'mFlatMagicDamageMod': 'mFlatMagicDamageMod',
                'mFlatArmorMod': 'mArmor', 'mFlatSpellBlockMod': 'mSpellBlock', 'mFlatHPPoolMod': 'mMaxHP',
                'mFlatMPPoolMod': 'mMaxPAR', 'mPercentAttackSpeedMod': 'mAttackSpeedMod',
                'mFlatMovementSpeedMod': 'mMoveSpeed', 'mFlatCritChanceMod': 'mCritChance'}


def read_request(body):
    import c2s16
    spec = c2s16.load(BUY_REQUEST)
    v = c2s16.decode(spec, body)
    if v is None:
        return None
    return int.from_bytes(v[0x14], 'little')


class Shop:
    def __init__(self, hero, events):
        self.hero, self.ev = hero, events
        self.inventory = [None] * 7
        self.session = 0
        self.tpl = events.values('item_bought', 63)
        self.bonus = {}

    def on_request(self, body, t, world):
        """-> (packets, text)"""
        item = read_request(body)
        h = self.hero
        if item is None:
            return [], 'buy request not read'
        if h.alive and math.dist(h.place(t), h.home) > SHOP_RANGE:
            return [], f'buy {item}: not at the shop'
        r = items16.purchase(item, self.inventory, h.gold)
        if isinstance(r, str):
            return [], f'buy {item}: {r}'
        cost, used, slot = r
        for s in used:
            self.inventory[s] = None
        self.inventory[slot] = item
        self.session += 1
        h.gold -= cost
        it = items16.items()[item]
        sc = self.ev.schema
        v = copy.deepcopy(self.tpl)
        v['+0x10'] = struct.pack('<f', h.gold).hex()
        v['+0x18']['+0x18'] = struct.pack('<I', item).hex()
        v['+0x18']['+0x6c'] = struct.pack('<f', float(it.get('priceTotal', 0))).hex()
        v['+0x18']['+0x70'] = f'{slot:02x}'
        out = [(1, 1122, h.net, sc(1122).encode({'+0x10': f'{min(self.session, 255):02x}'})),
               (1, 63, h.net, sc(63).encode(v))]
        out.append(h.replication(t, dict(self.stats(), mGold=h.gold)))
        return out, f'bought {item} for {cost:.0f} into slot {slot} (gold left {h.gold:.0f}; components out of slots {used})'

    def stats(self):
        """the champion's values with every item's stats added"""
        h = self.hero
        add = {}
        for item in self.inventory:
            for k, x in items16.items().get(item, {}).get('stats', {}).items() if item else ():
                if k in STAT_TO_REPL:
                    add[STAT_TO_REPL[k]] = add.get(STAT_TO_REPL[k], 0.0) + x
        base = h.stats_at(h.level) if hasattr(h, 'stats_at') else {}
        out = {}
        hp_bonus = add.pop('mMaxHP', 0.0)
        if base:
            new_max = base['mMaxHP'] + hp_bonus
            h.hp += new_max - h.max_hp
            h.max_hp = new_max
            out['mMaxHP'] = new_max
            out['mHP'] = h.hp
        bonus_ad = add.get('mFlatPhysicalDamageMod', 0.0)
        if hasattr(h, 'base'):
            h.damage = base.get('mBaseAttackDamage', h.damage) + bonus_ad
        out.update(add)
        if 'mArmor' in add and base:
            out['mArmor'] = base['mArmor'] + add['mArmor']
        self.bonus = add
        return out

    def left_shop(self):
        self.session = 0
