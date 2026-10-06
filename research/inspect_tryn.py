import re

def fnv1a(s):
    h = 0x811c9dc5
    for b in s.lower().encode('utf-8'):
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    return h

def inspect_file(bin_path):
    print("=" * 60)
    print("FILE:", bin_path)
    print("=" * 60)
    with open(bin_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    # Split entries
    entries = re.split(r'\n(?=\{[0-9a-fA-F]{8}\}|Characters/)', text)
    for entry in entries:
        lines = entry.strip().split('\n')
        if not lines or not lines[0]: continue
        header = lines[0]
        if 'SpellObject' in header:
            print("\n--- " + header)
            obj_name = ""
            for l in lines:
                s = l.strip()
                if s.startswith('ObjectName:') or s.startswith('mScriptName:'):
                    print("  " + s)
                elif any(s.startswith(k) for k in [
                    'cooldownTime:', 'mana:', 'castRange:', 'castRadius:', 
                    'spellCastTime:', 'mChannelDuration:', 'mAttackDelayCastOffsetPercent',
                    'mTargetingTypeData:', 'mLineWidth:'
                ]):
                    print("  " + s)
                elif s.startswith('name:') and '"' in s:
                    # check if followed by values
                    print("  " + s)
                elif s.startswith('key ') and 'GameCalculation' in s:
                    print("  Calculation: " + s)
        elif 'CharacterRecord' in header:
            print("\n--- " + header)
            for l in lines:
                s = l.strip()
                if any(s.startswith(k) for k in [
                    'baseHP', 'baseDamage', 'baseArmor', 'baseSpellBlock',
                    'baseMoveSpeed', 'attackRange', 'attackSpeed', 'attackSpeedRatio',
                    'hpPerLevel', 'damagePerLevel', 'armorPerLevel', 'spellBlockPerLevel',
                    'attackSpeedPerLevel', 'spellNames:', 'primaryAbilityResource:'
                ]):
                    print("  " + s)

if __name__ == '__main__':
    inspect_file("research/tryndamere_bin.txt")
