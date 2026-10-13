"""The engine under Riot's BuildingBlocks scripts (core/bb.py runs them): when their events fire and what their
engine blocks do in our match.

Events [the 1.31 scripts' event tables; when the engine fires them is our reading, checked against the replays]:
  a cast         SelfExecuteBuildingBlocks (Owner = Caster = the champion), then TargetExecuteBuildingBlocks for its
                 target (Target = the unit)
  a buff         OnBuffActivateBuildingBlocks when added; BuffOnUpdateActionsBuildingBlocks on every script update
                 while it lasts (8 frames); OnBuffDeactivateBuildingBlocks when it ends (time out / removed);
                 Owner = the unit holding it, Attacker = Caster = who gave it; its InstanceVars live as long as it
Blocks (each turns into the packets the real server sends for it): BBSpellBuffAdd (435) / BBSpellBuffRemove (262),
BBApplyDamage (150, through Game.deal), BBIncHealth (699 heal event), BBSpellEffectCreate (10) /
BBSpellEffectRemove (584). The rest are counted as missing (BBRuntime.missing) until written.
"""
import itertools
import os

from . import gamedata as G
from . import packets as P
from .bb import BBRuntime
from .units import dist

# LoL's BuffType numbers as the packets carry them [m: 435 +0x38 in the replays: 5 stun, 7 silence, 11 slow, 12
# snare, 13 damage (Burning, ignite), 27 counter, 30 knock-up, 31 knock-back]
BUFF_TYPES = ['Internal', 'Aura', 'CombatEnchancer', 'CombatDehancer', 'SpellShield', 'Stun', 'Invisibility', 'Silence',
              'Taunt', 'Berserk', 'Polymorph', 'Slow', 'Snare', 'Damage', 'Heal', 'Haste', 'SpellImmunity',
              'PhysicalImmunity', 'Invulnerability', 'AttackSpeedSlow', 'NearSight', 'Currency', 'Fear', 'Charm', 'Poison',
              'Suppression', 'Blind', 'Counter', 'Shred', 'Flee', 'Knockup', 'Knockback', 'Disarm', 'Grounded', 'Drowsy',
              'Asleep', 'Obscured', 'ClickProofToEnemies', 'Unkillable']
BUFF_TYPE = {'BUFF_' + n: i for i, n in enumerate(BUFF_TYPES)}
DAMAGE_TYPE = {'PHYSICAL_DAMAGE': P.PHYSICAL, 'MAGIC_DAMAGE': P.MAGIC, 'TRUE_DAMAGE': P.TRUE}
SOURCE = {'DAMAGESOURCE_ATTACK': P.SRC_ATTACK, 'DAMAGESOURCE_SPELL': P.SRC_DIRECT, 'DAMAGESOURCE_SPELLAOE': P.SRC_DIRECT,
          'DAMAGESOURCE_SPELLPERSIST': P.SRC_PERIODIC, 'DAMAGESOURCE_PERIODIC': P.SRC_PERIODIC,
          'DAMAGESOURCE_PROC': P.SRC_DIRECT, 'DAMAGESOURCE_INTERNALRAW': P.SRC_DIRECT}


import re

