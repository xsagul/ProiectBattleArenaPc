import sys
import re

def dump_spells_proper(filename):
    print("============================== " + filename + " ==============================")
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    
    # Split by entries: lines with "(ClassName)" at the end
    chunks = re.split(r'\n(?=[^\s\n]+ \(\w+\))', text)
    for c in chunks:
        first_line = c.strip().splitlines()[0] if c.strip() else ""
        if "(SpellObject)" in first_line:
            lines = c.splitlines()
            script_name = None
            anim_name = None
            cast_time = None
            delay_offset = None
            flags = None
            range_val = None
            mana_val = None
            cooldown = None
            icons = []
            calcs = []
            datavalues = []
            
            in_calc = False
            in_datavalue = False
            for l in lines:
                l_s = l.strip()
                if l_s.startswith("mScriptName:"):
                    script_name = l_s.split(':', 1)[1].strip().strip('"')
                elif l_s.startswith("mAnimationName:"):
                    anim_name = l_s.split(':', 1)[1].strip().strip('"')
                elif l_s.startswith("mCastTime:"):
                    cast_time = l_s.split(':', 1)[1].strip()
                elif l_s.startswith("delayCastOffsetPercent:"):
                    delay_offset = l_s.split(':', 1)[1].strip()
                elif l_s.startswith("flags:"):
                    flags = l_s.split(':', 1)[1].strip()
                elif l_s.startswith("key ") and ("mSpellCalculations" in c or in_calc):
                    calcs.append(l_s.split(' ', 1)[1].strip())
                elif l_s.startswith('name: "') and "DataValues" in c:
                    datavalues.append(l_s.split('"', 2)[1].strip())
                elif "ASSETS/" in l_s and (".dds" in l_s or ".png" in l_s):
                    icons.append(l_s.strip().strip('"'))

            if script_name:
                print(f"Spell: {script_name:25} | Anim: {str(anim_name):15} | CastTime: {str(cast_time or delay_offset):10} | Flags: {str(flags):10}")
                if calcs:
                    print(f"   Calcs: {calcs}")
                if datavalues:
                    print(f"   DataValues: {datavalues}")
                if icons:
                    print(f"   Icons: {icons}")

for champ in ["garen", "lux", "ashe", "tryndamere", "zed"]:
    dump_spells_proper(f"research/{champ}_bin.txt")
