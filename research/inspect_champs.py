import re

def inspect_champion(name, bin_file):
    print(f"==================================================")
    print(f"CHAMPION: {name} ({bin_file})")
    print(f"==================================================")
    with open(bin_file, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    # Find all spell objects
    spell_objs = re.findall(r'ObjectName:\s*"([^"]+)".*?mSpell:\s*SpellDataResource(.*?)(?=(?:ObjectName:|\Z))', text, re.DOTALL)
    print(f"Found {len(spell_objs)} spells in {bin_file}:")
    for sname, sbody in spell_objs:
        print(f"\n--- SPELL: {sname} ---")
        # Extract cooldown
        cd = re.search(r'cooldownTime:\s*\[\d+\](.*?\n(?:\s+[\d\.]+)+)', sbody)
        if cd:
            cds = [x.strip() for x in cd.group(1).split()]
            print(f"  Cooldown: {cds[1:6]}")
        # Extract mana
        mana = re.search(r'mana:\s*\[\d+\](.*?\n(?:\s+[\d\.]+)+)', sbody)
        if mana:
            manas = [x.strip() for x in mana.group(1).split()]
            print(f"  Mana: {manas[:5]}")
        # Extract castRange
        cr = re.search(r'castRange:\s*\[\d+\](.*?\n(?:\s+[\d\.]+)+)', sbody)
        if cr:
            crs = [x.strip() for x in cr.group(1).split()]
            print(f"  Range: {crs[1:6]}")
        # Extract castRadius
        rad = re.search(r'castRadius:\s*\[\d+\](.*?\n(?:\s+[\d\.]+)+)', sbody)
        if rad:
            rads = [x.strip() for x in rad.group(1).split()]
            print(f"  Radius: {rads[1:6]}")
        # Extract cast time
        ct = re.search(r'spellCastTime:\s*([\d\.]+)', sbody)
        if ct:
            print(f"  CastTime: {ct.group(1)}")
        # Extract channel duration
        ch = re.search(r'mChannelDuration:\s*\[\d+\](.*?\n(?:\s+[\d\.]+)+)', sbody)
        if ch:
            chs = [x.strip() for x in ch.group(1).split()]
            print(f"  ChannelDuration: {chs[1:6]}")
        # Extract DataValues
        dvals = re.findall(r'name:\s*"([^"]+)".*?values:\s*\[\d+\](.*?\n(?:\s+[\d\.]+)+)', sbody)
        for dvname, dvvals in dvals:
            vals = [x.strip() for x in dvvals.split()]
            print(f"  DataValue '{dvname}': {vals[1:6] if len(vals) > 5 else vals}")
        # Extract Calculations
        calcs = re.findall(r'key\s+([A-Za-z0-9_]+)\s+GameCalculation', sbody)
        if calcs:
            print(f"  Calculations: {calcs}")

if __name__ == '__main__':
    inspect_champion("Garen", "research/garen_bin.txt")
    inspect_champion("Lux", "research/lux_bin.txt")
    inspect_champion("Ashe", "research/ashe_bin.txt")
    inspect_champion("Tryndamere", "research/tryndamere_bin.txt")
    inspect_champion("Zed", "research/zed_bin.txt")