STAT_FN = re.compile(r'^(Get|Inc)(Permanent)?(Flat|PercentMultiplicative|Percent)(\w+?)Mod$')
STAT_KEYS = {('Flat', 'PhysicalDamage'): 'ad', ('Flat', 'MagicDamage'): 'ap', ('Flat', 'Armor'): 'armor',
             ('Flat', 'SpellBlock'): 'mr', ('Flat', 'HPPool'): 'hp', ('Flat', 'PARPool'): 'par', ('Flat', 'MovementSpeed'): 'ms',
             ('Percent', 'MovementSpeed'): 'ms_pct', ('PercentMultiplicative', 'MovementSpeed'): 'ms_pct',
             ('Percent', 'AttackSpeed'): 'as', ('PercentMultiplicative', 'AttackSpeed'): 'as', ('Flat', 'CritChance'): 'crit',
             ('Percent', 'LifeSteal'): 'lifesteal', ('Percent', 'SpellVamp'): 'omnivamp', ('Flat', 'HPRegen'): 'hp_regen',
             ('Percent', 'HPRegen'): 'hp_regen_pct', ('Flat', 'PARRegen'): 'par_regen', ('Percent', 'PARRegen'): 'par_regen_pct',
             ('Flat', 'AttackRange'): 'range', ('Percent', 'Cooldown'): 'haste', ('Flat', 'ArmorPenetration'): 'lethality',
             ('Percent', 'ArmorPenetration'): 'armor_pen', ('Flat', 'MagicPenetration'): 'magic_pen',
             ('Percent', 'MagicPenetration'): 'magic_pen_pct', ('Flat', 'CritDamage'): 'crit_damage',
             ('Percent', 'PhysicalDamage'): 'ad_pct', ('Percent', 'MagicDamage'): 'ap_pct', ('Percent', 'Armor'): 'armor_pct',
             ('Percent', 'SpellBlock'): 'mr_pct', ('Percent', 'Hardness'): 'tenacity', ('Percent', 'CCReduction'): 'tenacity',
             ('Flat', 'Dodge'): 'dodge', ('Percent', 'Dodge'): 'dodge', ('Percent', 'BubbleRadius'): 'sight_pct',
             ('Percent', 'EXPBonus'): 'xp_pct', ('Flat', 'GoldPer10'): 'gold10', ('Flat', 'PhysicalReduction'): 'phys_red',
             ('Flat', 'MagicReduction'): 'magic_red', ('Percent', 'PhysicalReduction'): 'phys_red_pct',
             ('Percent', 'MagicReduction'): 'magic_red_pct'}


# what the engine sends for a cast whatever the spell's script does [m: in the frame of every Garen cast: 635 its
# cooldown, 280 / 1088 / 904 animations, 827 the autocast state, 683 the attack range]: from the casts' templates
ENGINE_PIDS = frozenset({635, 280, 1088, 904, 827, 683, 326})


class Buff:
    __slots__ = ('id', 'name', 'owner', 'caster', 'type', 'until', 'stacks', 'key', 'level', 'alive')


