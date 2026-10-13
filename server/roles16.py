"""What the 16.20 packet ids are, as far as it has been read from the 16.20 replay itself (tools/digest16.py for the
fields in clear, x_life.py for what the real server says about one unit, in order). The 13.3 ids do not carry over
(tools/match_ids.py pairs 10 of 161 by shape), so every role here is named from its own content; the 13.3 id in a
comment is the packet that played the same role there.

Field offsets are object offsets as pkt_schema names them ('+0x10').  [m] = measured on the replay,
[g] = my reading of the fields, not checked in the client yet.
"""

# --- connection and start (server -> client)
GAME_INFO = 618        # [m] players, the receiver's slot (slot16.py); 13.3: 574
START_SPAWN = 1080     # [m] first packet of the start state; the client logs "Received StartSpawn packet"; 13.3: 10
GAME_START = 1086      # [m] second packet of the start state ("Received Game Start Packet"); 13.3: 20
CLOCK = 804            # [m] +0x20 f64 segment start time, +0x30 f64 scale (the client's "Replica" clock lines)

# --- units
HERO_CREATE = 222      # [m] +0x1c net id, +0x20 vec3 place, +0x38 champion name, +0x58 player name; 13.3: 79
MINION_SPAWN = 439     # [m] about the minion: +0x14 its barracks' net id, +0x18 kind (4 melee, 5 caster, 6 cannon),
#                            +0x1c the minion's net id, +0x20 wave number, +0x24 f32 game time; 13.3: 98
ENTER_239 = 239        # [m] CONTAINER (forms16.py): lengths + packets inside; live minion = 239{439} + 684; replay: empty after 723
ENTER_DATA = 684       # [m] about a unit coming into sight: +0x10 three floats (health, 0, full health), +0x20 a blob:
#                            26 bytes (a float 1.0 at +9), a byte 2, u32 movement counter, one waypoint entry (the unit's
#                            own id, speed, its way); 13.3: 518 + 770
UNIT_294 = 294         # [m] 0.17 s after a minion's spawn: +0x20 the unit's own net id, a one-element list; role unknown
MOVE = 61              # [m] +0x10 u16 units, +0x18 buffer of 13.3 waypoint entries, +0x28 growing counter; channel 2; 13.3: 552
REPLICATION = 287      # [m] +0x10 u8 units, +0x14 counter, +0x18 f32 game time, +0x20 buffer (repl16.py); channel 2; 13.3: 595
VISIBILITY_723 = 723   # [m] about a unit: +0x10 = the team that now sees it (1 order, 2 chaos); a new minion gets its own
#                            team's 33 ms after its spawn, the other team's when it is seen; 13.3: 387
DELETE = 1090          # [g] about a unit, +0x10 its own net id, about 4 s after its death

# --- fights
MINION_ATTACK = 390    # [m] about the attacker: +0x18 u32 attack counter, +0x1d slot 0x40 / 0x41, +0x20 vec3 target place,
#                            +0x2c the attack's own net id, +0x30 target net id; 13.3: 286
HERO_ATTACK = 906      # [m] about the champion: the same fields, +0x48 / +0x4c the attacker's x, z; 13.3: 592
ATTACK_972 = 972       # [m] follows every 906: +0x10 target net id, +0x14 vec3 target place, +0x20 = 2; 13.3: 516 [g]
STOP_ATTACK = 515      # [g] about the attacker: +0x10..+0x12 flags, +0x14 the attack's net id; 13.3: 490
TARGET = 447           # [g] about a unit: +0x10 the net id it turns to (0 = none); 13.3: 740
DAMAGE = 150           # [m] about the target: +0x10 f32 amount, +0x14 target, +0x1c source, +0x19 0 / 1 (the real server
#                            sends two per hit: a smaller amount with 0, then the full one with 1 and a hash at +0x2c),
#                            +0x20 4 / 5; 13.3: 263
DEATH = 1112           # [m] about the dying unit: +0x30 vec3 place, +0x50 killer net id; 13.3: 61
GOLD = 818             # [m] about the receiver: +0x14 f32 amount, +0x18 receiver, +0x1c the unit it came from; 13.3: 453

# --- spells, buffs, items (read from the digest only)
CAST = 1215            # [g] champion name text, +0x40 f32 game time, places; 13.3: 49
SPELL_IN_SLOT = 78     # [g] +0x1f slot, a spell name text ('TurretBasicAttack', 'AmbessaPassiveDash'); 13.3: 259
COOLDOWN = 635         # [g] +0x10 / +0x18 / +0x20 floats (0..120, 0..28, -1..30), +0x24 a byte; 13.3: 271
BUFF_ADD = 435         # [g] +0x1c source net id, +0x38 slot, +0x39 type, +0x3c f32 duration; 13.3: 693
BUFF_COUNT = 430       # [g] +0x10 count, +0x18 hash, +0x1c slot; 13.3: 220
BUFF_REMOVE = 262      # [g] +0x10 slot, +0x14 hash; 13.3: 522
ITEM_BOUGHT = 63       # [g] +0x30 item id (1001..4642), +0x48 u16; 13.3: 15

# --- client -> server (tools/c2s_classes16.py, c2s16.py)
C2S_ORDER = 1032       # [m] +0x18 place (x, z), +0x20 target net id, +0x24 kind as held in memory (0x91 = move), then the
#                            client's own path; 13.3: 491
C2S_LOADING = 197      # [m] sent while the loading screen is up
C2S_READY = 64         # [m] sent at connect and again when loading is done (our cue for the start state)
C2S_PING = 841         # [m] every 2 s on channel 4
C2S_CLICK_1148 = 1148  # [m] one or two at each right click, 4 B; role unknown

CHANNEL = {MOVE: 2, REPLICATION: 2}      # everything else seen on channel 1
