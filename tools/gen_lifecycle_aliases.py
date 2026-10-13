"""Compile folded lifecycle callbacks before exposing their real C++ names.

An already matched anonymous Small body does not justify a class-template alias.
Each callback below has its own complete compiled body and target verification.
"""
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
import match_func as M
import gen_reflected_buffers as B

SOURCE=ROOT/'client-src/src/gen/LifecycleAliases.cpp'
OWNERS={
    'ChampionRuneRecommendation':(1,1,{'create':0x37a310,'destroy':0x37a7a0}),
    'ChampionRuneRecommendationsContext':(1,1,{'create':0x37a310,'destroy':0x37a7a0}),
    'SHData':(108,4,{'destroy':0x3a1cf0}),
    'VfxSoftParticleDefinitionData':(32,4,{'destroy':0xa584c0}),
    'MapBehavior':(148,4,{'construct':0x3427f0}),
    'JunglePathRecommendations':(24,4,{'destroy':0xf1720}),
    'BerserkTargetingParameters':(12,4,{'destroy':0x127b30}),
    'DeathTimesScalingPoint':(8,4,{'destroy':0x127900}),
    'StealthBreakFlags':(4,1,{'destroy':0x127b90}),
    'StealthCharacterFade':(12,4,{'destroy':0x127b30}),
    'StealthFadeColorEffect':(24,4,{'destroy':0xf1720}),
    'AbilityResourceThresholdIndicatorRange':(8,4,{'destroy':0x127900}),
    'RecSpellRecommendations':(24,4,{'destroy':0xf1720}),
    'ToolEducationData':(8,4,{'destroy':0x127900}),
    'Breakpoint':(12,4,{'destroy':0x127b30}),
    'BaseItemAdvice':(12,4,{'destroy':0x127b30}),
    'ItemDataAvailability':(3,1,{'destroy':0x2a8870}),
    'ItemRecommendationOverrideContext':(12,4,{'destroy':0x127b30}),
    'LootItemDetails':(12,4,{'destroy':0x127b30}),
    'PerkReplacement':(24,4,{'destroy':0xf1720}),
    'SummonerSpellPerkReplacement':(24,4,{'destroy':0xf1720}),
    'RatioConversion':(8,4,{'destroy':0x127900}),
    'AISpellData':(24,4,{'destroy':0xf1720}),
    'SpellEffectAmount':(28,4,{'destroy':0x50a090}),
    'FloatPerSpellLevel':(28,4,{'destroy':0x50a090}),
    'TargeterDefinitionAoeScalar':(12,4,{'destroy':0x127b30}),
    'NumberFormattingBehavior':(8,4,{'destroy':0x127900}),
    'HudMenuTransitionData':(12,4,{'destroy':0x127b30}),
    'MinimapIconColorData':(12,4,{'destroy':0x127b30}),
    'UiLevelUpButtonEasingData':(28,4,{'destroy':0x50a090}),
    'LoadScreenTipConfiguration':(12,4,{'destroy':0x127b30}),
    'PerLocaleTooltipAdjustments':(24,4,{'destroy':0xf1720}),
    'BarracksLink':(8,4,{'destroy':0x127900}),
    'ExtraJointChainData':(12,4,{'destroy':0x127b30}),
    'SyncGroupData':(8,4,{'destroy':0x127900}),
    'FlexTypeFloat':(8,4,{'destroy':0x127900}),
    'CameraTrapezoid':(16,4,{'destroy':0x1dbee0}),
    'EVOSettings':(16,4,{'destroy':0x1dbee0}),
    'RotatingBannerEntry':(16,8,{'destroy':0x1dbee0}),
    'MapSkinColorizationPostEffect':(16,4,{'destroy':0x1dbee0}),
    'DrawablePositionLocator':(16,4,{'destroy':0x1dbee0}),
    'PoiFadeData':(16,4,{'destroy':0x1dbee0}),
    'PoiScalingData':(16,4,{'destroy':0x1dbee0}),
    'MapCloudsLayer':(16,4,{'destroy':0x1dbee0}),
    'MapAudio':(116,4,{'construct':0xa1d270}),
}


