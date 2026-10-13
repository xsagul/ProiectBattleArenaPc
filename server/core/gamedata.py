"""The game's own data as the server uses it (game16's property bins, read through bin_tree's cache).

Everything here is what Riot's server reads too - the client ships the same files:
  map11()              lanes (MinionPath_*), barracks + their wave configuration (BarracksConfig), structures with lane /
                       position / team, jungle camps and their monsters, locators, the CLASSIC mode's tables
                       (experience per level, experience for a kill, shared experience, death times, gameplay config)
  unit(name)           a non-champion character's record (minions, monsters, turrets): stats, attack times, gold, xp
  champion(name)       a champion: stats and growth, attack data, spell names, recommended skill order and items
  champions()          every playable champion's name

The map summary is kept as data/exe1620/gamedata/map11.json (built on first use; delete it to rebuild).
`python server/core/gamedata.py` prints a digest; `... champion Ezreal` one champion.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
ROOT = os.path.dirname(SERVER)
sys.path.insert(0, SERVER)
os.environ.setdefault('BA_PATCH', '1620')
import bin_tree as BT   # noqa: E402

GAME = os.path.join(ROOT, 'game16', 'DATA', 'FINAL')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'gamedata')
MAP_WAD = os.path.join(GAME, 'Maps', 'Shipping', 'Map11.wad.client')
ORDER, CHAOS, NEUTRAL = 100, 200, 300
LANES = {0: 'bot', 1: 'mid', 2: 'top'}
_map = None
_units = {}
_champs = {}


# ------------------------------------------------------------------------------------------------ helpers
def vec(text):
    """'[1, 2, 3]' -> [1.0, 2.0, 3.0]"""
    return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?', text)]


def place(transform):
    """'[mtx4 ... x y z 1]' -> (x, z), y"""
    m = vec(transform.replace('mtx4', ''))
    return [round(m[12], 2), round(m[14], 2)], round(m[13], 2)


def mod(rec, name, default=0.0):
    """a ModifiableFloat / plain number field of a record"""
    v = rec.get(name + 'Modifiable', rec.get(name))
    if isinstance(v, dict):
        v = v.get('baseValue', default)
    if isinstance(v, list):
        v = v[0] if v else default
    return float(v) if isinstance(v, (int, float)) else default


def first(v, default=0.0):
    if isinstance(v, list):
        return float(v[0]) if v else default
    return float(v) if isinstance(v, (int, float)) else default


def record_stats(rec):
    """the numbers of a CharacterRecord the simulation needs"""
    ar = rec.get('primaryAbilityResource') or {}
    ba = rec.get('basicAttack') or {}
    total = first(ba.get('mAttackTotalTime'), 0.0)
    cast = first(ba.get('mAttackCastTime'), 0.0)
    # LoL: an attack's windup share of the attack time = 0.3 + mAttackDelayCastOffsetPercent, or cast / total time
    windup = (cast / total) if total > 0 and cast > 0 else 0.3 + first(ba.get('mAttackDelayCastOffsetPercent'), 0.0)
    tags = [t.strip() for t in str(rec.get('unitTagsString', '')).split('|') if t.strip()]
    return {
        'name': rec.get('mCharacterName', ''),
        'hp': mod(rec, 'baseHP'), 'hp_lvl': mod(rec, 'hpPerLevel'),
        'hp_regen': mod(rec, 'baseStaticHPRegen'), 'hp_regen_lvl': mod(rec, 'hpRegenPerLevel'),
        'par_type': ar.get('arType', None),
        'par': mod(ar, '{726ee5cd}'), 'par_lvl': mod(ar, '{6216bf7b}'),
        'par_regen': mod(ar, '{c4ab3550}'), 'par_regen_lvl': mod(ar, '{3a509002}'),
        # [m: SRU_MurkwolfMini has no baseDamage in its record and hits for 10.00 before armor (122 hits): the
        # record class's default]
        'ad': mod(rec, 'baseDamage', 10.0), 'ad_lvl': mod(rec, 'damagePerLevel'),
        'armor': mod(rec, 'baseArmor'), 'armor_lvl': mod(rec, 'armorPerLevel'),
        'mr': mod(rec, 'baseMR', mod(rec, 'baseSpellBlock')), 'mr_lvl': mod(rec, 'mrPerLevel'),
        'speed': mod(rec, 'baseMoveSpeed', 325.0), 'range': mod(rec, 'attackRange', 125.0),
        'as': mod(rec, 'attackSpeed', 0.625), 'as_ratio': mod(rec, 'attackSpeedRatio', mod(rec, 'attackSpeed', 0.625)),
        'as_lvl': mod(rec, 'attackSpeedPerLevel'),
        'windup': round(max(0.05, min(0.6, windup)), 4),
        'attack_total': total, 'attack_cast': cast,
        'crit_mult': float(rec.get('critDamageMultiplier', 1.75) or 1.75),
        'acquire': float(rec.get('acquisitionRange', first(rec.get('firstAcquisitionRange'), 600.0)) or 600.0),
        'wake': first(rec.get('wakeUpRange'), 0.0),
        'radius': first(rec.get('overrideGameplayCollisionRadius'), float(rec.get('pathfindingCollisionRadius', 35.0) or 35.0)),
        'path_radius': float(rec.get('pathfindingCollisionRadius', 35.0) or 35.0),
        'select_radius': float(rec.get('selectionRadius', 100.0) or 100.0),
        'sight': first(rec.get('perceptionBubbleRadius'), 1350.0),
        'gold': float(rec.get('goldGivenOnDeath', 0.0) or 0.0), 'local_gold': float(rec.get('localGoldGivenOnDeath', 0.0) or 0.0),
        'xp': float(rec.get('expGivenOnDeath', 0.0) or 0.0),
        'gold_radius': float(rec.get('goldRadius', 0.0) or 0.0), 'xp_radius': float(rec.get('experienceRadius', 0.0) or 0.0),
        'tower_priority': float(rec.get('towerTargetingPriorityBoost', 0.0) or 0.0),
        'tags': tags,
    }


# ------------------------------------------------------------------------------------------------ the map
def _root_record(ents, name):
    """the CharacterRecord 'Characters/<name>/CharacterRecords/Root' of a bin (else its first record)"""
    want = BT.key_of(f'Characters/{name}/CharacterRecords/Root')
    recs = [(k, v) for k, c, v in ents if c == 'CharacterRecord']
    for k, v in recs:
        if k == want:
            return v
    return recs[0][1] if recs else None


def unit(name):
    """the record numbers of a map character (minion, monster, turret, inhibitor, nexus)"""
    if name in _units:
        return _units[name]
    ents = BT.entries(MAP_WAD, f'data/characters/{name.lower()}/{name.lower()}.bin')
    rec = _root_record(ents, name)
    st = record_stats(rec) if rec else None
    if st is not None:
        spells = {v.get('mScriptName'): v for k, c, v in ents if c == 'SpellObject' and v.get('mScriptName')}
        ba = (rec.get('basicAttack') or {})
        atk = first_name(ba.get('mAttackName')) or f'{name}BasicAttack'
        sp = (spells.get(atk) or {}).get('mSpell') or {}
        st['attack_name'] = atk
        st['attack_names'], st['attack_weights'] = attack_variants(rec, atk)
        st['missile_speed'] = float(sp.get('missileSpeed', 0.0) or 0.0) if sp else 0.0
        st['extra_spells'] = [str(s).split('/')[-1] for s in rec.get('extraSpells', []) if s and s != 'BaseSpell']
    _units[name] = st
    return st


def attack_variants(rec, first):
    """the attack variants' names and their chances [data: basicAttack + extraAttacks, mAttackProbability; a
    variant without one counts 0 - Jinx's Q-form attacks]"""
    names, weights = [first], [first_value((rec.get('basicAttack') or {}).get('mAttackProbability'), 1.0)]
    stem = first[:-len('BasicAttack')] + 'BasicAttack' if first.endswith('BasicAttack') else None
    for i, a in enumerate(rec.get('extraAttacks', []) or []):
        # a variant without a name is <unit>BasicAttack<2, 3 ..> [m: SRU_ChaosMinionRangedBasicAttack2 in the replays]
        n = first_name(a.get('mAttackName') if isinstance(a, dict) else None) or (f'{stem}{i + 2}' if stem else None)
        if n:
            names.append(n)
            weights.append(first_value(a.get('mAttackProbability') if isinstance(a, dict) else None, 0.0))
    if sum(weights) <= 0:
        weights = [1.0] + [0.0] * (len(names) - 1)
    return names, weights