class BBEngine:
    def __init__(self, game, champions=()):
        self.g = game
        self.champions = set(champions)
        self.rt = BBRuntime(game, extra=[os.path.join(G.ROOT, 'data', 'bb16', 'scripts', c) for c in self.champions])
        self.ids = itertools.count(1)
        self.buffs = []
        self.effects = {}                 # effect id the scripts hold -> our effect
        rt = self.rt
        rt.blocks.update({
            'BBSpellBuffAdd': self.buff_add,
            'BBSpellBuffRemove': self.buff_remove,
            'BBSpellBuffRemoveCurrent': self.buff_remove_current,
            'BBApplyDamage': self.apply_damage,
            'BBApplyStun': self.apply_stun,
            'BBApplySilence': self.apply_silence,
            'BBApplyRoot': self.apply_root,
            'BBApplyFear': self.apply_fear,
            'BBApplyTaunt': self.apply_taunt,
            'BBApplySlow': self.apply_slow,
            'BBIncPAR': self.inc_par,
            'BBIncHealth': self.inc_health,
            'BBSpellEffectCreate': self.effect_create,
            'BBSpellEffectRemove': self.effect_remove,
            'BBSetSpell': self.set_spell,
            'BBOverrideAutoAttack': self.override_attack,
            'BBRemoveOverrideAutoAttack': self.remove_override,
            'BBForEachUnitInTargetArea': self.each_in_area,
            'BBGetCastInfo': self.get_cast_info,
            'BBGetTeamID': self.get_team_id,
            'BBGetSkinID': self.get_skin_id,
            'BBSetCanCastWhileDisabled': lambda v, n: None,
            'BBCancelAutoAttack': lambda v, n: None,
            'BBPreloadParticle': lambda v, n: None,
            'BBPreloadSpell': lambda v, n: None,
            'BBPreloadCharacter': lambda v, n: None,
        })
        rt.funcs.update({
            'GetTime': lambda *a: self.g.t,
            'GetGameTime': lambda *a: self.g.t,
            'GetHealth': lambda u=None: u.hp if u is not None else 0.0,
            'GetMaxHealth': lambda u=None: u.max_hp if u is not None else 0.0,
            'GetLevel': lambda u=None: getattr(u, 'level', 1),
            'SpellBuffCount': self.spell_buff_count,
            'SpellBuffRemove': self.spell_buff_remove_func,
            'HasBuffOfType': self.has_buff_of_type,
            'HasPARType': lambda u=None, t=None: True,
            'GetTotalAttackDamage': lambda u=None: float(getattr(u, 'ad', 0.0)) if u is not None else 0.0,
            'GetArmor': lambda u=None: float(getattr(u, 'armor', 0.0)) if u is not None else 0.0,
            'GetSpellBlock': lambda u=None: float(getattr(u, 'mr', 0.0)) if u is not None else 0.0,
            'GetPosition': lambda u=None: getattr(u, 'pos', (0.0, 0.0)) if u is not None else (0.0, 0.0),
            'Xloc': lambda p=None: p.pos[0] if hasattr(p, 'pos') else (p[0] if isinstance(p, (tuple, list)) else 0.0),
            'Yloc': lambda p=None: 0.0,
            'Zloc': lambda p=None: p.pos[1] if hasattr(p, 'pos') else (p[-1] if isinstance(p, (tuple, list)) else 0.0),
            'DistanceBetweenObjects': lambda a=None, b=None: dist(a.pos, b.pos) if a and b and hasattr(a, 'pos') and hasattr(b, 'pos') else 0.0,
            'DistanceBetweenObjectAndPoint': lambda a=None, p=None: dist(a.pos, p if isinstance(p, (tuple, list)) else getattr(p, 'pos', (0.0, 0.0))) if a and hasattr(a, 'pos') else 0.0,
            'DistanceBetweenPoints': lambda a=(0, 0), b=(0, 0): dist(a, b),
            'IsDead': lambda u=None: not getattr(u, 'alive', False) if u is not None else True,
            'IsMelee': lambda u=None: bool(getattr(u, 'is_melee', False)) if u is not None else False,
            'IsObjectHero': lambda u=None: bool(getattr(u, 'is_hero', False)) if u is not None else False,
            'IsTurretAI': lambda u=None: bool(getattr(u, 'is_turret', False) or getattr(u, 'kind', '') == 'turret') if u is not None else False,
            'IsObjectAI': lambda u=None: bool(hasattr(u, 'ai') or hasattr(u, 'brain')) if u is not None else False,
            'GetTeamID': lambda u=None: getattr(u, 'team', 0) if u is not None else 0,
            'Make3DPoint': lambda x=0.0, y=0.0, z=0.0: (float(x), float(z)),
        })
        rt.fallback = self.stat_function
        game.systems.append(self.tick)

    # ------------------------------------------------------------------ running scripts
    def ctx(self, owner, target=None, caster=None, level=1):
        return {'Owner': owner, 'Target': target or owner, 'Caster': caster or owner, 'Attacker': caster or owner,
                'Level': level}

    def run(self, script, event, ctx, iid=None, init=None):
        if not self.rt.has(script, event):
            return None
        owner = ctx.get('Owner')
        try:
            return self.rt.vm.call('Glue_Run', script.lower(), event, ctx, iid, getattr(owner, 'net', None), init)
        except Exception as e:                           # noqa: BLE001 - a script error is reported, the match goes on
            self.rt.missing['error ' + script + '.' + event + ': ' + str(e)[:80]] += 1
            return None

    def handles(self, hero):
        return hero.name in self.champions

    def cast(self, hero, script, target=None, level=1, delay=0.0, ctx=None):
        """a cast of a scripted spell: executes SelfExecuteBuildingBlocks on caster"""
        def go(t=None):
            if not hero.alive:
                return
            self.run(script, 'SelfExecuteBuildingBlocks', self.ctx(hero, target, hero, level))
        if delay > 0:
            self.g.at(self.g.t + delay, go)
        else:
            go()

    def spell_hit(self, hero, script, target, level=1):
        """a spell or missile of a scripted champion hit a target unit:
        runs TargetExecuteBuildingBlocks on target -> returns True if handled by script"""
        if not self.rt.has(script, 'TargetExecuteBuildingBlocks'):
            return False
        self.run(script, 'TargetExecuteBuildingBlocks', self.ctx(hero, target, hero, level))
        return True

    def attack_hit(self, hero, tgt):
        """a basic attack of a scripted champion landed: an overridden attack is its spell's hit; then every buff
        it holds hears of the hit (BuffOnHitUnit) -> True when the attack's damage was the script's"""
        g = self.g
        over = getattr(hero, 'attack_override', None)
        done = False
        if over is not None:
            from .spells import info
            inf = info(hero.champ, over)
            amount, dtype = g.spells.damage_of(hero, inf, max(1, max(hero.spell_levels))) if inf is not None else (0.0, P.PHYSICAL)
            g.deal(hero, tgt, hero.ad + (amount or 0.0), dtype or P.PHYSICAL, basic=True, spell_hash=P.elf(over))
            done = True
        for b in [b for b in self.buffs if b.owner is hero and b.alive]:
            self.run(b.name, 'BuffOnHitUnitBuildingBlocks', self.ctx(hero, tgt, b.caster, b.level), iid=b.id)
        return done

    # ------------------------------------------------------------------ buffs
    def buff_add(self, v, n):
        g, sp = self.g, self.g.spells
        tgt, src = v.get('Target'), v.get('Attacker') or v.get('Target')
        name = v.get('BuffName') or self.script_name(v.get('__spell'))
        if tgt is None or not name or sp is None or not getattr(tgt, 'alive', False):
            return None
        dur = float(v.get('Duration') or 0.0) or 25000.0
        btype = BUFF_TYPE.get(v.get('BuffType'), 0)
        key = ('bb', name)
        old = getattr(tgt, 'buff_list', {}).get(key)
        mode = v.get('BuffAddType') or 'BUFF_REPLACE_EXISTING'
        if old is not None and mode == 'BUFF_RENEW_EXISTING':
            b = old['bb']
            b.until = g.t + dur
            old['until'] = b.until
            g.q += g.pk.buff_count(tgt.net, old['slot'], src.net, dur, b.stacks)
            sp.buffs.append([b.until, tgt, key])
            return None
        b = Buff()
        b.id, b.name, b.owner, b.caster, b.type, b.until, b.stacks = next(self.ids), name, tgt, src, btype, g.t + dur, int(v.get('NumberOfStacks') or 1)
        b.key, b.level, b.alive = key, getattr(src, 'level', 1), True
        if old is not None:
            self.end(old['bb'], quiet=True)
        sp.buff(src, tgt, _Named(name), btype, dur, key=key, undo=lambda b=b: self.end(b))
        tgt.buff_list[key]['bb'] = b
        self.buffs.append(b)
        self.run(name, 'OnBuffActivateBuildingBlocks', self.ctx(tgt, tgt, src, b.level), iid=b.id, init=v.get('__buffvars'))
        if self.rt.has(name, 'BuffOnUpdateActionsBuildingBlocks'):
            # every script update (0.25 s), or at the rate the buff was given with (TickRate) [a]
            rate = float(v.get('TickRate') or 0.0)
            upd = lambda t, b=b: b.alive and self.run(
                b.name, 'BuffOnUpdateActionsBuildingBlocks', self.ctx(b.owner, b.owner, b.caster, b.level), iid=b.id)
            if rate > 0:
                def tick(t, b=b, rate=rate):
                    if b.alive:
                        upd(t)
                        g.at(g.t + rate, tick)
                g.at(g.t + rate, tick)
            else:
                g.script_timer(0.25, upd, alive=lambda b=b: b.alive)
        return None

    def end(self, b, quiet=False):
        if not b.alive:
            return
        b.alive = False
        if b in self.buffs:
            self.buffs.remove(b)
        self.run(b.name, 'OnBuffDeactivateBuildingBlocks', self.ctx(b.owner, b.owner, b.caster, b.level), iid=b.id)
        self.rt.vm.call('Glue_Drop', b.id)

    def buff_remove(self, v, n):
        tgt, name = v.get('Target'), v.get('BuffName')
        if tgt is None or not name:
            return None
        self.remove_key(tgt, ('bb', name))

    def buff_remove_current(self, v, n):
        """the buff whose script runs takes itself away"""
        tgt = v.get('Target') or v.get('Owner')
        name = self.script_name(v.get('__spell'))
        if tgt is not None and name:
            for b in list(self.buffs):
                if b.owner is tgt and b.name.lower() == name.lower():
                    self.remove_key(tgt, b.key)

    def remove_key(self, u, key):
        cur = getattr(u, 'buff_list', {}).get(key)
        if cur is None:
            return
        del u.buff_list[key]
        if cur.get('known', True):
            self.g.tell_all(self.g.pk.buff_remove(u.net, cur['slot'], cur['hash']))
        if cur.get('undo'):
            cur['undo']()

    # ------------------------------------------------------------------ damage, health
    def apply_damage(self, v, n):
        src, tgt = v.get('Attacker'), v.get('Target')
        if src is None or tgt is None or not getattr(tgt, 'alive', False):
            return None
        # [1.31 scripts: Annie's Disintegrate 85-245 + SpellDamageRatio 0.7 = its AP ratio of the time; ignite (true
        # damage) carries PhysicalDamageRatio 1 and no AD in its damage] Damage x PercentOfAttack, + SpellDamageRatio
        # x AP; PhysicalDamageRatio x bonus AD for physical damage only [a]
        dtype = DAMAGE_TYPE.get(v.get('DamageType'), P.MAGIC)
        amount = self.get_num(v, 'Damage', 0.0) * self.get_num(v, 'PercentOfAttack', 1.0)
        bd = self.get_num(v, 'BaseDamage', 0.0)
        if bd > 0:
            amount = max(amount, bd)
        if v.get('DamageFromData') and getattr(src, 'champ', None) is not None:
            from .spells import info
            inf = info(src.champ, v.get('SpellName') or self.current_name(v))
            if inf is not None:
                amt, dt2 = self.g.spells.damage_of(src, inf, max(1, max(src.spell_levels)))
                amount, dtype = max(amount, amt or 0.0), dt2 or dtype
        ap_ratio = self.get_num(v, 'APRatio', self.get_num(v, 'SpellDamageRatio', 0.0))
        if ap_ratio > 0:
            amount += ap_ratio * getattr(src, 'ap', 0.0)
        bad_ratio = self.get_num(v, 'BonusADRatio', self.get_num(v, 'PhysicalDamageRatio', 0.0) if dtype == P.PHYSICAL else 0.0)
        if bad_ratio > 0:
            amount += bad_ratio * max(0.0, getattr(src, 'ad', 0.0) - getattr(src, 'base_ad', 0.0))
        ad_ratio = self.get_num(v, 'ADRatio', 0.0)
        if ad_ratio > 0:
            amount += ad_ratio * getattr(src, 'ad', 0.0)
        hp_ratio = self.get_num(v, 'BonusHPRatio', 0.0)
        if hp_ratio > 0:
            amount += hp_ratio * max(0.0, getattr(src, 'max_hp', 0.0) - getattr(src, 'base_hp', 0.0))
        source = SOURCE.get(v.get('SourceDamageType'), P.SRC_DIRECT)
        self.g.deal(src, tgt, amount, dtype, basic=v.get('SourceDamageType') == 'DAMAGESOURCE_ATTACK', source=source,
                    spell_hash=P.elf(v.get('SpellName') or self.current_name(v)))
        return None

    def current_name(self, v):
        return self.script_name(v.get('__spell')) or ''

    def script_name(self, key):
        """a script's own name with its letters' case (the scripts are found by lower case)"""
        if not key:
            return None
        p = self.rt.files.get(key.lower())
        import os
        return os.path.splitext(os.path.basename(p))[0] if p else key

    def get_num(self, v, key, default=0.0):
        val = v.get(key)
        if val is None:
            return default
        if isinstance(val, (list, tuple)):
            src = v.get('Attacker') or v.get('Owner') or v.get('Caster')
            lvl = v.get('Level') or (max(1, max(getattr(src, 'spell_levels', [1]))) if src else 1)
            idx = max(0, min(len(val) - 1, int(lvl) - 1))
            return float(val[idx])
        if isinstance(val, dict):
            src = v.get('Attacker') or v.get('Owner') or v.get('Caster')
            lvl = v.get('Level') or (max(1, max(getattr(src, 'spell_levels', [1]))) if src else 1)
            return float(val.get(lvl, val.get(1, default)))
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def inc_health(self, v, n):
        tgt, healer = v.get('Target'), v.get('Healer') or v.get('Target')
        d = self.get_num(v, 'Delta', 0.0)
        if tgt is None or d == 0.0:
            return None
        got = tgt.heal(d) if d > 0 else 0.0
        if d < 0:
            tgt.set_hp(tgt.hp + d)
        return None

    def apply_stun(self, v, n):
        src, tgt = v.get('Attacker') or v.get('Owner'), v.get('Target')
        if src is None or tgt is None or not getattr(tgt, 'alive', False):
            return None
        dur = self.get_num(v, 'Duration', 0.0)
        if dur > 0 and self.g.spells is not None:
            self.g.spells.cc(src, tgt, _Named(self.current_name(v) or 'Stun'), BUFF_TYPE.get('BUFF_Stun', 5), dur, stun=True)
        return None

    def apply_silence(self, v, n):
        src, tgt = v.get('Attacker') or v.get('Owner'), v.get('Target')
        if src is None or tgt is None or not getattr(tgt, 'alive', False):
            return None
        dur = self.get_num(v, 'Duration', 0.0)
        if dur > 0 and self.g.spells is not None:
            self.g.spells.cc(src, tgt, _Named(self.current_name(v) or 'Silence'), BUFF_TYPE.get('BUFF_Silence', 7), dur, silence=True)
        return None

    def apply_root(self, v, n):
        src, tgt = v.get('Attacker') or v.get('Owner'), v.get('Target')
        if src is None or tgt is None or not getattr(tgt, 'alive', False):
            return None
        dur = self.get_num(v, 'Duration', 0.0)
        if dur > 0 and self.g.spells is not None:
            self.g.spells.cc(src, tgt, _Named(self.current_name(v) or 'Snare'), BUFF_TYPE.get('BUFF_Snare', 12), dur, root=True)
        return None

    def apply_fear(self, v, n):
        src, tgt = v.get('Attacker') or v.get('Owner'), v.get('Target')
        if src is None or tgt is None or not getattr(tgt, 'alive', False):
            return None
        dur = self.get_num(v, 'Duration', 0.0)
        if dur > 0 and self.g.spells is not None:
            self.g.spells.cc(src, tgt, _Named(self.current_name(v) or 'Fear'), BUFF_TYPE.get('BUFF_Fear', 22), dur, stun=True)
        return None

    def apply_taunt(self, v, n):
        src, tgt = v.get('Attacker') or v.get('Owner'), v.get('Target')
        if src is None or tgt is None or not getattr(tgt, 'alive', False):
            return None
        dur = self.get_num(v, 'Duration', 0.0)
        if dur > 0 and self.g.spells is not None:
            self.g.spells.cc(src, tgt, _Named(self.current_name(v) or 'Taunt'), BUFF_TYPE.get('BUFF_Taunt', 8), dur, stun=True)
        return None

    def apply_slow(self, v, n):
        src, tgt = v.get('Attacker') or v.get('Owner'), v.get('Target')
        if src is None or tgt is None or not getattr(tgt, 'alive', False):
            return None
        dur = self.get_num(v, 'Duration', 0.0)
        pct = self.get_num(v, 'SlowPercent', self.get_num(v, 'Multiplier', 0.3))
        if dur > 0 and self.g.spells is not None:
            self.g.spells.slow(src, tgt, _Named(self.current_name(v) or 'Slow'), pct, dur)
        return None

    def inc_par(self, v, n):
        tgt = v.get('Target') or v.get('Owner')
        d = float(v.get('Delta') or 0.0)
        if tgt is not None and d != 0 and hasattr(tgt, 'set_par'):
            tgt.set_par(tgt.par + d)
        return None

    def get_cast_info(self, v, n):
        info_type = v.get('Info')
        u = v.get('Owner') or v.get('Caster')
        val = 0
        if info_type == 'GetPARCost' and u is not None and getattr(u, 'champ', None) is not None:
            sname = self.current_name(v)
            from .spells import info
            inf = info(u.champ, sname)
            if inf is not None:
                val = inf.mana(getattr(u, 'level', 1))
        return {'Dest': val}

    def get_team_id(self, v, n):
        u = v.get('Target') or v.get('Owner')
        return {'Dest': getattr(u, 'team', 0)}

    def get_skin_id(self, v, n):
        u = v.get('Unit') or v.get('Owner')
        return {'SkinID': getattr(u, 'skin', 0)}

    def spell_buff_count(self, u=None, name='', caster=None):
        if u is None or not name:
            return 0
        name_l = str(name).lower()
        cnt = 0
        for b in self.buffs:
            if b.owner is u and b.alive and b.name.lower() == name_l:
                if caster is None or b.caster is caster:
                    cnt += b.stacks
        if cnt == 0 and hasattr(u, 'buff_list'):
            for (kname, _), binfo in u.buff_list.items():
                if str(kname).lower() == name_l:
                    cnt += getattr(binfo.get('bb'), 'stacks', 1)
        return cnt

    def spell_buff_remove_func(self, u=None, name='', caster=None):
        if u is not None and name:
            self.remove_key(u, ('bb', str(name)))
        return None

    def has_buff_of_type(self, u=None, btype=None):
        if u is None or not hasattr(u, 'buff_list'):
            return False
        bt = BUFF_TYPE.get(str(btype), -1) if isinstance(btype, str) else btype
        for (_, t), binfo in u.buff_list.items():
            if t == bt and binfo.get('until', 0) > self.g.t:
                return True
        return False

    # ------------------------------------------------------------------ slots, attacks, areas
    def set_spell(self, v, n):
        u, slot, name = v.get('Target') or v.get('Owner'), v.get('SlotNumber'), v.get('SpellName')
        if u is None or slot is None or not name:
            return None
        self.g.q += self.g.pk.spell_in_slot(u.net, int(slot), name)
        if int(slot) < 4 and getattr(u, 'slot_names', None) is not None:
            u.slot_names[int(slot)] = name
        return None

    def override_attack(self, v, n):
        u = v.get('Owner')
        if u is not None:
            u.attack_override = v.get('SpellName')
        return None

    def remove_override(self, v, n):
        u = v.get('Owner')
        if u is not None:
            u.attack_override = None
        return None

    def each_in_area(self, v, n):
        """the units around a place (RangeFromData: the spell's own radius) -> __each"""
        g = self.g
        center, att = v.get('Center'), v.get('Attacker')
        rng = v.get('Range')
        if rng is None and v.get('RangeFromData') and att is not None and getattr(att, 'champ', None) is not None:
            from .spells import info
            inf = info(att.champ, v['RangeFromData'])
            rng = (inf.radius(max(1, max(att.spell_levels))) if inf is not None else 0.0) or 325.0
        if center is None or rng is None:
            return None
        cpos = self.place(center) or center.pos
        flags = str(v.get('Flags') or '')
        out = []
        for o in g.units.values():
            if not o.alive or not o.targetable or o is att or o.kind == 'plant':
                continue
            if 'AffectEnemies' in flags and att is not None and o.team == att.team:
                continue
            if dist(o.pos, cpos) <= float(rng) + o.radius:
                out.append(o)
        return {'__each': out}

    # ------------------------------------------------------------------ effects
    def effect_create(self, v, n):
        fx = self.g.fx
        name = (v.get('EffectName') or '').replace('.troy', '')
        key = v.get('EffectKey')
        if fx is None or not (name or key):
            return None
        bind = v.get('BindObject') or v.get('TargetObject')
        caster = v.get('SpecificUnitOnly') or bind
        if key:
            made = fx.create(int(key), caster, bound=bind, place=self.place(v.get('Pos'))) if fx.seen(caster, bind) else None
        else:
            made = fx.shared(name, caster, bound=bind, place=self.place(v.get('Pos')))
        if made is None:
            return None
        eid = next(self.ids)
        self.effects[eid] = made
        return {'EffectID': eid}

    def effect_remove(self, v, n):
        eid = v.get('EffectID')
        made = self.effects.pop(eid, None) if eid is not None else None
        if made is not None and self.g.fx is not None:
            self.g.fx.remove(made)
        return None

    def place(self, p):
        if p is None:
            return None
        if hasattr(p, 'pos'):
            return p.pos
        return None

    # ------------------------------------------------------------------ stats
    def stat_function(self, name):
        """Get/Inc[Permanent](Flat|Percent|PercentMultiplicative)<Stat>Mod(unit[, delta]) [the 1.31 scripts' names;
        a buff's Inc...Mod in BuffOnUpdateStats lasts until the next update, IncPermanent... for good]"""
        m = STAT_FN.match(name)
        if not m:
            return None
        verb, perm, kind, stat = m.groups()
        key = STAT_KEYS.get((kind, stat))
        if key is None:
            return None
        if verb == 'Get':
            return lambda u=None, *a: (getattr(u, 'bonus', {}) or {}).get(key, 0.0) if u is not None else 0.0
        table = 'bb_perm' if perm else 'bb_tmp'

        def inc(u=None, delta=0.0, *a):
            if u is None or not hasattr(u, 'add_mods'):
                return None
            mods = u.__dict__.setdefault(table, {})
            mods[key] = mods.get(key, 0.0) + float(delta or 0.0)
            u.add_mods(table, dict(mods))
            return None
        return inc

    # ------------------------------------------------------------------ the frame
    def tick(self, t, dt):
        pass


