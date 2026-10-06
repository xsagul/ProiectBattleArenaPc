# Template audit

Per field: `FIXED` = the same in every comparable replay case (protocol fact); `id` = swapped by us; `computed` = set by us; **`COPIED`** = copied from one replay moment although it varies in the replay (hardcoded).

Totals: {'fixed': 158, 'id': 14, 'computed': 59, 'COPIED': 10}

## darius_aa (replay t = 125.825)

- #0 **592** (caster, 147 replay cases): FIXED 1, id 2, computed 5 ['+0xc+0x4', '+0xc+0xc', '+0xc+0x1c', '+0xc+0x24', '+0x3c']
- #1 **516** (caster, 286 replay cases): FIXED 1, id 1, computed 1 ['+0xc']

## darius_aa_hit (replay t = 126.156)

- #0 **693** (target, 257 replay cases): FIXED 14, id 0, computed 0 , **COPIED 2**
    - COPIED +0x15 (17 values in 257 cases, e.g. 00, 02, 03)
    - COPIED +0x1d (2 values in 257 cases, e.g. 01, 05)
- #1 **263** (target, 657 replay cases): FIXED 3, id 1, computed 4 ['+0xa', '+0x14', '+0x1c', '+0x1d']

## darius_hemo_refresh (replay t = 299.785)

- #10 **326** (target, 401 replay cases): FIXED 1, id 0, computed 2 ['+0x14', '+0x15'], **COPIED 2**
    - COPIED +0xc (12 values in 401 cases, e.g. ~3, ~2, ~0.5)
    - COPIED +0x10 (2 values in 401 cases, e.g. 00000000, ~0.5277)

## darius_hemo_tick (replay t = 299.389)

- #1 **263** (target, 35 replay cases): FIXED 3, id 1, computed 4 ['+0xa', '+0x14', '+0x1c', '+0x1d']

## darius_kill_champion (replay t = 308.379)

- #2 **453** (caster, 11 replay cases): FIXED 2, id 1, computed 1 ['+0xc']
- #5 **101** (global, 51 replay cases): FIXED 1, id 0, computed 1 ['+0xa']
- #7 **215** (global, 51 replay cases): FIXED 1, id 0, computed 4 ['+0xc', '+0x10', '+0x14', '+0x18']
- #8 **46** (global, 51 replay cases): FIXED 1, id 0, computed 1 ['+0xc']
- #9 **453** (caster, 8 replay cases): FIXED 2, id 1, computed 1 ['+0xc']
- #10 **740** (target, 8 replay cases): FIXED 0, id 0, computed 1 ['+0xc']
- #11 **568** (target, 6 replay cases): FIXED 0, id 0, computed 4 ['+0xa', '+0xb', '+0xc', '+0x10']
- #12 **780** (target, 51 replay cases): FIXED 0, id 0, computed 1 ['+0xc']
- #13 **417** (target, 51 replay cases): FIXED 3, id 0, computed 6 ['+0xc', '+0x10+0x4', '+0x10+0x8', '+0x10+0xc', '+0x10+0x10', '+0x10+0x14']
- #14 **440** (target, 51 replay cases): FIXED 1, id 1, computed 0 

## darius_w_cast (replay t = 166.867)

- #0 **49** (caster, 96 replay cases): FIXED 28, id 2, computed 11 ['+0xc+0x4', '+0xc+0x8', '+0xc+0x28', '+0xc+0x42', '+0xc+0x4c', '+0xc+0x60', '+0xc+0x78', '+0xc+0x80', '+0xc+0x8c+0x10', '+0xc+0x8c+0x1c', '+0xc+0xc8']
- #1 **271** (caster, 96 replay cases): FIXED 6, id 0, computed 0 
- #2 **693** (caster, 36 replay cases): FIXED 15, id 0, computed 0 , **COPIED 1**
    - COPIED +0x15 (14 values in 36 cases, e.g. 00, 20, 11)
- #3 **721** (caster, 96 replay cases): FIXED 6, id 0, computed 0 
- #4 **259** (caster, 96 replay cases): FIXED 6, id 0, computed 0 
- #5 **118** (caster, 96 replay cases): FIXED 2, id 0, computed 0 
- #6 **465** (caster, 96 replay cases): FIXED 1, id 0, computed 0 
- #7 **71** (caster, 96 replay cases): FIXED 1, id 0, computed 0 
- #8 **71** (caster, 96 replay cases): FIXED 1, id 0, computed 0 
- #9 **71** (caster, 96 replay cases): FIXED 1, id 0, computed 0 
- #10 **71** (caster, 96 replay cases): FIXED 1, id 0, computed 0 
- #11 **65** (caster, 96 replay cases): FIXED 10, id 0, computed 0 
- #12 **592** (caster, 25 replay cases): FIXED 1, id 2, computed 5 ['+0xc+0x4', '+0xc+0x10', '+0xc+0x1c', '+0xc+0x24', '+0x3c']
- #13 **516** (caster, 28 replay cases): FIXED 1, id 1, computed 1 ['+0xc']

## darius_w_hit_minion (replay t = 167.196)

- #0 **522** (caster, 108 replay cases): FIXED 2, id 0, computed 0 , **COPIED 1**
    - COPIED +0xa (25 values in 108 cases, e.g. 00, 14, 1a)
- #1 **271** (caster, 107 replay cases): FIXED 4, id 0, computed 2 ['+0x14', '+0x18']
- #2 **118** (caster, 108 replay cases): FIXED 2, id 0, computed 0 
- #3 **465** (caster, 108 replay cases): FIXED 1, id 0, computed 0 
- #4 **71** (caster, 108 replay cases): FIXED 1, id 0, computed 0 
- #5 **71** (caster, 108 replay cases): FIXED 1, id 0, computed 0 
- #6 **71** (caster, 108 replay cases): FIXED 1, id 0, computed 0 
- #7 **71** (caster, 108 replay cases): FIXED 1, id 0, computed 0 
- #8 **65** (caster, 107 replay cases): FIXED 10, id 0, computed 0 
- #9 **693** (target, 62 replay cases): FIXED 14, id 0, computed 0 , **COPIED 2**
    - COPIED +0x15 (5 values in 62 cases, e.g. 00, 03, 05)
    - COPIED +0x18 (2 values in 62 cases, e.g. ~1, ~2)
- #11 **263** (target, 117 replay cases): FIXED 3, id 1, computed 4 ['+0xa', '+0x14', '+0x1c', '+0x1d']
- #14 **522** (target, 25 replay cases): FIXED 2, id 0, computed 0 , **COPIED 1**
    - COPIED +0xa (2 values in 25 cases, e.g. 00, 02)
- #15 **522** (target, 15 replay cases): FIXED 2, id 0, computed 0 , **COPIED 1**
    - COPIED +0xa (2 values in 15 cases, e.g. 01, 03)