def first_value(v, default):
    v = first_name(v)
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def first_name(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v


MAP_VERSION = 2
PLACEABLE_TYPES = ('AttackableEntityTemplate', 'NeutralCampEntityTemplate', 'VfxEntityTemplate', 'SuperwardEntityTemplate',
                   'ShopEntityTemplate', 'BarracksEntityTemplate')
PLACEABLE_NET = 0x40000005


def build_map():
    geo = BT.entries(MAP_WAD, 'data/maps/mapgeometry/map11/base_srx.materials.bin')
    shp = BT.entries(MAP_WAD, 'data/maps/shipping/map11/map11.bin')
    by = {k: (c, v) for k, c, v in shp}
    out = {'lanes': {}, 'barracks': [], 'structures': [], 'camps': [], 'monsters': [], 'locators': {}, 'shops': []}
    paths = {}
    for k, c, v in geo:
        if c != 'MapPlaceableContainer':
            continue
        for ik, it in (v.get('items') or {}).items():
            if not isinstance(it, dict) or 'transform' not in it:
                continue
            pos, height = place(it['transform'])
            t = it.get('_type')
            team = (it.get('Team') or {}).get('Team', 0) if isinstance(it.get('Team'), dict) else 0
            if t == '{3c995caf}' and str(it.get('name', '')).startswith('MinionPath_'):
                pts = [[round(pos[0] + s[0], 1), round(pos[1] + s[2], 1)] for s in (vec(x) for x in it.get('Segments', []))]
                paths[ik] = (it['name'][len('MinionPath_'):].lower(), pts)
            elif t == 'BarracksEntityTemplate':
                b = it.get('Barracks') or {}
                out['barracks'].append({'key': ik, 'name': it.get('name'), 'pos': pos, 'height': height, 'lane': LANES[b.get('lane', 0)],
                                        'team': team or ORDER, 'config': b.get('BarracksConfig'), 'path': b.get('LinkedPath')})
            elif t == 'AttackableEntityTemplate':
                ch = it.get('Character') or {}
                name = str(ch.get('CharacterRecord', '')).split('/')[1] if ch.get('CharacterRecord') else ''
                au = it.get('AttackableUnit') or {}
                ld = au.get('LaneDefinition') or {}
                rec = {'key': ik, 'name': it.get('name'), 'pos': pos, 'height': height, 'character': name,
                       'skin': str(ch.get('Skin', '')).split('/')[-1], 'team': team or ORDER}
                if team == NEUTRAL or name.lower().startswith('sru_'):
                    rec['team'] = NEUTRAL
                    out['monsters'].append(rec)
                else:
                    rec.update(lane=LANES.get(ld.get('lane', 1), 'mid'), position=ld.get('Position', 0), type=au.get('type', 0))
                    out['structures'].append(rec)
            elif t == 'NeutralCampEntityTemplate':
                nc = it.get('NeutralCamp') or {}
                out['camps'].append({'key': ik, 'name': it.get('name'), 'pos': pos, 'height': height, 'icon': nc.get('MinimapIcon', ''),
                                     'level': nc.get('CampLevel', 1), 'def': nc.get('{5a4ef4e7}')})
            elif t == 'ShopEntityTemplate':
                out['shops'].append({'pos': pos, 'team': team})
            elif t == 'MapLocator' and isinstance(it.get('name'), str):
                out['locators'][it['name']] = pos + [height]
    for ik, (lane, pts) in paths.items():
        out['lanes'][lane] = pts                   # from the order base to the chaos base
    # every monster belongs to the nearest camp
    for m in out['monsters']:
        if out['camps']:
            m['camp'] = min(out['camps'], key=lambda c: math.dist(c['pos'], m['pos']))['key']
    # the mode's tables (CLASSIC)
    classic = next(v for k, c, v in shp if c == 'GameModeMapData' and v.get('mModeName') == BT.key_of('CLASSIC'))

    def table(key):
        return by[classic[key]][1] if classic.get(key) in by else {}
    xp = table('mExperienceCurveData')
    out['xp_per_level'] = xp.get('mExperienceRequiredPerLevel', [])
    out['xp_for_kill'] = xp.get('mExperienceGrantedForKillPerLevel', [])
    out['xp_shared_mult'] = xp.get('mExperienceGrantedMultForSharedKillPerLevel', [])
    out['xp_minion_split'] = table('mExperienceModData').get('mPlayerMinionSplitXp', [1, 0.65, 0.433, 0.325, 0.26])
    out['death_times'] = {k: v for k, v in table('mDeathTimes').items() if k != '_type'}
    out['gameplay'] = {k: v for k, v in table('mGameplayConfig').items() if isinstance(v, (int, float))}
    out['respawn_points'] = table('DefaultRespawnPoints').get('RespawnPoints', [])
    for k, c, v in shp:
        if c == 'MapLocatorArray':
            for loc in v.get('locators', []):
                out['locators'][loc.get('name')] = place(loc['transform'])[0] + [place(loc['transform'])[1]]
    # wave configuration per barracks config, with each minion type's character
    out['waves'] = {}
    templates = {}
    for src in (geo, shp):
        for k, c, v in src:
            if c == 'AttackableEntityTemplate' and isinstance(v.get('Character'), dict):
                templates[k] = str(v['Character'].get('CharacterRecord', '')).split('/')[1]
            elif c == 'MapPlaceableContainer':
                for ik, it in (v.get('items') or {}).items():
                    if isinstance(it, dict) and it.get('_type') == 'AttackableEntityTemplate' and isinstance(it.get('Character'), dict):
                        templates.setdefault(ik, str(it['Character'].get('CharacterRecord', '')).split('/')[1])
    for k, c, v in shp:
        if c != 'BarracksConfig':
            continue
        cfg = {kk: vv for kk, vv in v.items() if isinstance(vv, (int, float))}
        cfg['units'] = []
        for u in v.get('units', []):
            et = u.get('EntityTemplate')
            if isinstance(et, dict):
                ch = str((et.get('Character') or {}).get('CharacterRecord', '')).split('/')
                et = ch[1] if len(ch) > 1 else ''
            else:
                et = templates.get(et, '')
            cfg['units'].append({'type': u.get('MinionType'), 'character': et,
                                 'behavior': u.get('WaveBehavior'),
                                 'upgrade': {kk: vv for kk, vv in (u.get('MinionUpgradeStats') or {}).items() if kk != '_type'}})
        out['waves'][k] = cfg
    # every entity the map places has a net id of its own: 0x40000005 + the rank of its key among the templates
    # of these types [m: true of all 59 the recorded start state creates with 502 and of the one created later]
    members = {}
    for src in (geo, shp):
        for k, c, v in src:
            if c != 'MapPlaceableContainer':
                continue
            for ik, it in (v.get('items') or {}).items():
                if isinstance(it, dict) and ik.startswith('{') and it.get('_type') in PLACEABLE_TYPES and 'transform' in it:
                    members[int(ik.strip('{}'), 16)] = it
    out['placeables'] = {}
    for i, key in enumerate(sorted(members)):
        it = members[key]
        m = vec(it['transform'].replace('mtx4', ''))
        out['placeables'][f'{key:08x}'] = {'net': PLACEABLE_NET + i, 'type': it['_type'], 'pos': [m[12], m[14]], 'matrix': m}
    out['version'] = MAP_VERSION
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, 'map11.json'), 'w'), indent=1)
    return out