def definitions(rows):
    return [line for row in rows for (key,_,_),line in zip(B.CALLBACK_ORDER,B.definitions([row]))
            if key in row['callbacks']]


def verify(path,rows):
    obj=M.compile_obj(str(path),M.FLAGS);out=[]
    allowed={'??2@YAPAXI@Z':0x9bb8d0,'??3@YAXPAXI@Z':0x9bb940,'??0MapBehavior@@QAE@XZ':0x349ce0,
             '??0MapAudio@@QAE@XZ':0xa22520}
    for row in rows:
        for key,fn,suffix in B.CALLBACK_ORDER:
            if key not in row['callbacks']:continue
            rva=row['callbacks'][key];symbol=f'??${fn}@U{row["name"]}@@@@YA{suffix}'
            result=M.compare(str(path),symbol,rva,M.FLAGS,obj)
            _,code,_=M.function_of(obj,symbol);targets=M.symbol_addresses(rva,code)
            if result[3] is not None or any(allowed.get(sym)!=target for sym,target in targets):
                raise ValueError(f'Lifecycle alias lacks an identical body: {row["name"]} {key}: {result}: {targets}')
            out.append(dict(name=row['name'],key=key,rva=rva,bytes=result[1],targets=targets))
    return out


def main():
    import gen_sources as G,gen_meta as A
    im=G.Image();a=A.analysis(im);facts=A.class_facts(im,a);rows=[]
    for name,(size,align,callbacks) in OWNERS.items():
        matches=[f for g,f in facts.items() if a.cls[g]==name]
        if len(matches)!=1:raise ValueError('Lifecycle class metadata is not unique: '+name)
        f=matches[0]
        if (f['size'],f['align'])!=(size,align) or any(f[key]!=rva for key,rva in callbacks.items()):
            raise ValueError('Lifecycle metadata changed: '+name)
        if name=='MapAudio' and A.out_of_line(im,f['construct'])!=('jump',None,0xa22520):
            raise ValueError('MapAudio native constructor binding changed')
        if name not in ('MapBehavior','MapAudio') and (f['parent'] is not None or f['poly'] or im.text(f['destruct'])!='ret 0'):
            raise ValueError('Trivial destruction not established: '+name)
        rows.append(dict(name=name,callbacks=callbacks))
    probe=ROOT/'client-src/obj/root_lifecycle_aliases.cpp'
    probe.write_text('\n'.join([f'#include "{(SOURCE.parent/"BinClasses.h").as_posix()}"',*definitions(rows),'']),encoding='utf-8')
    verify(probe,rows)
    claimed=set()
    for path in M.sources():
        if pathlib.Path(path).resolve()==SOURCE.resolve():continue
        claimed.update(int(rva,16) for rva in re.findall(r'^// match: ([0-9a-f]+)',pathlib.Path(path).read_text(encoding='utf-8'),re.M))
    claims=[]
    for row in rows:
        for key,fn,suffix in B.CALLBACK_ORDER:
            if key not in row['callbacks']:continue
            rva=row['callbacks'][key];kind='same' if rva in claimed else 'match';claimed.add(rva)
            claims.append(f'// {kind}: {rva:x} ??${fn}@U{row["name"]}@@@@YA{suffix}')
    SOURCE.write_text('\n'.join(['// Folded lifecycle names backed by their own complete C++ bodies.',
        '// Generated by tools/gen_lifecycle_aliases.py.',*claims,'#include "BinClasses.h"',*definitions(rows),'']),encoding='utf-8',newline='\n')
    M.rebuilt_symbols.__dict__.pop('v',None)
    audit=verify(SOURCE,rows)
    (ROOT/'client-src/obj/root_lifecycle_aliases_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('Lifecycle aliases:',len(audit),'complete C++ bodies and all targets verified')


if __name__=='__main__':main()
