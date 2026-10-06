import re

with open("research/tryndamere_bin.txt", 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

entries = re.split(r'\n(?=\{[0-9a-fA-F]{8}\}|Characters/)', text)
for entry in entries:
    lines = entry.strip().split('\n')
    if not lines or not lines[0]: continue
    header = lines[0]
    if 'SpellObject' in header:
        print("=" * 60)
        print("SPELL:", header)
        for i, l in enumerate(lines):
            s = l.strip()
            if any(s.startswith(k) for k in [
                'mScriptName:', 'ObjectName:', 'spellCastTime:', 'mLineWidth:', 'mSpeed:',
                'cooldownTime:', 'castRange:', 'castRadius:', 'name:', 'values:',
                'key ', 'mStat:', 'mCoefficient:', 'mFormulaParts:'
            ]):
                print(" ", s)