def map11():
    global _map
    if _map is None:
        p = os.path.join(OUT, 'map11.json')
        _map = json.load(open(p)) if os.path.exists(p) else None
        if _map is None or _map.get('version') != MAP_VERSION:
            _map = build_map()
    return _map


# ------------------------------------------------------------------------------------------------ champions
def champions():
    out = []
    for f in sorted(os.listdir(os.path.join(GAME, 'Champions'))):
        if f.endswith('.wad.client') and f.count('.') == 2:
            out.append(f.split('.')[0])
    return out


class Champion:
    """a champion's data: .stats (record_stats), .spells [4 names], .passive, .attacks [names], .spell(name) ->
    SpellObject value, .skill_priority / .skill_early (recommended order), .items (recommended item ids by block)"""
    def __init__(self, name):
        self.name = name
        self.ents = BT.entries(os.path.join(GAME, 'Champions', f'{name}.wad.client'),
                               f'data/characters/{name.lower()}/{name.lower()}.bin')
        rec = _root_record(self.ents, name)
        if rec is None:
            raise KeyError(f'no CharacterRecord for {name}')
        self.record = rec
        self.stats = record_stats(rec)
        self.spells = [str(s).split('/')[-1] for s in rec.get('spellNames', [])][:4]
        self.passive = rec.get('passiveSpell') or ''
        self.extra = [str(s).split('/')[-1] for s in rec.get('extraSpells', [])]
        ba = rec.get('basicAttack') or {}
        self.attacks, self.attack_weights = attack_variants(rec, first_name(ba.get('mAttackName')) or f'{name}BasicAttack')
        self.crit_attack = next((first_name(a.get('mAttackName')) for a in rec.get('critAttacks', []) or [] if a.get('mAttackName')), None)
        self.objects = {v['mScriptName']: v for k, c, v in self.ents if c == 'SpellObject' and v.get('mScriptName')}
        self.by_key = {k: v for k, c, v in self.ents if c == 'SpellObject'}
        self.champion_id = int(((rec.get('characterToolData') or {}).get('championId')) or 0)
        self.melee = self.stats['range'] < 300
        self.skill_priority, self.skill_early = [3, 0, 2, 1], []
        for k, c, v in self.ents:
            if c == 'RecSpellRankUpInfolist':
                infos = [i for i in v.get('RecSpellRankUpInfos', []) if i.get('MapId') == 11] or v.get('RecSpellRankUpInfos', [])
                if infos:
                    self.skill_priority = list(infos[0].get('mDefaultPriority', self.skill_priority))
                    self.skill_early = list(infos[0].get('mEarlyLevelOverrides', []))
        self._items = None

    def spell(self, name):
        return self.objects.get(name) or next((v for n, v in self.objects.items() if n.lower() == str(name).lower()), None)

    def spell_data(self, name):
        return (self.spell(name) or {}).get('mSpell') or {}

    def attack_missile_speed(self):
        sp = self.spell_data(self.attacks[0])
        return float(sp.get('missileSpeed', 0.0) or 0.0)

    @property
    def items(self):
        """recommended items on Summoner's Rift: {'start': [[ids]...], 'core': [ids in order]} - the champion's own
        ItemRecommendationOverrideSet for the CLASSIC mode; another mode's item variants (ids above 9999) are read
        as their Rift item; a champion without a list gets its class's usual items [a]"""
        if self._items is None:
            import items16
            db = items16.items()
            keys = {BT.key_of(f'Items/{iid}'): iid for iid in db}

            def rift(i):
                iid = keys.get(i)
                if iid is None:
                    return None
                if iid > 9999 and (iid % 10000) in db:
                    iid = iid % 10000
                return iid if iid <= 9999 else None
            start, core = [], []
            classic = BT.key_of('CLASSIC')
            for k, c, v in self.ents:
                if c != 'ItemRecommendationOverrideSet':
                    continue
                ovs = v.get('mOverrides', [])
                best = [o for o in ovs if any(x.get('mMapID') == 11 and x.get('mModeNameStringId') == classic for x in o.get('mOverrideContexts', []))] or                     [o for o in ovs if any(x.get('mMapID') == 11 for x in o.get('mOverrideContexts', []))] or ovs
                if best:
                    o = best[0]
                    start = [[x for x in (rift(i) for i in b.get('items', [])) if x] for b in o.get('StartingItemBundles', [])]
                    for r in o.get('mRecItemRanges', []):
                        for i in r.get('items', []):
                            x = rift(i)
                            if x and x not in core:
                                core.append(x)
            tags = str((self.record.get('characterToolData') or {}).get('searchTags', '')).lower()
            if not core:
                if 'mage' in tags or 'support' in tags:
                    core = [6655, 3020, 3157, 3089, 3135, 3116]
                elif 'marksman' in tags:
                    core = [3031, 3006, 3094, 3036, 3072, 3046]
                elif 'tank' in tags:
                    core = [3068, 3047, 3075, 3065, 3143, 3742]
                else:
                    core = [3078, 3047, 3071, 3053, 3742, 6333]
            if not [s for s in start if s]:
                start = [[1056, 2003, 2003]] if ('mage' in tags or 'support' in tags) else [[1055, 2003]]
            self._items = {'start': [s for s in start if s], 'core': core}
        return self._items