class _Named:
    def __init__(self, name):
        self.name = name


def setup(game, session=None):
    """BB_CHAMPS=Garen,Annie (or the session option 'bb'): those champions run on data/bb16/scripts"""
    names = (getattr(session, 'options', None) or {}).get('bb') or os.environ.get('BB_CHAMPS', 'ALL')
    if names in ('NONE', 'OFF', '0', 'false'):
        game.bb = None
        return
    if names == 'ALL':
        hero_names = {h.name for h in getattr(game, 'heroes', []) if getattr(h, 'name', None)}
        d = os.path.join(G.ROOT, 'data', 'bb16', 'scripts')
        if os.path.isdir(d):
            if hero_names:
                champs = {c for c in hero_names if os.path.isdir(os.path.join(d, c)) and os.listdir(os.path.join(d, c))}
            else:
                champs = {x for x in os.listdir(d) if os.listdir(os.path.join(d, x))}
        else:
            champs = set()
    elif names == '@choice':
        import json
        names = ','.join(json.load(open(os.path.join(G.ROOT, 'data', 'bb16', 'choice.json'))))
        champs = {c.strip() for c in names.split(',') if c.strip()}
    else:
        champs = {c.strip() for c in names.split(',') if c.strip()}
    game.bb = BBEngine(game, champs) if champs else None
