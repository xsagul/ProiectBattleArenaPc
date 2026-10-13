"""Riot's BuildingBlocks spell / buff / character scripts, run as the scripts they are.

The scripts: the 1.0.0.131 client's DATA/**/*.luaobj (the only full ones found: data/lua131/decomp, decompiled by
tools/lua131_decomp.py), each a set of event tables (SelfExecuteBuildingBlocks, OnBuffActivateBuildingBlocks,
BuffOnUpdateActionsBuildingBlocks ...) of blocks {Function, Params, SubBlocks}. The 16.20 client ships the same
scripts with their tables cut away (same header variables: BuffName, NotSingleTargetSpell ...) and the same
interpreter library: the format is Riot's current one.

How it runs here (one Lua 5.1 state for the match, server/lua51):
  - Riot's interpreter, BuildingBlocksBase.lua (the 1.31 one: it holds the blocks Riot wrote in Lua: BBIf, BBMath,
    BBGetStat, BBExecutePeriodically ...)
  - bb_glue.lua: every script in its own environment; the engine's blocks (BBApplyDamage, BBSpellBuffAdd ... - 142
    kinds in the 1.31 scripts) made from one adapter that hands plain values to Engine() below
  - engine constants (TEAM_ORDER, BUFF_Slow, MAGIC_DAMAGE ...) as their own names; engine functions passed as values
    (GetPercentHardnessMod for BBGetStat) as callable named objects -> Call() below

BBRuntime.blocks[name] = fn(values, names) -> dict of results ('__each' = a list of units for a loop block) is the
engine's side, block by block (core/bbblocks.py); a block or function no one wrote yet is counted in .missing.
"""
import collections
import glob
import os
import re

from . import gamedata as G
from .luavm import VM, LuaError

DECOMP = os.path.join(G.ROOT, 'data', 'lua131', 'decomp')
BASE = os.path.join(DECOMP, 'DATA', 'BuildingBlocks', 'BuildingBlocksBase.lua')
GLUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bb_glue.lua')
VERB = re.compile(r'^(Get|Set|Inc|Is|Has|Can|Spell|Apply|Add|Remove|Push|Pop|Clear|Make|Say|Stop|Init|Turn|Find|Distance|Turn|Net)')


class Named(dict):
    """an engine name the scripts pass around (a stat getter, a constant)"""


def script_files():
    """script name -> decompiled file (DATA/Spells/X.lua, DATA/Characters/C/Scripts/X.lua, DATA/Items/X.lua ...)"""
    out = {}
    for p in glob.glob(os.path.join(DECOMP, 'DATA', '**', '*.lua'), recursive=True):
        if os.sep + 'BuildingBlocks' + os.sep in p:
            continue
        out.setdefault(os.path.splitext(os.path.basename(p))[0].lower(), p)
    return out


def engine_names():
    """every global the scripts read that neither they nor BuildingBlocksBase define"""
    base = open(BASE, errors='replace').read()
    defined = set(re.findall(r'^([A-Za-z_]\w*) = ', base, re.M))
    blocks, names = set(), set()
    for p in script_files().values():
        s = open(p, errors='replace').read()
        own = set(re.findall(r'^([A-Za-z_]\w*) = ', s, re.M))
        for m in re.findall(r'= ([A-Za-z_]\w*)$', s, re.M):
            if m in defined or m in own or re.match(r'L\d+_\d+$', m) or not m[0].isupper():
                continue                         # Lua's own library and the scripts' lower-case variables are not the engine's
            (blocks if m.startswith('BB') else names).add(m)
    return sorted(blocks), sorted(names)


class BBRuntime:
    def __init__(self, game=None, extra=()):
        """extra: folders of scripts that come before the 1.31 ones (data/bb16/scripts/<Champion>)"""
        self.g = game
        self.vm = VM()
        self.missing = collections.Counter()
        self.blocks = {}              # engine block name -> fn(values, names) -> dict | None
        self.funcs = {}               # engine function name (called by a script / by BuildingBlocksBase) -> fn(*args)
        self.files = script_files()
        for d in extra:
            for p in glob.glob(os.path.join(d, '*.lua')):
                self.files[os.path.splitext(os.path.basename(p))[0].lower()] = p
        self.loaded = {}              # script name -> error or None
        self.fallback = None          # name -> fn for engine functions known by their name's pattern (stats)
        vm = self.vm
        vm.register('Engine', self._engine)
        vm.register('EngineCall', self._call)
        vm.load(open(BASE, encoding='utf-8', errors='replace').read(), 'BuildingBlocksBase')
        vm.load(open(GLUE, encoding='utf-8').read(), 'bb_glue')
        blocks, names = engine_names()
        lines = []
        for b in blocks:
            lines.append(f'MakeEngineBlock("{b}")')
        for n in names:
            if VERB.match(n):
                lines.append(f'{n} = setmetatable({{__name = "{n}"}}, {{__call = function(self, ...) return EngineCall("{n}", ...) end}})')
            else:
                lines.append(f'{n} = "{n}"')
        vm.load('\n'.join(lines), 'engine_names')
        # what BuildingBlocksBase itself calls (GetLevel ...) and any other engine function: an EngineCall each
        vm.load("""
setmetatable(_G, {__index = function(t, k)
    if type(k) == 'string' and string.match(k, '^%u%l') then
        local f = setmetatable({__name = k}, {__call = function(self, ...) return EngineCall(k, ...) end})
        rawset(t, k, f)
        return f
    end
    return nil
end})""", 'engine_catchall')
        self.engine_blocks, self.engine_names = blocks, names

    # ------------------------------------------------------------------ scripts
    def load(self, name):
        key = name.lower()
        if key in self.loaded:
            return self.loaded[key] is None
        p = self.files.get(key)
        if p is None:
            self.loaded[key] = 'no script'
            return False
        err = self.vm.call('Glue_LoadScript', key, open(p, encoding='utf-8', errors='replace').read())
        self.loaded[key] = err
        if err:
            self.missing['load ' + name] += 1
        return err is None

    def has(self, name, event):
        return self.load(name) and bool(self.vm.call('Glue_ScriptHas', name.lower(), event))

    def get(self, name, key):
        return self.vm.call('Glue_ScriptGet', name.lower(), key) if self.load(name) else None

    def run(self, name, event, ctx):
        """run a script's event with a context dict -> the context after the run (results the script wrote)"""
        if not self.has(name, event):
            return None
        try:
            return self.vm.call('Glue_RunScriptEvent', name.lower(), event, ctx)
        except LuaError as e:
            self.missing['error ' + name + '.' + event + ': ' + str(e)[:80]] += 1
            return None

    # ------------------------------------------------------------------ the engine's side
    def _engine(self, block, values, names):
        fn = self.blocks.get(block)
        if fn is None:
            self.missing[block] += 1
            return None
        return fn(values or {}, names or {})

    def _call(self, name, *args):
        fn = self.funcs.get(name)
        if fn is None and self.fallback is not None:
            fn = self.fallback(name)
            if fn is not None:
                self.funcs[name] = fn
        if fn is None:
            self.missing['fn ' + name] += 1
            return None
        return fn(*args)