def champion(name):
    if name not in _champs:
        _champs[name] = Champion(name)
    return _champs[name]


def champion_index():
    """every playable champion: [{'alias', 'id', 'tags' [primary, secondary], 'melee', 'square', 'load'}] (square /
    load = the 64-bit hashes of its square icon and loading screen art in its own wad), kept as
    data/exe1620/gamedata/champions.json"""
    p = os.path.join(OUT, 'champions.json')
    if os.path.exists(p):
        return json.load(open(p))
    out = []
    for name in champions():
        try:
            c = champion(name)
        except Exception:
            continue
        if 'Champion' not in c.stats['tags'] or not c.champion_id or len(c.spells) < 4:
            continue
        tool = c.record.get('characterToolData') or {}
        skin = BT.entries(os.path.join(GAME, 'Champions', f'{name}.wad.client'), f'data/characters/{name.lower()}/skins/skin0.bin')
        sv = next((v for k, cl, v in skin if cl == 'SkinCharacterDataProperties'), {})

        def h(x):
            if isinstance(x, list):
                x = x[0] if x else None
            return x.strip('{}') if isinstance(x, str) and x.startswith('{') else None
        out.append({'alias': name, 'id': c.champion_id, 'melee': c.melee,
                    'tags': [str(tool.get('searchTags', '')).lower(), str(tool.get('searchTagsSecondary', '')).lower()],
                    'square': h(sv.get('iconSquare')), 'load': h((sv.get('loadscreen') or {}).get('image'))})
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(p, 'w'), indent=0)
    return out


