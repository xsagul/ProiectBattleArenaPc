"""Every champion of the lobby through what the server needs to give it working abilities, without the client:
four spell names for the slots (packet 259), each present in the champion's spell data, with cast times, a
cooldown / cost at rank 1 and a shape and damage the generic engine can work with.

  check_champion_spells.py            the champions with something missing, and the totals
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, os.path.join(ROOT, 'launcher'))
import spell_engine as SE  # noqa: E402
import spell_info as SI  # noqa: E402
import lobby_server as LS  # noqa: E402


def main():
    bad, total, ok_spells = {}, 0, 0
    for c in sorted(LS.champions(), key=lambda c: c['alias']):
        name = c['alias']
        total += 1
        problems = []
        try:
            names = SE.main_spells(name)
            data = SI.spells(name)
        except Exception as e:
            bad[name] = [f'no spell list: {type(e).__name__} {str(e)[:60]}']
            continue
        if len(names) != 4:
            problems.append(f'{len(names)} slot spells')
        for slot, spell in enumerate(names):
            if spell not in data:
                problems.append(f'slot {slot} {spell}: not in the spell data')
                continue
            try:
                SI.cast_times(name, spell)
                d = data[spell]
                if d.get('cooldown'):
                    SI.at_level(d['cooldown'], 1)
                if d.get('mana'):
                    SI.at_level(d['mana'], 1)
                sh = SE.shape(name, spell, 1)
                SE.damage(name, spell, 1, 1, {})
                SE.hit_delay(name, sh, 0.0)
                ok_spells += 1
            except Exception as e:
                problems.append(f'slot {slot} {spell}: {type(e).__name__} {str(e)[:50]}')
        if problems:
            bad[name] = problems
    for name, problems in bad.items():
        print(f'{name}: ' + '; '.join(problems))
    print(f'{total} champions, {total - len(bad)} complete, {ok_spells} of {total * 4} slot spells usable')


if __name__ == '__main__':
    main()