ROLE_TAGS = {'TOP': ('fighter', 'tank'), 'JUNGLE': ('assassin', 'fighter', 'tank'), 'MIDDLE': ('mage', 'assassin'),
             'BOTTOM': ('marksman',), 'UTILITY': ('support',)}


def random_roster(player=None, seed=None):
    """ten champions for a match: the player's (or any) first, the other nine by position (top, jungle, middle,
    bottom, support of each team) from the champions whose class fits it, no champion twice"""
    import random
    rng = random.Random(seed)
    idx = champion_index()
    roles = ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY']
    taken = {player} if player else set()
    out = []
    for i in range(10):
        role = roles[i % 5]
        if i == 0 and player:
            out.append(player)
            continue
        want = ROLE_TAGS[role]
        pool = [c['alias'] for c in idx if c['alias'] not in taken and c['tags'][0] in want and (role != 'JUNGLE' or c['melee'])]
        pool = pool or [c['alias'] for c in idx if c['alias'] not in taken]
        pick = rng.choice(pool)
        taken.add(pick)
        out.append(pick)
    return out


# The "package" hash a cast (1215 +0x18+0xa0) and a buff (435 +0x5c) carry: one value per champion, another for
# summoner spells and items, another for the map's own units [m: both live recordings]. The function that makes it is
# not found (no plain hash of the champion's name or paths gives these); a champion not listed gets 0.
PACKAGE = {'Zaahen': 0x3253bcf4, 'Morgana': 0xd125fcec, 'Xerath': 0xb38c545b, 'Galio': 0x5182b611, 'Garen': 0xc14782c8,
           'Lissandra': 0xb001cd00, 'Tryndamere': 0x0902fd10, 'Tristana': 0x05381e83, 'MissFortune': 0x2f35eaa4,
           'MasterYi': 0xad56e239, 'Lux': 0x55ece39a, 'Yasuo': 0xfef52c44, 'Brand': 0x6d86a702, 'Velkoz': 0x96b87232,
           'Jinx': 0x037705e2, 'Darius': 0x3d5d5a79, 'Braum': 0x7b379ac0, 'Sion': 0x23f077f6}
PACKAGE_GLOBAL, PACKAGE_MAP = 0xd553ffbd, 0x29781980


def package_hash(name):
    """the hash a unit's casts, buffs and effects carry for the unit's 'package' [m: the 18 champions above and
    SRU_RiftHerald, all exact]: the sdbm hash (h = c + 65599 h, 32 bits) of the lower-cased string
    "[Character]" + <character name> + <eleven more characters>. The eleven characters are the same for every
    unit and not named yet; their own sdbm is 0xaef9ccfa, which is all the formula needs."""
    h = 0
    for c in ('[character]' + name.lower()).encode():
        h = (c + 65599 * h) & 0xffffffff
    return (h * PACKAGE_K11 + 0xaef9ccfa) & 0xffffffff


PACKAGE_K11 = pow(65599, 11, 1 << 32)


def level_stat(base, per_level, level):
    """LoL's growth of a per-level statistic"""
    n = level - 1
    return base + per_level * n * (0.7025 + 0.0175 * n)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'champion':
        c = champion(sys.argv[2])
        print(json.dumps(c.stats, indent=0).replace('\n', ' '))
        print('spells', c.spells, 'passive', c.passive, 'attacks', c.attacks, 'crit', c.crit_attack, 'id', c.champion_id)
        print('skill priority', c.skill_priority, 'early', c.skill_early, 'items', c.items)
        sys.exit()
    if len(sys.argv) > 2 and sys.argv[1] == 'unit':
        print(json.dumps(unit(sys.argv[2]), indent=0).replace('\n', ' '))
        sys.exit()
    m = build_map()
    print('lanes', {k: (len(v), v[0], v[-1]) for k, v in m['lanes'].items()})
    print('barracks', [(b['team'], b['lane'], b['pos'], b['config']) for b in m['barracks']])
    print('structures', len(m['structures']), [(s['character'], s['team'], s['lane'], s['position'], s['type'], s['pos']) for s in m['structures']][:40])
    print('camps', len(m['camps']), [(c['icon'], c['pos']) for c in m['camps']])
    print('monsters', len(m['monsters']), [(x['character'], x['pos']) for x in m['monsters']][:12])
    print('waves', {k: [(u['type'], u['character']) for u in v['units']] for k, v in m['waves'].items()})
    print('xp per level', m['xp_per_level'][:18])
    print('death', m['death_times'])
    print('locators', list(m['locators'])[:20])


_wiki = None


def wiki(champ, slot):
    """what the LoL wiki says about a champion's ability ('Q' 'W' 'E' 'R', or 'P' the passive): tools/wiki16.py's
    gamedata/wiki16.json (cooldown, cost, damage, crowd control by rank, the text). The wiki's patch is not the
    client's: used only where the game's own data gives nothing. None when the wiki file has no such ability"""
    global _wiki
    if _wiki is None:
        p = os.path.join(ROOT, 'data', 'exe1620', 'gamedata', 'wiki16.json')
        _wiki = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    return (_wiki.get(champ) or {}).get(slot)
