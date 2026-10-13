"""A minimal server side of the 13.3 transport ("LNP"), to see how far the unpacked client gets.

Control packets have packet number 0 and are told apart by payload length (connection layer, vtable rva 0x1578914,
lengths set at rva 0x2d644a, receive at rva 0x2e2090):
  500  connect     u64 sender nonce, u64 nonce the sender believes the other side has, u8 flag, filler
  100  accept      u64 client nonce, u64 server nonce, u8 flag, filler
   50  disconnect  (not handled here)
Client side, state "connecting": an accept whose two nonces match its own -> connected (next layer's OnConnect gets the
flag); otherwise it adopts the server nonce and sends connect again (rva 0x2eebb0).
Server side (same code, rva 0x2e2090 first branch): a connect whose second nonce is the server's -> connected, stores
the client nonce; either way it answers with an accept (rva 0x2eef90).

Once connected (read in the client's receive layers, vtable order):
  - any packet with a number > 0 keeps the connection alive (rva 0x2e24f7; [Network] Timeout 8000 ms otherwise);
  - packet number with the top bit set = an ACK packet: number = -(latest packet received), the extra u64 after the
    flag byte = bit k set when packet (latest - k) was received (bit 0 = latest itself) (rva 0x2ee8a0 builds it,
    rva 0x2ed360 reads it);
  - header flag byte != 0: payload compressed with zstd, at most 1100 bytes once inflated (rva 0x2e2020);
  - payload = messages, one after the other (rva 0x2e1da0, header reader rva 0x2dcd40):
      u16 w      length = w >> 3; bit0 fragment; bit1 message number = previous + 1; bit2 channel = previous
      [u8  channel]            unless bit2
      [u16 message number]     unless bit1
      [u16 fragment id, u8 fragment count, u8 fragment index]   only with bit0  (log: fragment=id(index+1/count))
      length bytes: the game packet = [u16 packet id][u32 net id][body]
  - packet 574 (player list) sets the client's player slot (listener rva 0x3554e0 -> rva 0x364850), which with the
    connected flag opens "Game Server Connection Established" (rva 0x3630c0, 0x324f50).

  lnp_server.py [--replay-574] [--frag N] <port>     logs every datagram, decrypted, to stdout
  --own-79 [--set79 "1.skin=0"]                      champion creations built by us (create_hero.py)
"""
import base64, collections, math, os, socket, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lnp import Lnp, checksum, parse
import lol_packets as LP
import waypoints as W

KEY = base64.b64decode('17BLOhi6KZsTtldTsizvHg==')
PEER = 1                      # the u64 that goes into the checksum (the hello used 1)
NO_EXTRA = 0xFFFFFFFFFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
REPLAY_574 = os.path.join(HERE, '..', 'data', 'exe133', 's2c_574_replay.bin')
# packet 574, body byte 2 = the receiving client's own player slot, stored obfuscated: the client turns it into the slot
# at rva 0x36489d (found by running that code on all 256 values; the replay's spectator gets 0xef = slot 17)
SLOT_BYTE = [0xba, 0xfa, 0x3a, 0x7a, 0xca, 0x0a, 0x4a, 0x8a, 0xda, 0x1a, 0x5a, 0x9a]


def build(lnp, seq, payload, flag=0, extra=None):
    crc = checksum(seq, PEER, NO_EXTRA if extra is None else extra, payload)
    body = struct.pack('<H', seq) + struct.pack('>I', crc) + bytes([flag])
    if extra is not None:
        body += struct.pack('<Q', extra)
    return lnp.seal(body + payload)


def message(channel, number, data, frag=None):
    """One message record; frag = (fragment id, count, index)."""
    w = (len(data) << 3) | (1 if frag else 0)
    out = struct.pack('<HBH', w, channel, number & 0xFFFF)
    if frag:
        out += struct.pack('<HBB', *frag)
    return out + data


def split_messages(p):
    out, at, prev_ch, prev_num = [], 0, 0, 0
    while at + 2 <= len(p):
        w = struct.unpack_from('<H', p, at)[0]; at += 2
        ch = prev_ch
        if not w & 4:
            ch = p[at]; at += 1
        num = prev_num + 1
        if not w & 2:
            num = struct.unpack_from('<H', p, at)[0]; at += 2
        frag = None
        if w & 1:
            frag = struct.unpack_from('<HBB', p, at); at += 4
        n = w >> 3
        out.append((ch, num, frag, p[at:at + n])); at += n
        prev_ch, prev_num = ch, num
    return out


class Peer:
    def __init__(self):
        self.connected = False
        self.seq = 0                 # our last data packet number
        self.latest = None           # their latest data packet number
        self.mask = 0
        self.msgnum = {}             # channel -> last message number sent
        self.sent_574 = False
        self.skills = {}             # slot -> level given by us

    def got(self, seq):
        if self.latest is None:
            self.latest, self.mask = seq, 0xFFFFFFFFFFFFFFFF   # the client starts its own mask this way
        elif seq > self.latest:
            self.mask = ((self.mask << (seq - self.latest)) | 1) & 0xFFFFFFFFFFFFFFFF
            self.latest = seq
        elif self.latest - seq < 64:
            self.mask |= 1 << (self.latest - seq)


def main():
    args = sys.argv[1:]
    send_574 = '--replay-574' in args
    frag_size = 1000
    # bytes before the encrypted body in a client datagram: 8 on 13.3, 12 on 16.20 (measured: match_hello)
    id_len = int(args[args.index('--id-len') + 1]) if '--id-len' in args else 8; s2c = [b'']   # 16.20: our datagrams start with bytes 8..11 of the client's header (hello_probe16.py)
    if '--frag' in args:
        frag_size = int(args[args.index('--frag') + 1])
    frag_mode = args[args.index('--frag-mode') + 1] if '--frag-mode' in args else 'after'
    replay_path = args[args.index('--stream') + 1] if '--stream' in args else None
    speed = float(args[args.index('--speed') + 1]) if '--speed' in args else 1.0
    start_at = 0.0
    slot = int(args[args.index('--slot') + 1]) if '--slot' in args else None
    hero = int(args[args.index('--hero') + 1], 16) if '--hero' in args else None   # e.g. 4000001e = Darius (slot 1)
    # --own-79: every champion creation (79) is built by us (create_hero.py) from named fields instead of sent from the
    # replay; --set79 "1.skin=0;2.champion=Garen" changes fields of the hero in a player slot first
    own_79 = None
    if '--own-79' in args:
        import create_hero as CH
        heroes = CH.load_heroes()
        if '--set79' in args:
            for item in args[args.index('--set79') + 1].split(';'):
                key, val = item.split('=', 1)
                sl, name = key.split('.')
                h = next(x for x in heroes if x['slot'] == int(sl))
                old = h[name]
                h[name] = type(old)(val) if not isinstance(old, list) else [float(x) for x in val.split(',')]
                print(f'79 of slot {sl}: {name} {old!r} -> {h[name]!r}', flush=True)
        own_79 = [CH.build(h) for h in heroes]
        print(f'{len(own_79)} champion creations (79) built by us', flush=True)
    # --own-574: the game info (574) built by us (game_info.py) from the replay's values, with the receiving client's
    # slot set through the codec; --set574 "1.name=BattleArena;1.champion=Darius;1.skin=0" changes a player first
    own_574 = None
    if '--own-574' in args:
        import game_info as GI
        gv = GI.template()
        GI.set_local_slot(gv, slot or 17)
        if '--set574' in args:
            for item in args[args.index('--set574') + 1].split(';'):
                key, val = item.split('=', 1)
                sl, name = key.split('.')
                if name == 'name':
                    GI.set_name(gv, int(sl), val)
                elif name == 'champion':
                    GI.set_champion(gv, int(sl), val)
                elif name == 'champion_id':
                    _, g = GI.by_slot(gv, int(sl))
                    g['+0x80'] = GI.mk_u32(int(val))
                elif name == 'skin':
                    _, g = GI.by_slot(gv, int(sl))
                    g['+0x84'] = GI.mk_u32(int(val))
                print(f'574 slot {sl}: {name} = {val}', flush=True)
        own_574 = GI.build(gv)
        print(f'game info (574) built by us: {len(own_574)} B', flush=True)
    port = int(args[-1])
    lnp = Lnp(KEY)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', port))
    s.settimeout(0.01)
    t0 = time.time()
    server_nonce = struct.unpack('<Q', os.urandom(8))[0]
    peers = {}
    last_keepalive = 0.0
    print(f'listening on udp {port}, server nonce {server_nonce:016x}', flush=True)

    def send_data(addr, st, payload, what, quiet=False):
        st.seq = st.seq % 0x7FFF + 1          # top bit marks ack packets, 0 control packets
        s.sendto(s2c[0] + build(lnp, st.seq, payload), addr)
        if not quiet:
            print(f'{time.time() - t0:8.3f} snd data seq {st.seq} len {len(payload)} {what}', flush=True)

    def send_message(addr, st, channel, data, what, quiet=False):
        if len(data) <= frag_size:
            st.msgnum[channel] = st.msgnum.get(channel, 0) + 1
            send_data(addr, st, message(channel, st.msgnum[channel], data), what, quiet)
            return
        parts = [data[i:i + frag_size] for i in range(0, len(data), frag_size)]
        first = st.msgnum.get(channel, 0) + 1
        for i, part in enumerate(parts):
            if frag_mode == 'seq':        # every fragment its own message number, fragment id = the first one
                num, fid = first + i, first
            elif frag_mode == 'after':    # same, but the whole message takes the number after the fragments
                num, fid = first + i, first + len(parts)
            else:                         # 'same': every fragment carries the message's own number
                num, fid = first, first
            send_data(addr, st, message(channel, num, part, (fid, len(parts), i)),
                      f'{what} fragment {i + 1}/{len(parts)} num {num} id {fid}', quiet)
        st.msgnum[channel] = {'seq': first + len(parts) - 1, 'after': first + len(parts)}.get(frag_mode, first)

    # The replay's own stream (chunks only, in order), sent in real time once the client says it has loaded.
    stream = None
    # --start-only: the start state alone (keyframe 1), none of the match that followed: the world after the start
    # is our server's
    start_only = '--start-only' in args
    pass_kinds = {int(x) for x in args[args.index('--pass-kinds') + 1].split(',')} if '--pass-kinds' in args else set()
    if replay_path:
        import rofl_packets as R
        def spectator_stream(r):
            # what a spectator gets: the file's entries in order, chunks plus only the first keyframe (it holds the
            # start state, with StartSpawn = packet 10 and Game Start = packet 20); later keyframes only serve seeking
            for e in r.entries:
                if (e['type'] == 1 and not start_only) or (e['type'] == 2 and e['id'] == 1):
                    for b in R.blocks(r.payload(e)):
                        yield e, b
            if start_only and pass_kinds:
                # control experiment (--pass-kinds "98,518,..."): after the start state, the replay's own packets of
                # these kinds go to the client untouched, to tell what our own packets of a kind do differently
                yield None, (0.0, 0, -1, 0, b'')
                for e in r.entries:
                    if e['type'] == 1:
                        for b in R.blocks(r.payload(e)):
                            if b[2] in pass_kinds:
                                yield e, b
        stream = spectator_stream(R.Rofl(replay_path))
    # --hero-spells "GarenQ,GarenW,GarenE,GarenR": the spells the hero's slots 0..3 get (packet 259, pkt_schema)
    hero_spells = args[args.index('--hero-spells') + 1].split(',') if '--hero-spells' in args else []
    hero_champion = 'Darius'
    for item in (args[args.index('--set79') + 1].split(';') if '--set79' in args else []):
        if item.startswith('1.champion='):
            hero_champion = item.split('=')[1]
    import spell_engine as SE
    engine_spells = hero_spells or SE.main_spells(hero_champion)
    print(f'hero champion {hero_champion}: spells {engine_spells}', flush=True)
    cast_tpl = {}
    # --buff-family <hex>: 693 +0x2c for our buffs (a per-source hash whose name is unknown; default: the template's)
    buff_family = args[args.index('--buff-family') + 1] if '--buff-family' in args else None
    _spell = {}

    def spell_codec():
        if not _spell:
            import pkt_schema as PS2_
            import pkt_tree as PT2_
            _spell['c'] = (PS2_.Schema.load(259), PT2_.Tree(259))
        return _spell['c']
    import pkt_schema as PS2
    pending = None                   # next replay block not sent yet
    # what Riot's server sent about the hero for its first Q (replay 113.0 .. 113.8 s): answered to the client's
    # cast request (16) with the same spacing in time, until the server builds these packets itself
    CAST_KINDS = (49, 65, 271, 693, 522, 63, 453, 220, 406)
    # another champion in slot 1: of the replay's packets about the hero only these stay (595 is filtered, 259 puts
    # our spells in, 606 = level + skill points, 46 = experience)
    own_hero = hero is not None and (hero_champion != 'Darius' or start_only)
    OWN_HERO_KEEP = (595, 259, 606, 46)
    own_hero_state = {'progress': (1, 0.0), 'dirty': True, 'gold': 500.0,
                      'inv': [None] * 7, 'stacks': [0] * 7}

    def hero_progress(groups):
        """(mLevelRef, mExp) out of the hero's replicated groups (unchanged values keep the last ones)"""
        import replication as RP
        import repl_codec as RC_
        level, exp = own_hero_state['progress']
        names_ = RC_.names()
        want = {names_['mLevelRef'][:2]: 'level', names_['mExp'][:2]: 'exp'}
        for g, (mask, data) in groups.items():
            at = 0
            for b in range(32):
                if not mask >> b & 1:
                    continue
                kind = next((k for n_, (g_, b_, k) in names_.items() if g_ == g and b_ == b), 'i')
                end = RP.take(data, at, kind)
                raw = data[at:end]
                at = end
                if (g, b) in want:
                    if kind == 'f':
                        v = 0.0 if raw == b'\xff' else struct.unpack('<f', raw[-4:])[0]
                    else:
                        v, sh = 0, 0
                        for c in raw:
                            v |= (c & 0x7f) << sh
                            sh += 7
                    if want[(g, b)] == 'level':
                        level = int(v)
                    else:
                        exp = float(v)
        return level, exp

    def own_hero_stats(level, exp):
        """the hero's replicated stats at a level from its CharacterRecord: base + growth x (lvl-1) x (0.7025 +
        0.0175 (lvl-1)) (the formula checked on the replay's AD); health / mana full [our approximation: no regen, no
        items, no runes]"""
        import spell_info as SI
        rec = SI.char_record(hero_champion)
        f = lambda k, d=0.0: float(rec.get(k, d))   # noqa: E731
        g = lambda base, per: base + per * (level - 1) * (0.7025 + 0.0175 * (level - 1))   # noqa: E731
        hp = g(f('baseHP'), f('hpPerLevel'))
        par = g(f('primaryAbilityResource.arBase'), f('primaryAbilityResource.arPerLevel'))
        values = {
            'mHP': hp, 'mMaxHP': hp,
            'mPAR': par, 'mMaxPAR': par, 'mPAREnabled': 1 if par > 0 else 0,
            'mBaseAttackDamage': g(f('baseDamage'), f('damagePerLevel')),
            'mArmor': g(f('baseArmor'), f('armorPerLevel')),
            'mSpellBlock': g(f('baseSpellBlock'), f('spellBlockPerLevel')),
            'mHPRegenRate': g(f('baseStaticHPRegen'), f('hpRegenPerLevel')),
            'mPARRegenRate': g(f('primaryAbilityResource.arBaseStaticRegen'), f('primaryAbilityResource.arRegenPerLevel')),
            'mAttackRange': f('attackRange', 125), 'mMoveSpeed': f('baseMoveSpeed', 325),
            'mAttackSpeedMod': 1.0 + g(0.0, f('attackSpeedPerLevel')) / 100.0,
            'mLevelRef': level, 'mExp': exp, 'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4, 'mScaleSkinCoef': 1.0,
            # what the hero may do. Riot's server sends it in the first seconds of the match (replay: 0xa000003 at
            # 4.0 s, 0x200000f with ActionState2 = 4 from 5.1 s on, the value of a hero free to act). Without it the
            # client let the hero walk but never sent an attack order: nothing could be attacked.
            'ActionState': 0x200000f, 'ActionState2': 4,
        }
        # the items' stat mods (items133: items.bin ItemData): flat health / mana / damage / armor / magic resist,
        # attack speed percent, ability haste, crit, movement speed
        import items133 as IT
        db_ = IT.items()
        mods = {}
        for iid in own_hero_state['inv']:
            for k_, v_ in (db_.get(iid, {}).get('stats', {}) if iid else {}).items():
                mods[k_] = mods.get(k_, 0.0) + v_
        if mods:
            values['mMaxHP'] = values['mHP'] = values['mMaxHP'] + mods.get('mFlatHPPoolMod', 0)
            values['mMaxPAR'] = values['mPAR'] = values['mMaxPAR'] + mods.get('mFlatMPPoolMod', 0)
            values['mFlatPhysicalDamageMod'] = mods.get('mFlatPhysicalDamageMod', 0)
            values['mFlatMagicDamageMod'] = mods.get('mFlatMagicDamageMod', 0)
            values['mBonusArmor'] = mods.get('mFlatArmorMod', 0)
            values['mArmor'] += values['mBonusArmor']
            values['mBonusSpellBlock'] = mods.get('mFlatSpellBlockMod', 0)
            values['mSpellBlock'] += values['mBonusSpellBlock']
            values['mAttackSpeedMod'] += mods.get('mPercentAttackSpeedMod', 0)
            values['mAbilityHasteMod'] = mods.get('mAbilityHasteMod', 0)
            values['mCrit'] = mods.get('mFlatCritChanceMod', 0)
            values['mMoveSpeed'] = (values['mMoveSpeed'] + mods.get('mFlatMovementSpeedMod', 0)) * \
                (1 + mods.get('mPercentMovementSpeedMod', 0))
        # the health is what the hero has left: full minus the damage taken (hero_takes), back up with time (hero_regen)
        own_hero_state.update(max_hp=values['mMaxHP'], armor=values['mArmor'], regen=values['mHPRegenRate'],
                              max_par=values['mMaxPAR'])
        values['mHP'] = max(0.0, values['mMaxHP'] - own_hero_state.get('lost', 0.0))
        if start_only:
            # the hero's gold (500 at the start, the replay's first value for every hero) and the can-cast bits of the
            # summoner spells and recall (0x2030, the replay's first value)
            values.update(mGold=own_hero_state['gold'])
            if not own_hero_state.get('gold_sent'):
                own_hero_state['gold_sent'] = True
                values.update(mGoldTotal=500.0, mReplicatedSpellCanCastBitsLower1=0x2030)
        return values

    def buy_item(addr, st, item_id):
        """the client's purchase request (C2S 782, +0xc item id): LoL's recipe rule (items133.purchase), then what
        Riot's server sends for it (replay 718.9 s, Trinity Force): 728 per component taken out (+0xc gold before, +0x10
        slot), 15 for the new item (+0xc+0x4 stacks, +0x8 total price, +0xc item id, +0x10 slot, +0x20 gold after,
        +0xa 1 = bought), then the hero's gold and stats (595)"""
        import items133 as IT
        import pkt_schema as PSb
        import pkt_tree as PTb
        S_ = own_hero_state
        db_ = IT.items()
        it_ = db_.get(item_id, {})
        # a stackable item already owned goes on the same slot
        stack_slot = next((i for i in range(7) if S_['inv'][i] == item_id and S_['stacks'][i] < it_.get('maxStack', 1)), None)
        res = IT.purchase(item_id, S_['inv'], S_['gold'])
        if isinstance(res, str):
            print(f'buy {item_id} refused: {res}', flush=True)
            return
        cost, used, slot_ = res
        if stack_slot is not None and not used:
            slot_ = stack_slot
        before = S_['gold']
        # only the encoder is needed here, and only once: building the decoder tree of 728 took 0.9 s on every
        # purchase (the item appeared in the inventory seconds after the click)
        sc728 = schema_cache.get(728) or schema_cache.setdefault(728, PSb.Schema.load(728))
        for u in used:
            v = {'+0xa': '00', '+0xb': '00', '+0xc': struct.pack('<f', before).hex(), '+0x10': f'{u:02x}'}
            send_message(addr, st, 1, struct.pack('<HI', 728, hero) + sc728.encode(v), f'728 item out of slot {u}')
            S_['inv'][u], S_['stacks'][u] = None, 0
        S_['gold'] = before - cost
        if S_['inv'][slot_] == item_id:
            S_['stacks'][slot_] += 1
        else:
            S_['inv'][slot_], S_['stacks'][slot_] = item_id, 1
        sc15 = schema_cache.get(15) or schema_cache.setdefault(15, PSb.Schema.load(15))
        v = {'+0xa': '01',
             '+0xc': {'+0x4': f'{S_["stacks"][slot_]:02x}', '+0x8': struct.pack('<f', float(it_.get('priceTotal', cost))).hex(),
                      '+0xc': struct.pack('<I', item_id).hex(), '+0x10': f'{slot_:02x}', '+0x12': '0000'},
             '+0x20': struct.pack('<f', S_['gold']).hex(), '+0x24': '01'}
        send_message(addr, st, 1, struct.pack('<HI', 15, hero) + sc15.encode(v),
                     f'15 bought {it_.get("name", item_id)} for {cost} in slot {slot_} (gold {S_["gold"]:.0f})')
        own_hero_state['dirty'] = True
    q_reply = []
    if replay_path and hero is not None:
        for _, (bt0, ch0, pid0, obj0, body0) in R.stream(R.Rofl(replay_path), (1,)):
            if bt0 > 113.8:
                break
            if bt0 >= 112.99 and obj0 == hero and pid0 in CAST_KINDS:
                q_reply.append((bt0 - 113.0, ch0, pid0, body0))
        print(f'first Q of the hero in the replay: {[(round(a, 2), p) for a, _, p, _ in q_reply]}', flush=True)
    if q_reply:
        import pkt_schema as PSc
        import pkt_tree as PTc
        for dt0, ch0, p0, b0 in q_reply:
            if p0 in (49, 65, 271) and (p0 not in cast_tpl or (p0 == 271 and dt0 > 0.5)):
                sc_ = PSc.Schema.load(p0)
                cast_tpl[p0] = (sc_, PSc.decode(PTc.Tree(p0), sc_, struct.pack('<HI', p0, hero) + b0))
                cast_tpl[f'ch{p0}'] = ch0
        # buffs (693 put, 522 taken off): templates from the replay's own packets (pkt_dump_all.py), Darius's W buff
        import json as _json
        import spell_info as _SI
        onh = struct.pack('<I', _SI.elf('DariusNoxianTacticsONH')).hex()
        for p0, pick in ((693, lambda v: v['+0x10'] == onh), (522, lambda v: v['+0x10'] == onh)):
            for line in open(os.path.join(PSc.OUT, f'{p0}.all.jsonl')):
                v0 = _json.loads(line)['v']
                if v0 and pick(v0):
                    cast_tpl[p0] = (PSc.Schema.load(p0), v0)
                    cast_tpl[f'ch{p0}'] = 1
                    break
        print(f'generic cast templates: {sorted(k for k in cast_tpl if isinstance(k, int))}', flush=True)
    # --own-49: the cast (49) of that Q is built by us (pkt_schema, data/exe133/codec/49.tree.json) from the
    # replay's values, with the cast times set to the game time of our cast and the spell's skin set to our hero's
    own_49 = None
    if ('--own-49' in args or '--own-cast' in args) and q_reply:
        import pkt_schema as PS
        import pkt_tree as PTR
        # every packet of the Q reply whose writer is learnt (data/exe133/codec/<id>.tree.json: 49, 271, 65, 693)
        # is decoded once here and rebuilt by us at each cast
        own_49 = {}
        for i, (_, _, p, b) in enumerate(q_reply):
            if not os.path.exists(os.path.join(PS.OUT, f'{p}.tree.json')):
                continue
            if p not in own_49:
                own_49[p] = (PS.Schema.load(p), PTR.Tree(p))
            sc_p, tree_p = own_49[p]
            own_49[i] = (sc_p, PS.decode(tree_p, sc_p, struct.pack('<HI', p, hero) + b))
        print(f'Q reply packets built by us: {sorted({q_reply[i][2] for i in own_49 if isinstance(i, int) and i < len(q_reply) and isinstance(own_49[i][1], dict)})}', flush=True)
        q_cooldown = float(args[args.index('--q-cooldown') + 1]) if '--q-cooldown' in args else None
        q_gold = float(args[args.index('--q-gold') + 1]) if '--q-gold' in args else None
        # --q-kill <net id>: with the Q, our own damage (263, the Q's 127.4 from the replay) and death (61, killed by
        # the hero) for that unit, built from the replay's packets about the minion that Q killed (0x40000232)
        q_kill = int(args[args.index('--q-kill') + 1], 16) if '--q-kill' in args else None
        kill_tpl = {}
        if q_kill is not None:
            for _, (bt0, ch0, pid0, obj0, body0) in R.stream(R.Rofl(replay_path), (1,)):
                if bt0 > 113.8:
                    break
                if obj0 == 0x40000232 and pid0 in (263, 61) and bt0 >= 113.7:
                    if pid0 not in own_49:
                        own_49[pid0] = (PS.Schema.load(pid0), PTR.Tree(pid0))
                    sc_p, tree_p = own_49[pid0]
                    kill_tpl[pid0] = (ch0, sc_p, PS.decode(tree_p, sc_p, struct.pack('<HI', pid0, obj0) + body0))
            print(f'kill templates: {sorted(kill_tpl)}', flush=True)
        hero_skin = 15
        if own_79 is not None:
            hero_skin = next((h['skin'] for h in CH.load_heroes() if h['net_id'] == hero), 15)
            for item in (args[args.index('--set79') + 1].split(';') if '--set79' in args else []):
                if item.startswith('1.skin='):
                    hero_skin = int(item.split('=')[1])
        print(f'49 (cast) built by us, skin {hero_skin}', flush=True)
    scheduled = []                   # (wall time, addr, channel, data, what)
    stream_t0 = None                 # (wall clock, game time) when streaming started
    sent_count = {}

    def pump_stream(addr, st):
        nonlocal pending
        now = time.time()
        game_now = stream_t0[1] + (now - stream_t0[0]) * speed
        batch, n, budget = b'', 0, 40      # at most ~40 datagrams per turn, so the client's socket keeps up
        while budget > 0:
            if pending is None:
                try:
                    pending = next(stream)[1]
                except StopIteration:
                    if start_only and not own_hero_state.get('start_sent'):
                        # the start state is all sent (the hero exists in the client now): our hero's first values
                        own_hero_state['start_sent'] = True
                        own_hero_state['dirty'] = True
                    break
            bt, ch, pid, obj, body = pending
            if pid == -1:
                # the start state is all sent; what follows are the replay's packets of the passed kinds
                own_hero_state['start_sent'] = True
                own_hero_state['dirty'] = True
                pending = None
                continue
            if pid == 574:
                pending = None
                continue
            if pass_kinds and start_only and own_hero_state.get('start_sent') and pid in (552, 595):
                # passed movement / replication packets are batches: the ten champions are taken out (they are ours
                # to move and to describe), the minions, monsters and structures of the real stream stay
                for h_ in list(hero_names):
                    if body is None:
                        break
                    body = LP.without_unit(body, h_) if pid == 552 else LP.take_unit(body, h_)[0]
                if body is None:
                    pending = None
                    continue
            if pid == 259 and obj == hero and (hero_spells or hero_champion != 'Darius'):
                # 259 = a spell put in a slot (+0xc+0x7 slot, +0x18 the spell's name): our hero's own spells
                sc_, tree_ = spell_codec()
                v_ = PS2.decode(tree_, sc_, struct.pack('<HI', 259, obj) + body)
                slot_ = int(v_['+0xc']['+0x7'], 16) if v_ and isinstance(v_['+0xc'], dict) and '+0x7' in v_['+0xc'] else None
                if slot_ is not None and slot_ < len(engine_spells):
                    # the name travels with its terminating zero (the replay's own: "DariusCleave\0"); without it
                    # the client finds no such spell and leaves the slot empty: no icon, no level-up, no cast
                    v_['+0x18'] = {'text': (engine_spells[slot_].encode() + b'\0').hex()}
                    body = sc_.encode(v_)
                    print(f'our 259: slot {slot_} = {engine_spells[slot_]}', flush=True)
            if pid == 79 and own_79 is not None:
                body = own_79[sent_count.get(79, 0)]
            if own_hero and obj == hero and bt > 1 and pid not in OWN_HERO_KEEP:
                # another champion than the replay's Darius in slot 1: what the replay says about Darius (his casts,
                # buffs, fog -- 387 LeaveFog hid our hero, 730 at re-entry re-created it as Darius) is not about ours
                pending = None
                continue
            if own_hero and pid == 595 and bt <= 1:
                # the start state: Darius's gold and can-cast bits stay (group 0, 1), his stats go (ours follow)
                for g_ in (2, 3, 4, 5):
                    body = LP.without_group(body, hero, g_) if body is not None else None
                own_hero_state['dirty'] = True
                if body is None:
                    pending = None
                    continue
            if own_hero and pid == 595 and bt > 1:
                # Darius's stats are not ours: his unit goes; his level and experience stay (the match's progression,
                # with 606 / 46), our champion's stats for that level come from its own data (own_hero_stats)
                body, groups_ = LP.take_unit(body, hero)
                if groups_:
                    prog_ = hero_progress(groups_)
                    if prog_ != own_hero_state.get('progress'):
                        own_hero_state['progress'] = prog_
                        own_hero_state['dirty'] = True
                if body is None:
                    pending = None
                    continue
            if hero is not None and obj == hero and pid in CAST_KINDS and bt > 1:   # the hero's casts are ours
                pending = None
                continue
            if pid == 676 and obj == hero and bt > 1:   # in-game skill levels come from our answers to 384 (the keyframe sets them up)
                pending = None
                continue
            if pid == 595 and hero is not None and bt > 1:   # the hero's private group (gold, can-cast bits) is ours
                body = LP.without_group(body, hero, 0)
                if body is None:
                    pending = None
                    continue
            if obj in dead_units and bt > 1:
                pending = None
                continue
            if pid == 552 and dead_units:
                for du_ in dead_units:
                    body = LP.without_unit(body, du_) if body is not None else None
                if body is None:
                    pending = None
                    continue
            if pid == 595 and bt > 1:
                for tgt_ in list(unit_hp):        # the health of units we damage is ours (group 5: mHP, mMaxHP, ...)
                    body = LP.without_group(body, tgt_, 3 if tgt_ in minions else 5) if body is not None else None
                if body is None:
                    pending = None
                    continue
            if pid == 552 and hero is not None:   # the hero is ours: the replay no longer moves it
                body = LP.without_unit(body, hero)
                if body is None:
                    pending = None
                    continue
            if bt > game_now:
                break
            data = struct.pack('<HI', pid, obj) + body
            pending = None
            sent_count[pid] = sent_count.get(pid, 0) + 1
            if len(data) > frag_size:
                if batch:
                    send_data(addr, st, batch, f'replay batch {n}', quiet=True); batch, n = b'', 0
                send_message(addr, st, ch, data, f'replay {pid} t {bt:.2f}', quiet=True)
                budget -= len(data) // frag_size + 1
                continue
            st.msgnum[ch] = st.msgnum.get(ch, 0) + 1
            rec = message(ch, st.msgnum[ch], data)
            if len(batch) + len(rec) > frag_size:
                send_data(addr, st, batch, f'replay batch {n}', quiet=True); batch, n = b'', 0
                budget -= 1
            batch += rec; n += 1
        if batch:
            send_data(addr, st, batch, f'replay batch {n}', quiet=True)
        if own_hero and own_hero_state.get('dirty') and (not start_only or own_hero_state.get('start_sent')):
            own_hero_state['dirty'] = False
            level_, exp_ = own_hero_state['progress']
            import repl_codec as RC
            hp_counter[0] += 1
            body_ = RC.packet([(hero, own_hero_stats(level_, exp_), RC.HERO)], game_now, hp_counter[0])
            send_message(addr, st, 2, struct.pack('<HI', 595, 0) + body_, f'our 595: {hero_champion} level {level_} stats')

    def skill_up(addr, st, slot, t):
        """answer to a skill-up request (384): the spell's new level (676) and the can-cast bits (595)"""
        level = st.skills.get(slot, 0) + 1
        answer = LP.skill_up_676(slot, level)
        print(f'{t:8.3f}   skill up request slot {slot} -> level {level} ({answer and answer.hex()})', flush=True)
        if answer:
            st.skills[slot] = level
            send_message(addr, st, 1, struct.pack('<HI', 676, hero) + answer, f'676 skill {slot} level {level}')
            # mReplicatedSpellCanCastBitsLower1 (group 0 bit 3): summoner spells 4, 5 and recall 13 as in the
            # replay's first value (0x2030), plus every learned spell
            bits = 0x2030 | sum(1 << k for k, v in st.skills.items() if v > 0)
            # The client applies a replication packet only when its counter is newer than the last one it took.
            # The fixed head and trailer of a replay packet carry an old counter: once any of our own 595 (hero
            # stats, gold) had gone out, these bits were ignored - the point showed, the spell could not be cast.
            import repl_codec as RC
            hp_counter[0] += 1
            game_now_ = stream_t0[1] + (time.time() - stream_t0[0]) * speed if stream_t0 else 0.0
            send_message(addr, st, 2, struct.pack('<HI', 595, 0) +
                         RC.packet([(hero, {'mReplicatedSpellCanCastBitsLower1': bits}, RC.HERO)], game_now_, hp_counter[0]),
                         f'595 can-cast bits {bits:#x}')

    def cast_q(addr, st, t):
        """answer to a cast request (16): the replay's first Q of the hero, its 49 rebuilt by us with --own-49"""
        import copy
        now = time.time()
        for i, (dt, ch0, pid0, body0) in enumerate(q_reply):
            what = f'Q reply {pid0} +{dt:.2f}s'
            if own_49 is not None and i in own_49:
                sc_p, v0 = own_49[i]
                v = copy.deepcopy(v0)
                game_t = stream_t0[1] + (now - stream_t0[0]) * speed if stream_t0 else 0.0
                what = f'our {pid0} +{dt:.2f}s'
                if pid0 == 49:
                    cast = v['+0xc']
                    t0_ = struct.unpack('<f', bytes.fromhex(cast['+0x78']))[0]
                    t1_ = struct.unpack('<f', bytes.fromhex(cast['+0x8c']['+0x10']))[0]
                    cast['+0x78'] = struct.pack('<f', game_t).hex()
                    cast['+0x8c']['+0x10'] = struct.pack('<f', game_t + (t1_ - t0_)).hex()
                    cast['+0x8c']['+0x18'] = struct.pack('<H', hero_skin).hex()
                    what = f'our 49 (cast at game time {game_t:.2f}, skin {hero_skin})'
                if pid0 == 271 and q_cooldown is not None and v['+0x14'] != '00000000':
                    # 271 at the end of the cast: the spell's cooldown (+0x14 left, +0x18 total; 9 s for Q level 1)
                    v['+0x14'] = v['+0x18'] = struct.pack('<f', q_cooldown).hex()
                    what = f'our 271 (cooldown {q_cooldown} s)'
                if pid0 == 453 and q_gold is not None:
                    # 453 = gold earned: +0xc amount (float), +0x10 who gets it, +0x18 the unit it came from (the replay:
                    # 21 for the minion this Q killed)
                    v['+0xc'] = struct.pack('<f', q_gold).hex()
                    what = f'our 453 (gold {q_gold})'
                if pid0 == 65:
                    what = f'our 65 (animation {bytes.fromhex(v["+0xc"]["text"]).decode()})'
                body0 = sc_p.encode(v)
            scheduled.append((now + dt, addr, ch0, struct.pack('<HI', pid0, hero) + body0, what))
        print(f'{t:8.3f}   cast -> {len(q_reply)} packets of the replay Q', flush=True)
        if own_49 is not None and q_kill is not None and kill_tpl:
            nid = struct.pack('<I', q_kill).hex()
            me = struct.pack('<I', hero).hex()
            if 263 in kill_tpl:
                ch_, sc_, v = kill_tpl[263]
                v = copy.deepcopy(v)
                v['+0xc'], v['+0x20'] = nid, me      # target, source
                scheduled.append((now + 0.76, addr, ch_, struct.pack('<HI', 263, q_kill) + sc_.encode(v),
                                  f'our 263 ({struct.unpack("<f", bytes.fromhex(v["+0x14"]))[0]:.1f} damage to {q_kill:#x})'))
            if 61 in kill_tpl:
                ch_, sc_, v = kill_tpl[61]
                v = copy.deepcopy(v)
                v['+0x2c'] = me                      # killer
                scheduled.append((now + 0.77, addr, ch_, struct.pack('<HI', 61, q_kill) + sc_.encode(v),
                                  f'our 61 (death of {q_kill:#x}, killed by {hero:#x})'))
        if '--shots-on-cast' in args:
            # ask the GPU sponge (d3d11.dll proxy next to the client) for frames during the cast
            for dt in (0.25, 0.5, 0.8, 1.1, 2.0, 3.5):
                cast_shots.append(now + dt)

    def add_buff(addr, st, target, name, secs, btype, at):
        """our 693 (buff put on target, by the ELF hash of its name) at `at`, and its 522 (taken off) secs later"""
        import copy
        import spell_info as SI
        f32 = lambda x: struct.pack('<f', x).hex()
        h = struct.pack('<I', SI.elf(name)).hex()
        # buff slot on the unit: the replay's own buffs use slots up to 65 (0x41) -- ours take 0x48.. so they never meet
        st.buff_next = getattr(st, 'buff_next', 0x48)
        bslot = st.buff_next
        st.buff_next = 0x48 + (st.buff_next - 0x48 + 1) % 0x30
        sc, v0 = cast_tpl[693]
        v = copy.deepcopy(v0)
        v['+0x10'] = h
        v['+0x15'] = f'{bslot:02x}'
        v['+0x16'] = '03'
        v['+0x18'] = f32(secs)
        v['+0x34'] = f'{btype:02x}'
        v['+0x44'] = struct.pack('<I', hero).hex()
        if buff_family is not None:
            v['+0x2c'] = buff_family
        scheduled.append((at, addr, cast_tpl['ch693'], struct.pack('<HI', 693, target) + sc.encode(v),
                          f'our 693: buff {name} on {target:#x} slot {bslot:#x} type {btype} for {secs} s'))
        if 522 in cast_tpl:
            sc2, w0 = cast_tpl[522]
            w = copy.deepcopy(w0)
            w['+0xa'] = f'{bslot:02x}'
            w['+0x10'] = h
            scheduled.append((at + secs, addr, cast_tpl['ch522'], struct.pack('<HI', 522, target) + sc2.encode(w),
                              f'our 522: buff {name} off {target:#x} slot {bslot:#x}'))

    def engine_hits(addr, st, spell, slot, rank, aim, aimed=None):
        """who the cast hits and for how much (spell_engine.py: shape and damage from the spell's data); every hit
        lowers the target's health (595), shows its damage (263) and may kill"""
        import positions as POs
        import spell_calc as SCc
        import spell_info as SI
        champ = hero_champion
        sh = SE.shape(champ, spell, rank)
        game_now_ = stream_t0[1] + (time.time() - stream_t0[0]) * speed if stream_t0 else 0.0
        my_team = 'red' if hero_teams.get(hero) in ('red', 200) else 'blue'
        units = []
        if world_[0] is not None:
            # our own world (world.py): enemy lane minions, the jungle's monsters, the enemy champions
            units = world_[0].targets_for(my_team, game_now_)
        else:
            for net, name in hero_names.items():
                if net == hero or net in dead_units or hero_teams.get(net) == my_team:
                    continue
                pos = POs.at(net, game_now_)
                if pos:
                    units.append((net, pos, unit_radius(name)))
            for net, m in minions.items():
                if net in dead_units or m['team'] == my_team or not (m['spawn'] <= game_now_ < (m['death'] or 1e9)):
                    continue
                pos = POs.at(net, game_now_)
                if pos:
                    units.append((net, pos, 48.0))       # lane minion radius [approximation]
        me = hero_pos(st)
        got = SE.hits(sh, me, aim, units)
        if aimed is not None:
            # a targeted spell hits the unit the client named in its request, when that one can be hit
            got = [(n_, math.hypot(p_[0] - me[0], p_[1] - me[1])) for n_, p_, r_ in units if n_ == aimed] or got
        rec = SI.char_record(champ)
        stats = SCc.Stats(ad=(char_level_value(float(rec['baseDamage']), float(rec['damagePerLevel']), 1), 0.0),
                          ap=(0.0, 0.0))
        dm = SE.damage(champ, spell, rank, 1, stats)
        print(f'engine: {spell} ({sh["targeting"]}, range {sh["range"]:.0f}, radius {sh["radius"]:.0f}, '
              f'width {sh["width"]:.0f}, missile {sh["missile_speed"]:.0f}) hits {[hex(n) for n, _ in got]}, '
              f'damage {dm}', flush=True)
        if not dm or not got:
            return
        raw, kind, calc_name = dm
        for net, travel in got:
            tr = SI.char_record(hero_names[net]) if net in hero_names else {}
            resist = char_level_value(float(tr.get('baseArmor', 0)), float(tr.get('armorPerLevel', 0)), 1) if kind == 0 else \
                char_level_value(float(tr.get('baseSpellBlock', 0)), float(tr.get('spellBlockPerLevel', 0)), 1)
            dmg = raw * 100 / (100 + resist)
            at = time.time() + SE.hit_delay(champ, sh, travel)

            def only263(k, p, v, dmg=dmg, kind=kind):
                if p['pid'] != 263:
                    return None
                v['+0x14'] = struct.pack('<f', dmg).hex()
                v['+0x10'] = f'{kind:02x}'            # 0 physical, 1 magic, 2 true (replay: Azir 1, Darius R 2)
                v['+0xa'], v['+0x1c'], v['+0x1d'] = '00', '04', '00'
                return v
            if world_[0] is None:
                emit_template(addr, st, 'darius_aa_hit', {0x4000001e: hero, 0x4000026b: net}, at, only263)
            apply_damage(addr, st, net, dmg, at, source=f'spell:{slot}:{spell}:{kind}')
            print(f'engine: {spell} -> {net:#x}: {dmg:.1f} ({"magic" if kind else "physical"}, {calc_name} {raw:.1f}) '
                  f'at +{at - time.time():.2f} s', flush=True)

    # champions of the replay: their casts as Riot's server sent them (auto_templates.py: the modal packet sequence
    # of the cast tick, every field classed FIXED / varying over all casts); varying fields are computed with the
    # rules checked on the replay, the FIXED ones are copied (protocol facts)
    AUTO_DIR = os.path.join(HERE, '..', 'data', 'exe133', 'templates', 'auto')
    buff_slots = {}

    def alloc_slot(unit):
        """a buff slot on a unit: the lowest one not used by our own buffs, from 0x30 (the real server's rule is the
        lowest free slot, but it counts internal buffs the client never sees -- not reproducible from the replay)"""
        used = buff_slots.setdefault(unit, set())
        s_ = 0x30
        while s_ in used:
            s_ += 1
        used.add(s_)
        return s_

    def emit_auto(addr, st, spell, slot, level, aim, data, any_champion=False):
        import copy
        import spell_info as SI
        path = os.path.join(AUTO_DIR, hero_champion, f'{spell}.json')
        tpl_champ = hero_champion
        if not os.path.exists(path) and any_champion:
            for c_ in sorted(os.listdir(AUTO_DIR)):
                if os.path.exists(os.path.join(AUTO_DIR, c_, f'{spell}.json')):
                    path, tpl_champ = os.path.join(AUTO_DIR, c_, f'{spell}.json'), c_
                    break
        if not os.path.exists(path):
            return False
        tpl = _json2.load(open(path))
        f32 = lambda x: struct.pack('<f', x).hex()
        u32 = lambda x: struct.pack('<I', x).hex()
        now = time.time()
        game_t = stream_t0[1] + (now - stream_t0[0]) * speed if stream_t0 else 0.0
        me = hero_pos(st)
        y = 171.0
        is_self = data.get('targeting', '').startswith('Self')
        point = (me[0], y, me[1]) if is_self else (aim[0], y, aim[1])
        if not is_self:
            face(st, me, aim)
        cd = data['cd_override'] if 'cd_override' in data else cooldown(spell, level) if data.get('cooldown') else 0.0
        st.spell_cds = getattr(st, 'spell_cds', {})
        st.spell_cds[slot] = now + cd
        mana = SI.at_level(data['mana'], level) if data.get('mana') else 0.0

        def fix(k, p, v):
            pid = p['pid']
            varying = set(tpl['varying'].get(str(k), []))
            if pid == 49:
                c = v['+0xc']
                sp_name = name_of_hash(c['+0xbc'])
                w_, tot_ = SI.cast_times(hero_champion, sp_name) if sp_name else (struct.unpack('<f', bytes.fromhex(c['+0x24']))[0], 1.0)
                st.cast_count = getattr(st, 'cast_count', 0x100) + 1
                c['+0x80'] = u32(st.cast_count)
                c['+0x78'] = f32(game_t)
                c['+0x8c']['+0x10'] = f32(game_t + float(w_))
                c['+0x4c'] = c['+0x60'] = struct.pack('<3f', *point).hex()
                c['+0x60'] = struct.pack('<3f', me[0], y, me[1]).hex()
                c['+0x28'] = facing_hex(st)
                c['+0x1c'] = u32(0x40100000 + 2 * st.cast_count)
                c['+0xc4'] = u32(0x40100001 + 2 * st.cast_count)
                c['+0x8c']['+0x1c'] = next_instance()
                c['+0x8c']['+0x18'] = struct.pack('<H', hero_skin).hex()
                if '+0xc+0x8[]' in varying:
                    c['+0x8'] = []
                if '+0xc+0xc8' in varying:
                    c['+0xc8'] = f32(cd)
                if '+0xc+0x84' in varying:
                    c['+0x84'] = f32(mana)
                if '+0xc+0x42' in varying:
                    c['+0x42'] = struct.pack('<H', level - 1).hex()
            elif pid == 693 and p['who'] == 'caster':
                v['+0x15'] = f'{alloc_slot(hero):02x}'
                own_buffs[v['+0x10']] = int(v['+0x15'], 16)
            elif pid == 271:
                if '+0x14' in varying and v['+0x14'] != '00000000':
                    v['+0x14'] = v['+0x18'] = f32(cd)
            elif pid == 516:
                v['+0xc'] = struct.pack('<3f', *point).hex()
            return v
        fix.declared = {49: ['+0xc+0x80', '+0xc+0x78', '+0xc+0x8c+0x10', '+0xc+0x4c', '+0xc+0x60', '+0xc+0x28',
                             '+0xc+0x1c', '+0xc+0xc4', '+0xc+0x8c+0x1c', '+0xc+0xc8', '+0xc+0x84', '+0xc+0x42'],
                        693: ['+0x15'], 271: ['+0x14', '+0x18'], 516: ['+0xc']}
        own_buffs = {}
        emit_template(addr, st, f'auto/{tpl_champ}/{spell}', {tpl['caster']: hero}, 0, fix)
        print(f'auto cast {hero_champion} {spell}: sequence {tpl["sequence"]} (replay: {tpl["sequence_cases"]} of '
              f'{tpl["casts"]} casts)', flush=True)
        if 118 in tpl['sequence']:
            # the cast arms the next attack (118 = the attack slot, 259 = the attack spell put there), as Darius W
            p118 = next(p for p in tpl['packets'] if p['pid'] == 118)
            p259 = next((p for p in tpl['packets'] if p['pid'] == 259), None)
            atk = bytes.fromhex(p259['values']['+0x18']['text']).decode().rstrip('\x00') if p259 else ''
            st.armed = {'spell': spell, 'slot': slot, 'rank': level, 'attack': atk,
                        'atk_slot': int(p118['values']['+0xa'], 16), 'buffs': own_buffs}
            if getattr(st, 'aa', None):
                st.aa['next'] = time.time()           # an attack reset: the empowered attack goes at once
            print(f'armed: next attack = {atk} (slot {st.armed["atk_slot"]:#x})', flush=True)
            return 'armed'
        return True

    _spell_by_hash = {}

    def name_of_hash(h):
        """a spell of the hero's champion by the ELF hash 49 carries (its own SpellObjects; no big dictionary here:
        name_hashes.json takes tens of seconds to load)"""
        import bin_tree as BTn
        import spell_info as SIn
        if not _spell_by_hash:
            for nm_ in BTn.champion_spells(hero_champion):
                _spell_by_hash[struct.pack('<I', SIn.elf(nm_)).hex()] = nm_
        return _spell_by_hash.get(h)

    # summoner spells (D / F = slots 4 / 5): which ones the hero has comes from its own casts in the replay (Darius:
    # D SummonerHaste, F SummonerFlash); the cast is any champion's replay template of that spell; Flash moves the hero
    # (552 teleport entry, 400 units: median 393 over the replay's 34 Flash teleports; the data's indicator says 425)
    hero_summoners = {}
    try:
        import json as _json2
        _cnt = collections.Counter()
        for line in open(os.path.join(HERE, '..', 'data', 'exe133', 'codec', '49.all.jsonl')):
            r_ = _json2.loads(line)
            if r_['v'] and r_['obj'] == hero and int(r_['v']['+0xc']['+0x34'], 16) in (4, 5):
                _cnt[(int(r_['v']['+0xc']['+0x34'], 16), r_['v']['+0xc']['+0xbc'])] += 1
        for (sl_, h_), _n in _cnt.most_common():
            hero_summoners.setdefault(sl_, h_)
    except OSError:
        pass
    teleports = {}

    def summoner_cast(addr, st, slot, aim):
        import math
        import spell_info as SIs
        h = hero_summoners.get(slot)
        if not h:
            return
        # the summoner spell's name: one of the replay templates' names with that ELF hash (no big dictionary here)
        names = {f[:-5] for c_ in os.listdir(AUTO_DIR) if os.path.isdir(os.path.join(AUTO_DIR, c_))
                 for f in os.listdir(os.path.join(AUTO_DIR, c_)) if f.endswith('.json')}
        spell = next((n_ for n_ in names if struct.pack('<I', SIs.elf(n_)).hex() == h), None)
        if not spell:
            return
        cds = {'SummonerFlash': 300.0, 'SummonerHaste': 240.0}          # Global spells' cooldownTime (SummonerFlash 300)
        done = emit_auto(addr, st, spell, slot, 1, aim, {'cd_override': cds.get(spell, 0.0)}, any_champion=True)
        print(f'summoner {slot}: {spell} ({"replay template" if done else "no template"})', flush=True)
        if spell == 'SummonerFlash':
            me = hero_pos(st)
            dx, dz = aim[0] - me[0], aim[1] - me[1]
            d = math.hypot(dx, dz) or 1.0
            k = min(d, 400.0) / d
            dest = (me[0] + dx * k, me[1] + dz * k)
            import waypoints as Wt
            cell = (int(round((dest[0] - Wt.CENTER[0]) / Wt.CELL)), int(round((dest[1] - Wt.CENTER[1]) / Wt.CELL)))
            teleports[hero] = teleports.get(hero, 1) + 1
            entry = LP.waypoint_teleport(hero, cell, float(SI_char()['baseMoveSpeed']), teleports[hero])
            send_message(addr, st, 2, struct.pack('<HI', 552, 0) + LP.encode_552(entry),
                         f'552 Flash: hero to ({dest[0]:.0f}, {dest[1]:.0f}), teleport {teleports[hero]}')
            st.pos, st.path = dest, None
            face(st, me, dest)

    def SI_char():
        import spell_info as SI
        return SI.char_record(hero_champion)

    def generic_cast(addr, st, t, slot, target, caster, target_net=0):
        """any spell of the hero (--hero-spells, slot 0..3): our own 49 (spell named by its ELF hash, its rank's
        cooldown and mana from the game files), 65 (the spell's animation) and 271 (its cooldown), built on the
        replay's first Q of the hero as a template (pkt_schema decodes it once)"""
        import copy
        import spell_info as SI
        if not cast_tpl:
            return
        spell = engine_spells[slot]
        data = SI.spells(hero_champion).get(spell, {})
        level = max(st.skills.get(slot, 1), 1)
        cd = SI.at_level(data['cooldown'], level) if data.get('cooldown') else 0.0
        mana = SI.at_level(data['mana'], level) if data.get('mana') else 0.0
        # windup and total time of the cast as Riot's server writes them (spell_info.cast_times, checked on the replay)
        windup, total = SI.cast_times(hero_champion, spell)
        done = emit_auto(addr, st, spell, slot, level, target, data)
        if done:
            if done != 'armed':
                engine_hits(addr, st, spell, slot, level, target)
            if '--shots-on-cast' in args:
                for dt in (0.15, 0.4, 0.8, 1.5):
                    cast_shots.append(time.time() + dt)
            return
        now = time.time()
        game_t = stream_t0[1] + (now - stream_t0[0]) * speed if stream_t0 else 0.0
        st.cast_count = getattr(st, 'cast_count', 0x100) + 1
        f32 = lambda x: struct.pack('<f', x).hex()
        u32 = lambda x: struct.pack('<I', x).hex()
        # The cast's places as Riot's server writes them (measured on the replay's casts, the caster's place known
        # from its own path): 49 +0xc+0x60 = where the CASTER stands, +0xc+0x4c = the target place -- a line
        # missile's is the end of its flight, caster + aimed direction x cast range (JavelinToss 1498 away with
        # castRange 1500, BlindMonkQOne 1200), a ground spell's is the aimed place, a targeted spell's the unit's
        # place (and the unit in +0xc+0x8), a self spell's the caster's; +0xc+0x28 = where the caster looked when
        # the cast began; heights are the ground's (navgrid.height). We wrote the TARGET into both places and took
        # the caster's place from the request, where it is the aimed place for every aimed spell: start = end,
        # direction 0 -- no missile of a champion outside the replay had anywhere to fly.
        import math
        import navgrid as NGc
        ground = NGc.grid().height
        me = hero_pos(st)
        sh = SE.shape(hero_champion, spell, level)
        kind = sh['targeting']
        tx, tz = target
        dx, dz = tx - me[0], tz - me[1]
        n = math.hypot(dx, dz)
        ux, uz = (dx / n, dz / n) if n > 1e-3 else getattr(st, 'facing', (0.0, 1.0))
        rng = sh['range']
        y_me = ground(*me)
        aimed = None
        unit_at = world_[0].place(target_net, game_t) if world_[0] is not None and target_net and target_net != hero else None
        if kind in ('Self', 'SelfAoe'):
            point, y_pt = me, y_me
        elif kind in ('Target', 'TargetOrLocation') and unit_at is not None:
            aimed, point = target_net, unit_at
            y_pt = ground(*point)
        elif kind in ('direction', 'DragDirection', 'WallDetection') or (
                kind in ('Location', 'LocationClamped') and sh['width'] > 0 and sh['missile_speed'] > 0):
            L = rng or n
            point, y_pt = (me[0] + ux * L, me[1] + uz * L), y_me
        else:
            L = min(n, rng) if rng else n
            point = (me[0] + ux * L, me[1] + uz * L)
            y_pt = y_me if kind == 'Cone' else ground(*point)
        tx, tz = point
        sc49, v49 = cast_tpl[49]
        v = copy.deepcopy(v49)
        c = v['+0xc']
        c['+0x8c']['+0x14'] = c['+0xbc'] = u32(SI.elf(spell))
        c['+0x8c']['+0x24'] = {'text': hero_champion.encode().hex()}
        c['+0x8c']['+0x18'] = struct.pack('<H', hero_skin).hex()
        c['+0x34'] = f'{slot:02x}'
        c['+0x80'] = u32(st.cast_count)
        c['+0x84'] = f32(mana)
        c['+0xc8'] = f32(cd)
        c['+0x24'] = f32(windup)
        c['+0x58'] = f32(total)
        c['+0x78'] = f32(game_t)
        c['+0x8c']['+0x10'] = f32(game_t + windup)
        c['+0x4c'] = struct.pack('<3f', point[0], y_pt, point[1]).hex()
        c['+0x60'] = struct.pack('<3f', me[0], y_me, me[1]).hex()
        c['+0x28'] = facing_hex(st)
        if kind not in ('Self', 'SelfAoe'):
            face(st, me, point)
        # ids of the cast and of its missile: one counter of their own (the attacks' ids come from another rule;
        # two live objects under one id replace each other in the client)
        st.obj_ids = getattr(st, 'obj_ids', 0x40300000) + 2
        c['+0x1c'] = u32(st.obj_ids)
        c['+0xc4'] = u32(st.obj_ids + 1)
        c['+0x8'] = [{'+0x4': u32(aimed), '+0x8': '00'}] if aimed else []
        send_message(addr, st, cast_tpl['ch49'], struct.pack('<HI', 49, hero) + sc49.encode(v),
                     f'our 49: {spell} (slot {slot}, rank {level}, cooldown {cd}, mana {mana}, windup {windup:.3f}, total {total:.3f}; '
                     f'{kind} from ({me[0]:.0f}, {me[1]:.0f}) to ({point[0]:.0f}, {point[1]:.0f})' + (f' on {aimed:#x}' if aimed else '') + ')')
        if sh.get('own_missile'):
            # The spell's own missile leaves when the cast time is over: 779 naming the cast (49 +0xc+0xc4), one tick
            # after the windup (replay: every one of 88 Lee Sin Q, 145 of 146 Nidalee Q, 57 of 60 Jhin Q, +0.014 s
            # median; no cast of a spell without an mMissileSpec of its own gets one). Seen in the client with
            # Caitlyn's Q (match_spells1: the bullet flies its line); before, such spells did their damage with
            # nothing flying.
            sc779 = PS2.Schema.load(779)
            scheduled.append((now + windup + 0.014, addr, 1, struct.pack('<HI', 779, hero) + sc779.encode({'+0xc': c['+0xc4']}),
                              f'779 {spell}: its missile leaves'))
        elif EXTRA_MISSILE and kind not in ('Self', 'SelfAoe') and SE.missile_spell(hero_champion, spell, kind == 'Cone'):
            # The missile is a spell of its own (RocketGrab -> RocketGrabMissile, Volley -> VolleyAttack). Riot's
            # server puts that spell in an extra slot (259, slot 0x2d) when the cast time is over and creates the
            # missile with a packet we cannot write yet (117). In its place the missile spell is cast like a spell
            # that owns its missile: 259, its own 49 from that slot, 779 naming it. Seen in the client with
            # Caitlyn's E (the net) and R (the bullet flies to its target), match_spells1 [the way is ours; which
            # spell is THE missile when several are named after the cast is our choice: spell_engine.missile_spell].
            # A cone's missiles: as many as the spell's own 'NumberOf...' value says (else 3), spread over the cone
            # (castConeAngle each side) [approximation].
            ms = SE.missile_spell(hero_champion, spell, kind == 'Cone')
            ways = [(ux, uz)]
            if kind == 'Cone':
                count = next((int(SI.at_level(v_, level)) for k_, v_ in data.get('values', {}).items()
                              if k_.lower().startswith('numberof') and v_), 3)
                half = math.radians(sh['cone_angle'] or 22.5)
                base = math.atan2(uz, ux)
                ways = [(math.cos(a_), math.sin(a_)) for a_ in
                        (base - half + 2 * half * i_ / max(count - 1, 1) for i_ in range(count))]
            sc259 = spell_codec()[0]
            v259 = {'+0xc': {'+0x4': '00', '+0x5': '00', '+0x6': '00', '+0x7': '2d', '+0x8': '02000000'},
                    '+0x18': {'text': (ms.encode() + b'\0').hex()}}
            at2 = now + windup + 0.014
            scheduled.append((at2, addr, 1, struct.pack('<HI', 259, hero) + sc259.encode(v259), f'our 259: slot 45 = {ms}'))
            sc779 = PS2.Schema.load(779)
            reach = math.hypot(point[0] - me[0], point[1] - me[1]) if kind != 'Cone' else (sh['cone_distance'] or rng or 600.0)
            for wx_, wz_ in ways:
                st.obj_ids += 2
                v2 = copy.deepcopy(v)
                c2 = v2['+0xc']
                c2['+0x8c']['+0x14'] = c2['+0xbc'] = u32(SI.elf(ms))
                c2['+0x34'] = '2d'
                c2['+0x24'] = f32(0.0)
                c2['+0x84'] = c2['+0xc8'] = f32(0.0)
                c2['+0x78'] = f32(game_t + windup)
                c2['+0x8c']['+0x10'] = f32(game_t + windup)
                c2['+0x1c'], c2['+0xc4'] = u32(st.obj_ids), u32(st.obj_ids + 1)
                if len(ways) > 1:
                    c2['+0x4c'] = struct.pack('<3f', me[0] + wx_ * reach, y_me, me[1] + wz_ * reach).hex()
                st.cast_count += 1
                c2['+0x80'] = u32(st.cast_count)
                scheduled.append((at2, addr, cast_tpl['ch49'], struct.pack('<HI', 49, hero) + sc49.encode(v2),
                                  f'our 49: {ms} (the missile of {spell}, slot 45)'))
                scheduled.append((at2, addr, 1, struct.pack('<HI', 779, hero) + sc779.encode({'+0xc': c2['+0xc4']}),
                                  f'779 {ms}: the missile leaves'))
        # Play the spell's animation and particles (packet 65) for all champions
        anim_name = data.get('animation')
        empowers = data.get('targeting', '').startswith('Self') and (spell + 'Attack') in SI.spells(hero_champion)
        if anim_name and 65 in cast_tpl and '--no-anim' not in args and not empowers:
            sc65, v65 = cast_tpl[65]
            v = copy.deepcopy(v65)
            v['+0xc'] = {'text': anim_name.encode().hex()}
            send_message(addr, st, cast_tpl['ch65'], struct.pack('<HI', 65, hero) + sc65.encode(v), f'our 65: {anim_name}')
        st.spell_cds = getattr(st, 'spell_cds', {})
        st.spell_cds[slot] = now + cd
        if 271 in cast_tpl and cd > 0:
            sc271, v271 = cast_tpl[271]
            v = copy.deepcopy(v271)
            v['+0x10'] = f'{slot:02x}'
            v['+0x14'] = v['+0x18'] = f32(cd)
            send_message(addr, st, cast_tpl['ch271'], struct.pack('<HI', 271, hero) + sc271.encode(v),
                         f'our 271: slot {slot} cooldown {cd:.1f}')
        # what the spell does besides the cast: buffs and held animations (spell_effects.py, sources there)
        import spell_effects as SEf
        for kind, name, secs, btype in SEf.effects(spell, data, level):
            if kind == 'buff' and 693 in cast_tpl:
                add_buff(addr, st, hero, name, secs, btype, now + windup)
            elif kind == 'hold' and 65 in cast_tpl and '--no-anim' not in args:
                sc65, v65 = cast_tpl[65]
                v = copy.deepcopy(v65)
                v['+0xc'] = {'text': name.encode().hex()}
                v['+0x24'] = f32(secs)
                v['+0x31'] = '01'
                send_message(addr, st, cast_tpl['ch65'], struct.pack('<HI', 65, hero) + sc65.encode(v), f'our 65: {name} held {secs} s')
        if empowers:
            # how long the next attack stays empowered is not read from the data yet [approximation: 4.5 s]
            st.next_attack_spell = {'spell': spell, 'slot': slot, 'rank': level, 'until': now + 4.5,
                                    'animation': SI.spells(hero_champion)[spell + 'Attack'].get('animation') or data.get('animation')}
            print(f'{spell}: the next basic attack within 4.5 s is {spell}Attack', flush=True)
            return
        engine_hits(addr, st, spell, slot, level, target, aimed)
        if '--shots-on-cast' in args:
            for dt in (0.15, 0.4, 0.8, 1.5):
                cast_shots.append(now + dt)

    # Darius W as Riot's server sends it: the replay's own cast tick and hit tick (spell_templates.py), rewritten
    # with our ids, times and positions. The hit comes 0.329 s after the cast, as in the replay (166.867 -> 167.196).
    w_tpl = None
    schema_cache = {}

    # provenance audit: for every template packet we send, which fields we swapped (ids) and which we computed; the
    # rest is copied from the replay's moment (template_audit.py compares that with how the field varies in the replay)
    audit = {}
    AUDIT_PATH = os.path.join(HERE, '..', 'data', 'exe133', 'audit_runtime.json')

    def paths_changed(a, b, path=''):
        out = set()
        if isinstance(a, dict) and isinstance(b, dict) and 'text' not in a:
            for k in set(a) | set(b):
                out |= paths_changed(a.get(k), b.get(k), path + k)
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for i, (x, y) in enumerate(zip(a, b)):
                out |= paths_changed(x, y, f'{path}[{i}]')
        elif a != b:
            out.add(path)
        return out

    def audit_note(name, k, pid, who, swapped, computed):
        import json as _ja
        key = f'{name}#{k}'
        e = audit.setdefault(key, {'pid': pid, 'who': who, 'swapped': [], 'computed': [], 'sent': 0})
        e['swapped'] = sorted(set(e['swapped']) | swapped)
        e['computed'] = sorted(set(e['computed']) | computed)
        e['sent'] += 1
        try:
            _ja.dump(audit, open(AUDIT_PATH, 'w'), indent=1)
        except OSError:
            pass

    def emit_template(addr, st, name, ids, at, fix=None):
        """every packet of a template, its ids swapped (template id -> ours, as 4-byte hex anywhere in the values)"""
        import copy
        import json as _json
        import pkt_schema as PSw
        import spell_templates as STm
        tpl = STm.load(name)
        swap = {struct.pack('<I', a).hex(): struct.pack('<I', b).hex() for a, b in ids.items()}

        def sub(x):
            if isinstance(x, dict) and 'text' in x and isinstance(x['text'], str):
                h_ = x['text']             # ids inside a byte blob (750): swapped where they sit on a byte boundary
                for a_, b_ in swap.items():
                    i_ = h_.find(a_)
                    while i_ >= 0:
                        if i_ % 2 == 0:
                            h_ = h_[:i_] + b_ + h_[i_ + 8:]
                        i_ = h_.find(a_, i_ + 2)
                return {'text': h_}
            if isinstance(x, dict):
                return {k: sub(v) for k, v in x.items()}
            if isinstance(x, list):
                return [sub(v) for v in x]
            if isinstance(x, str) and len(x) == 8 and x in swap:
                return swap[x]
            return x
        for k, p in enumerate(tpl['packets']):
            if p['values'] is None:
                continue
            v = sub(copy.deepcopy(p['values']))
            swapped = paths_changed(p['values'], v)
            if fix:
                before = copy.deepcopy(v)
                v = fix(k, p, v)
                if v is None:
                    continue
                computed = paths_changed(before, v) | set(getattr(fix, 'declared', {}).get(p['pid'], ()))
            else:
                computed = set()
            audit_note(name, k, p['pid'], p['who'], swapped, computed)
            obj = 0 if p['who'] == 'global' else ids.get(tpl['caster'] if p['who'] == 'caster' else tpl['target'], 0)
            sc = schema_cache.get(p['pid']) or schema_cache.setdefault(p['pid'], PSw.Schema.load(p['pid']))
            scheduled.append((at, addr, p['ch'], struct.pack('<HI', p['pid'], obj) + sc.encode(v),
                              f"our {p['pid']} ({name} #{k}, {p['who']})"))

    # the hero's facing (49 +0xc+0x28): the latest of its movement direction and its attack direction -- 165 of
    # Darius's 199 replay casts; the turn is gradual in the game, so the rest falls in between (not modelled)
    def face(st, frm, to):
        import math
        dx, dz = to[0] - frm[0], to[1] - frm[1]
        n = math.hypot(dx, dz)
        if n > 1e-3:
            st.facing = (dx / n, dz / n)

    def facing_hex(st):
        fx, fz = getattr(st, 'facing', (0.0, 1.0))
        return struct.pack('<3f', fx, 0.0, fz).hex()

    # 49 +0xc+0x8c+0x1c: a different value for every cast in the replay (96 / 96 for Darius's W): an instance id, made
    # unique here (its rule is not known)
    instance_ids = [0x3000]

    def next_instance():
        instance_ids[0] += 1
        return struct.pack('<I', instance_ids[0]).hex()

    # cooldown = the rank's cooldownTime x 100 / (100 + ability haste) -- all 172 casts of Darius's Q/W/E/R in the
    # replay (haste from 595 mAbilityHasteMod); our hero has no haste
    def cooldown(spell, rank, haste=0.0):
        import spell_info as SI
        return SI.at_level(SI.spells(hero_names.get(hero, 'Darius'))[spell]['cooldown'], rank) * 100 / (100 + haste)

    def darius_w(addr, st, target, part='both'):
        """part 'cast': the cast tick without the attack (592, 516), the next attack is armed; 'attack': only the
        armed attack (592, 516) and the hit; 'both': all of it (W while attacking: the attack reset)"""
        f32 = lambda x: struct.pack('<f', x).hex()
        now = time.time()
        game_t = stream_t0[1] + (now - stream_t0[0]) * speed if stream_t0 else 0.0
        st.cast_count = getattr(st, 'cast_count', 0x100) + 2
        cast_id, attack_id = 0x40100000 + 4 * st.cast_count, 0x40100001 + 4 * st.cast_count
        me2 = hero_pos(st)
        tp2 = (getattr(st, 'aa', None) or {}).get('tp', (me2[0] + 150.0, me2[1] + 50.0))
        me_xyz = (me2[0], 171.0, me2[1])           # the height of the fountain (79); the terrain's is not read yet
        tg_xyz = (tp2[0], 171.0, tp2[1])
        me_pos = struct.pack('<3f', *me_xyz).hex()
        tg_pos = struct.pack('<3f', *tg_xyz).hex()
        if target:
            face(st, me2, tp2)
        w_cd = cooldown('DariusNoxianTacticsONH', max(st.skills.get(1, 1), 1))
        ids = {0x4000001e: hero, 0x400006e1: target, 0x40000baa: cast_id, 0x40000ba9: cast_id + 2,
               0x40000bb2: attack_id}

        def fix_cast(k, p, v):
            if p['pid'] == 49:
                c = v['+0xc']
                c['+0x78'] = f32(game_t)
                c['+0x8c']['+0x10'] = f32(game_t + 0.3667)
                c['+0x80'] = struct.pack('<I', st.cast_count).hex()
                c['+0x4c'] = c['+0x60'] = me_pos
                c['+0xc8'] = f32(w_cd)
                c['+0x28'] = facing_hex(st)
                c['+0x42'] = struct.pack('<H', max(st.skills.get(1, 1), 1) - 1).hex()   # rank - 1 (Q at rank 5: 4, 51 / 62)
                c['+0x8c']['+0x1c'] = next_instance()
            if p['pid'] == 592:
                a = v['+0xc']
                a['+0x4'] = struct.pack('<I', st.cast_count + 1).hex()
                a['+0x24'] = tg_pos
                c = a['+0x10'][0]
                c['+0x78'] = f32(game_t)
                c['+0x8c']['+0x10'] = f32(game_t + 0.3045)
                c['+0x80'] = struct.pack('<I', st.cast_count + 1).hex()
                c['+0x4c'] = tg_pos
                c['+0x60'] = me_pos
                c['+0x8c']['+0x1c'] = next_instance()
                a['+0x1c'] = '80'          # 0x80 on the first attack of a series (lower on chained attacks: a timing offset)
                v['+0x3c'] = struct.pack('<ff', me_xyz[0], me_xyz[2]).hex()
            if p['pid'] == 516:
                v['+0xc'] = tg_pos
            return v
        fix_cast.declared = {49: ['+0xc+0xc8', '+0xc+0x28', '+0xc+0x8c+0x1c', '+0xc+0x42'], 592: ['+0xc+0x1c']}

        def fix_part(k, p, v):
            if (part == 'cast' and p['pid'] in (592, 516)) or (part == 'attack' and p['pid'] not in (592, 516)):
                return None
            return fix_cast(k, p, v)
        fix_part.declared = fix_cast.declared
        emit_template(addr, st, 'darius_w_cast', ids, 0, fix_part)
        if part == 'cast':
            st.w_armed = True
            return
        st.w_armed = False
        ids_hit = {0x4000001e: hero, 0x400006e1: target}
        dmg, ad, armor = hit_damage(target, 1.4)   # W: effect 4 = 1.4 x AD at rank 1 (113.4 = 1.4 x 81 in the replay)
        print(f'W attack on {target:#x}: damage {dmg:.2f} (AD {ad:.1f}, armor {armor:.1f})', flush=True)

        def fix_hit(k, p, v):
            # no kill here: the minion's death, its gold and the cooldown refund belong to a kill
            if p['pid'] in (61, 453, 606) or (p['pid'] == 271 and k == len(w_hit_pids) - 1):
                return None
            if p['pid'] == 693 and v.get('+0x10') == hemo_hash:
                return None                         # the bleed's 693 / 326 come from hemo_hit when the hit lands
            if p['pid'] == 263:
                v['+0x14'] = f32(dmg)
                v['+0xa'], v['+0x1c'], v['+0x1d'] = '00', '04', '00'   # not a basic attack (+0x1d 1 only for those)
            if p['pid'] == 271:
                v['+0x14'] = v['+0x18'] = f32(w_cd)
            return v
        fix_hit.declared = {263: ['+0x14', '+0xa', '+0x1c', '+0x1d'], 271: ['+0x14', '+0x18']}
        apply_damage(addr, st, target, dmg, time.time() + 0.329, by_w=True, source='w')
        hemo_hit_at(addr, st, target, time.time() + 0.329)
        emit_template(addr, st, 'darius_w_hit_minion', ids_hit, time.time() + 0.329, fix_hit)
        if '--shots-on-cast' in args:
            for dt in (0.1, 0.25, 0.4, 0.6, 1.0, 1.6):
                cast_shots.append(time.time() + dt)

    # basic attacks (592 + 516 from the replay's own attack, data/exe133/templates/darius_aa*.json): the period and
    # windup from the character's data (spell_info.attack_times, checked on the replay), the hit on the next 1/30 s
    # server tick, damage = AD * 100 / (100 + target armor) (AD per level from the data; checked on the replay with
    # armor 0 only)
    import json as _json2
    hero_names = {}
    try:
        for e in _json2.load(open(os.path.join(HERE, '..', 'data', 'exe133', 's2c_79_heroes.json'), encoding='utf8')):
            hero_names[int(e['net_id'], 16) if isinstance(e['net_id'], str) else e['net_id']] = e['champion']
    except Exception as ex:
        print('no hero names:', ex, flush=True)

    if hero is not None:
        hero_names[hero] = hero_champion
    # teams: the replay's 79 (+ --set79 changes, e.g. 5.team_order=0 to make a test enemy)
    hero_teams = {}
    try:
        import create_hero as _CHt
        for h_ in _CHt.load_heroes():
            hero_teams[h_['net_id']] = h_['team_order']
        for item in (args[args.index('--set79') + 1].split(';') if '--set79' in args else []):
            k_, v_ = item.split('=', 1)
            sl_, name_ = k_.split('.')
            if name_ == 'team_order':
                for h_ in _CHt.load_heroes():
                    if h_['slot'] == int(sl_):
                        hero_teams[h_['net_id']] = int(v_)
    except Exception as ex:
        print('no teams:', ex, flush=True)

    # lane minions (minions_table.py): id -> spawn / death time in the replay, kind, team; their health over time
    minions = {}
    minion_hp = {}
    try:
        import pickle as _pk
        for k_, v_ in _json2.load(open(os.path.join(HERE, '..', 'data', 'exe133', 'minions.json'))).items():
            minions[int(k_)] = v_
        minion_hp = _pk.load(open(os.path.join(HERE, '..', 'data', 'exe133', 'minion_hp.pkl'), 'rb'))
    except OSError as ex:
        print('no minion table:', ex, flush=True)
    MINION_GOLD = {'melee': 21.0, 'caster': 14.0, 'cannon': 57.0}   # replay 453: 21 / 14; SR_LevelScript: 57 cannon

    def replay_value(track, t):
        import bisect
        if not track:
            return None
        i = bisect.bisect_right([x[0] for x in track], t) - 1
        return track[i][1] if i >= 0 else track[0][1]

    def char_level_value(base, per, lvl):
        return base + per * (lvl - 1) * (0.7025 + 0.0175 * (lvl - 1))

    # the hero's position, as the server keeps it: it starts at its spawn point (79) and walks the paths the server
    # sends (552) at its move speed (baseMoveSpeed; the replay's own 552 for Darius carry 340). Other units' positions
    # come from the replay's movement packets (positions.py).
    def hero_pos(st):
        import positions as POs
        if getattr(st, 'path', None):
            return POs.walk(st.path, st.move_speed, time.time() - st.path_t)
        return getattr(st, 'pos', (554.0, 581.0))

    def send_path(addr, st, pts, why):
        """552 for the hero: pts in world units, the first one being where it stands; one point = stop there"""
        import spell_info as SI
        import waypoints as Wp
        st.move_speed = float(SI.char_record(hero_names.get(hero, 'Darius'))['baseMoveSpeed'])
        cells = [(int(round((x - Wp.CENTER[0]) / Wp.CELL)), int(round((z - Wp.CENTER[1]) / Wp.CELL))) for x, z in pts]
        entry = LP.waypoint_entry(hero, cells, st.move_speed)
        send_message(addr, st, 2, struct.pack('<HI', 552, 0) + LP.encode_552(entry), f'552 hero {why}: {[(round(x), round(z)) for x, z in pts]}')
        st.pos = pts[0]
        if len(pts) > 1:
            face(st, pts[0], pts[1])
        st.path = list(pts) if len(pts) > 1 else None
        st.path_t = time.time()

    def unit_radius(name):
        import spell_info as SI
        if not name:
            return 65.0
        return float(SI.char_record(name).get('overrideGameplayCollisionRadius', 65.0))

    def chase(addr, st, game_now):
        """the attack order: walk to the target until it is in range (attackRange + both gameplay radii; the replay's
        Darius attacks champions from at most 297 = under 175 + 80 + 65), then stop (552 with one point, as Riot's
        server does on 92 of Darius's 286 attacks) and attack"""
        import math
        import positions as POs
        import spell_info as SI
        aa = st.aa
        me = hero_pos(st)
        size = unit_radius(hero_names.get(aa['target']))
        if world_[0] is not None:
            # every unit of the match is our world's (world.py: lane minions, turrets, monsters, the other champions):
            # where it is now; the order is over once it is gone (dead, or a turret still protected)
            w_ = world_[0]
            tp = w_.place(aa['target'], game_now) if w_.knows(aa['target']) else None
            tu_ = w_.turrets.get(aa['target'])
            if tp is None or (tu_ is not None and not tu_.open):
                st.aa = None
                return False
            size = w_.body(aa['target'])
        else:
            tp = POs.at(aa['target'], game_now)
        if tp is None:
            return True
        rng = float(SI.char_record(hero_names.get(hero, 'Darius'))['attackRange']) + unit_radius(hero_names.get(hero)) + size
        d = math.hypot(tp[0] - me[0], tp[1] - me[1])
        aa['me'], aa['tp'] = me, tp
        if d <= rng:
            if getattr(st, 'path', None):
                send_path(addr, st, [me], 'stops in range')
            return True
        last = aa.get('chase_to')
        # a new path when the target moved, at most every 0.25 s (Riot's server: 0.1..0.5 s between Darius's paths
        # before an attack in the replay, player clicks included -- approximation)
        if not getattr(st, 'path', None) or last is None or (math.hypot(tp[0] - last[0], tp[1] - last[1]) > 25 and
                                                            time.time() - st.path_t >= 0.25):
            aa['chase_to'] = tp
            send_path(addr, st, [me, tp], f'walks to the target ({d:.0f} away, range {rng:.0f})')
        return False

    # health of the units our hero damages: from the data (baseHP + hpPerLevel growth, level 1), lowered on every hit
    # and sent as our own 595 (mHP, group 5) at the hit's time; the replay's group 5 of those units is dropped
    unit_hp = {}
    # --test-hp "40000022=200": a test knob, the unit starts with that much health (to reach a kill quickly)
    test_hp = {int(a, 16): float(b) for a, b in (x.split('=') for x in args[args.index('--test-hp') + 1].split(';'))}         if '--test-hp' in args else {}
    hp_counter = [1000000]
    WORLD_NET = 0x40001000           # net ids from here up are units of our own world (world.NET_BASE)

    def max_hp(target):
        import spell_info as SI
        name = hero_names.get(target)
        if not name and target in minions:
            game_now_ = stream_t0[1] + (time.time() - stream_t0[0]) * speed if stream_t0 else 0.0
            return replay_value(minion_hp.get(target), game_now_)
        if not name:
            return None
        r = SI.char_record(name)
        return char_level_value(float(r['baseHP']), float(r['hpPerLevel']), 1)

    def apply_damage(addr, st, target, dmg, at, by_w=False, source='attack0x40'):
        """the damage lands at `at`: the health is lowered then (in the order the hits land) and sent as 595"""
        if target in dead_units:
            return
        scheduled.append((at, addr, None, lambda: damage_now(addr, st, target, dmg, at, by_w, source), 'damage'))

    def damage_now(addr, st, target, dmg, at, by_w, source='attack0x40'):
        import repl_codec as RC
        if target in dead_units:
            return None
        if world_[0] is not None:
            # a unit of our own world (lane minion, turret, monster, another champion): its health, its death and
            # what follows are the world's business; gold and experience for a kill come back as events (world_events)
            w_ = world_[0]
            if not w_.knows(target):
                return None
            game_at = stream_t0[1] + (at - stream_t0[0]) * speed if stream_t0 else 0.0
            kind = 0
            is_basic = True
            if source.startswith('spell:'):
                _, sl_, sp_name_, k_ = source.split(':')
                kind = int(k_)
                is_basic = False
            for ch_, data_, what_ in w_.hit(game_at, hero, target, dmg, show=True, kind=kind, is_basic=is_basic):
                send_message(addr, st, ch_, data_, what_, quiet=False)
            if w_.place(target, game_at) is None:
                print(f'{target:#x} killed by the hero', flush=True)
                if getattr(st, 'aa', None) and st.aa.get('target') == target:
                    st.aa = None
            return 0.0
        if target not in unit_hp:
            m = test_hp.get(target) or max_hp(target)
            if m is None:
                return None
            unit_hp[target] = m
        unit_hp[target] = max(0.0, unit_hp[target] - dmg)
        hp_counter[0] += 1
        game_at = stream_t0[1] + (at - stream_t0[0]) * speed if stream_t0 else 0.0
        if target in minions:
            body595 = RC.packet([(target, {'mHP': unit_hp[target]}, 'lane_minion')], game_at, hp_counter[0])
        else:
            body595 = RC.packet([(target, {'mHP': unit_hp[target]}, RC.HERO)], game_at, hp_counter[0])
        send_message(addr, st, 2, struct.pack('<HI', 595, 0) + body595, f'our 595: {target:#x} health {unit_hp[target]:.1f}')
        if unit_hp[target] <= 0 and target not in dead_units:
            on_kill(addr, st, target, at, by_w, source)
        return unit_hp[target]

    dead_units = set()

    def give_gold(addr, st, amount):
        """the hero's gold (595 group 0, which is ours: the replay's is dropped) goes up; starts at the replay's 500"""
        import repl_codec as RC
        st.gold = getattr(st, 'gold', 500.0) + amount
        st.gold_total = getattr(st, 'gold_total', 500.0) + amount
        hp_counter[0] += 1
        game_now_ = stream_t0[1] + (time.time() - stream_t0[0]) * speed if stream_t0 else 0.0
        send_message(addr, st, 2, struct.pack('<HI', 595, 0) + RC.packet([(hero, {'mGold': st.gold, 'mGoldTotal': st.gold_total}, RC.HERO)], game_now_, hp_counter[0]),
                     f'our 595: hero gold {st.gold:.0f}')

    # ---- our hero as a target of our world (world.py: turrets, minions), its health, death, return and levels ----
    FOUNTAIN = (394.77, 461.57)                 # the blue fountain (the map's own point)
    # experience a level needs in all (the usual table: 280 for level 2, +100 more each level)
    XP_LEVELS = [280, 660, 1140, 1720, 2400, 3180, 4060, 5040, 6120, 7300, 8580, 9960, 11440, 13020, 14700, 16480, 18360]

    def game_time():
        return stream_t0[1] + (time.time() - stream_t0[0]) * speed if stream_t0 else 0.0

    def hero_health(addr, st, why):
        """our hero's health as it is now (595 mHP)"""
        import repl_codec as RC
        hp = max(0.0, own_hero_state.get('max_hp', 600.0) - own_hero_state.get('lost', 0.0))
        hp_counter[0] += 1
        send_message(addr, st, 2, struct.pack('<HI', 595, 0) + RC.packet([(hero, {'mHP': hp}, RC.HERO)], game_time(), hp_counter[0]),
                     f'our 595: hero health {hp:.0f} ({why})', quiet=True)
        return hp

    def hero_takes(addr, st, source, raw):
        """a turret's or a minion's attack lands on our hero: physical damage through its armor, the number (263),
        the new health and, at zero, its death"""
        if getattr(st, 'dead', False) or world_[0] is None:
            return
        if getattr(st, 'recalling', None):
            st.recalling = None
            print(f'Recall cancelled by damage from {source:#x}!', flush=True)
        dmg = raw * 100.0 / (100.0 + own_hero_state.get('armor', 30.0))
        own_hero_state['lost'] = own_hero_state.get('lost', 0.0) + dmg
        ch_, data_, what_ = world_[0].damage_number(hero, source, dmg)
        send_message(addr, st, ch_, data_, what_, quiet=True)
        if hero_health(addr, st, f'hit by {source:#x} for {dmg:.0f}') <= 0:
            hero_dies(addr, st, source)

    def hero_dies(addr, st, killer):
        """our hero's death as the replay's (Jax at 308.379 s): target cleared (740), 568, the death time (780, 417
        with the killer), 440; it stops where it is (552 with one point) and comes back at the fountain later"""
        w_ = world_[0]
        level = own_hero_state['progress'][0]
        dt = death_time(level, game_time())
        st.dead, st.alive_at = True, time.time() + dt / speed
        st.aa = None
        f32 = struct.pack('<f', dt).hex()
        me = hero_pos(st)
        for ch_, data_, what_ in (
                w_.real['attack_740'][1].as_sent(hero, '740 hero target cleared'),
                w_.real['herodeath_568'][0].as_sent(hero, '568 (hero death)'),
                w_.real['herodeath_780'][0].packet(hero, lambda v: v.update({'+0xc': f32}), f'780 death time {dt:.1f}'),
                w_.real['herodeath_417'][0].packet(hero, lambda v: v.update({'+0xc': f32, '+0x2c': struct.pack('<I', killer).hex()}),
                                                   f'417 hero dies (killer {killer:#x})'),
                w_.real['herodeath_440'][0].packet(hero, lambda v: v.update({'+0xc': struct.pack('<I', hero).hex()}), '440 (hero death)')):
            send_message(addr, st, ch_, data_, what_)
        send_path(addr, st, [me], 'dies')
        print(f'hero killed by {killer:#x}: back in {dt:.1f} s', flush=True)

    def hero_returns(addr, st):
        """the hero alive again at its fountain (the replay's Jax at 322.393 s: 128 with the place and the mana, a
        552 with that one point, full health)"""
        st.dead = False
        own_hero_state['lost'] = 0.0
        mana = float(own_hero_state.get('max_par', 0.0))
        ch_, data_, what_ = world_[0].real['respawn_128'][0].packet(
            hero, lambda v: v.update({'+0xc': struct.pack('<ff', *FOUNTAIN).hex(), '+0x14': struct.pack('<f', mana).hex()}),
            '128 hero alive again')
        send_message(addr, st, ch_, data_, what_)
        st.pos, st.path = FOUNTAIN, None
        send_path(addr, st, [FOUNTAIN], 'is back at the fountain')
        own_hero_state['dirty'] = True
        print('hero alive again at the fountain', flush=True)

    def hero_regen(addr, st, dt):
        """health coming back: the champion's own regeneration, and 8.5 % of its health a second at the fountain"""
        import math
        lost = own_hero_state.get('lost', 0.0)
        if lost <= 0 or getattr(st, 'dead', False):
            return
        gain = own_hero_state.get('regen', 1.5) * dt
        if math.dist(hero_pos(st), FOUNTAIN) < 1000.0:
            gain += 0.085 * own_hero_state.get('max_hp', 600.0) * dt
        own_hero_state['lost'] = max(0.0, lost - gain)
        if int(lost) != int(own_hero_state['lost']):
            hero_health(addr, st, 'regeneration')

    def hero_xp(addr, st, amount):
        """experience for our hero; a new level = 606 (level, one more skill point) and the level's stats (595)"""
        level, exp = own_hero_state['progress']
        exp += amount
        while level < 18 and exp >= XP_LEVELS[level - 1]:
            level += 1
            b = LP.BODIES.get(f'606:{level},1')
            if b:
                send_message(addr, st, 1, struct.pack('<HI', 606, hero) + bytes.fromhex(b[0]), f'606 hero level {level}')
            print(f'hero reaches level {level}', flush=True)
        own_hero_state['progress'] = (level, exp)
        own_hero_state['dirty'] = True

    def world_events(addr, st):
        """what our world did to the champions since the last tick"""
        w_ = world_[0]
        events, w_.events = w_.events, []
        for ev in events:
            if ev[0] == 'hero_hit' and ev[3] == hero:
                hero_takes(addr, st, ev[2], ev[4])
            elif ev[0] == 'xp' and ev[2] == hero:
                xp_val = ev[3]
                try:
                    import pkt_schema as PSw
                    sc46 = schema_cache.get(46) or schema_cache.setdefault(46, PSw.Schema.load(46))
                    v46 = {'+0xc': struct.pack('<f', float(xp_val)).hex(),
                           '+0x10': struct.pack('<I', hero).hex()}
                    send_message(addr, st, 1, struct.pack('<HI', 46, hero) + sc46.encode(v46),
                                 f'46 give xp +{xp_val:.1f}')
                except Exception as ex:
                    print(f'packet 46 error: {ex}', flush=True)
                hero_xp(addr, st, xp_val)
            elif ev[0] == 'gold' and ev[2] == hero:
                gold_val = ev[3]
                target_minion = ev[4] if len(ev) > 4 else 0
                try:
                    import pkt_schema as PSw
                    sc453 = schema_cache.get(453) or schema_cache.setdefault(453, PSw.Schema.load(453))
                    v453 = {'+0xc': struct.pack('<f', float(gold_val)).hex(),
                            '+0x10': struct.pack('<I', hero).hex(),
                            '+0x14': '00',
                            '+0x18': struct.pack('<I', target_minion).hex() if target_minion else '00000000'}
                    send_message(addr, st, 1, struct.pack('<HI', 453, hero) + sc453.encode(v453),
                                 f'453 last-hit gold +{gold_val:.0f} from {target_minion:#x}')
                except Exception as ex:
                    print(f'packet 453 error: {ex}', flush=True)
                give_gold(addr, st, gold_val)
            elif ev[0] == 'turret_dead':
                print(f'turret {ev[2]:#x} ({ev[3]}) fell, killer {ev[4]:#x}', flush=True)
            elif ev[0] == 'inhibitor_dead':
                print(f'inhibitor {ev[2]:#x} ({ev[3]} {ev[4]}) fell, killer {ev[5]:#x}', flush=True)
            elif ev[0] == 'inhibitor_respawn':
                print(f'inhibitor {ev[2]:#x} ({ev[3]} {ev[4]}) respawned!', flush=True)
            elif ev[0] == 'game_over':
                print(f'THE MATCH IS OVER: the {ev[2]} nexus fell (killer {ev[3]:#x})', flush=True)
            elif ev[0] == 'fountain_heal' and ev[2] == hero:
                max_h = max_hp(hero) or 600.0
                curr_h = unit_hp.get(hero, max_h)
                if curr_h < max_h:
                    unit_hp[hero] = min(max_h, curr_h + 0.10 * max_h)
                    hp_counter[0] += 1
                    import repl_codec as RC
                    body_ = RC.packet([(hero, {'mHP': unit_hp[hero]}, RC.HERO)], game_time(), hp_counter[0])
                    send_message(addr, st, 2, struct.pack('<HI', 595, 0) + body_, f'595 fountain heal {unit_hp[hero]:.0f}/{max_h:.0f}', quiet=True)
            elif ev[0] == 'champion_dead':
                print(f'champion {hero_names.get(ev[2], hex(ev[2]))} ({ev[3]}) died, killer {ev[4]:#x}', flush=True)

    # what the replay says about a champion's death (every one of its 53, data/exe133/codec/417.all.jsonl ...):
    # - the death time (417 / 780 +0xc) = DeathTimes.mTimeDeadPerLevel[level] x (1 + increase), the increase growing
    #   continuously by mPercentIncrease per 30 s from each mScalingPoints start (map11.bin {9de5b46c}): 51 / 51 exact
    # - the killing source (417 +0x10): attack {08, name, 7dcf0000, slot 0x40 / 0x41}, W {18, ONHAttack, 7dcf0000, 1},
    #   bleed {20, -, a8c90000, 0} (Darius's kills in the replay)
    # - gold (453 to the killer): 400 for the game's first kill (68.9 s), 300 after (less for victims on a death
    #   streak -- not modelled); 101 = the killer's multikill count (2 for a double kill)
    # - 215 OnChampionKill: +0xc victim / +0x10 killer = a per-character hash (measured, function unknown), +0x14 the
    #   killer's player slot, +0x18 its team (0x64 = 100, 0xc8 = 200)
    DEATH_LEVELS = [6, 8, 10, 12, 14, 16, 21, 27.5, 30, 32.5, 35, 37.5, 40, 42.5, 45, 47.5, 50, 52.5]
    DEATH_POINTS = [(900, 0.00425), (1800, 0.003), (2700, 0.0145)]
    CHAR_HASH = {'Darius': '326a1852', 'Alistar': '7041007d', 'Jax': 'c1839334', 'LeeSin': '8cee34bb',
                 'Talon': 'fecacd9d', 'Blitzcrank': '2a84929d', 'Azir': '229691dd', 'Nidalee': 'b436a47d'}
    KILL_SOURCE = {'attack0x40': ('08000000', 'DariusBasicAttack', '7dcf0000', '40000000'),
                   'attack0x41': ('08000000', 'DariusBasicAttack2', '7dcf0000', '41000000'),
                   'w': ('18000000', 'DariusNoxianTacticsONHAttack', '7dcf0000', '01000000'),
                   'bleed': ('20000000', '', 'a8c90000', '00000000')}
    kills_done = []
    multikill = {}

    def death_time(level, game_t):
        inc = 0.0
        for k, (st_, pc) in enumerate(DEATH_POINTS):
            end = DEATH_POINTS[k + 1][0] if k + 1 < len(DEATH_POINTS) else 1e9
            if game_t > st_:
                inc += (min(game_t, end) - st_) / 30 * pc
        return DEATH_LEVELS[max(1, min(level, 18)) - 1] * (1 + min(inc, 0.5))

    def kill_champion(addr, st, target, at, source):
        import spell_info as SI
        game_t = stream_t0[1] + (at - stream_t0[0]) * speed if stream_t0 else 0.0
        level = 1                                    # level of the victim: our test units are at level 1
        dt = death_time(level, game_t)
        first = not kills_done
        kills_done.append(at)
        mk = multikill.get(hero)
        mk = (mk[0] + 1, at) if mk and at - mk[1] <= 10.0 else (1, at)   # multikill window: 10 s (not checked)
        multikill[hero] = mk
        gold = 400.0 if first else 300.0
        # XP to the killer (46): mExperienceGrantedForKillPerLevel[victim level] (map11 {c6f6a84c}); exact on the
        # replay's solo kills between equal levels; level differences and shared kills change it (not modelled)
        XP_FOR_KILL = [42, 114, 186, 258, 330, 402, 434, 500, 515, 590, 640, 690, 740, 790, 840, 890, 940, 990]
        xp = XP_FOR_KILL[level - 1]
        src = KILL_SOURCE.get(source, KILL_SOURCE['attack0x40'])
        dmg_type = '00'
        if source.startswith('spell:'):
            _, sl_, name_, kind_ = source.split(':')
            src = ('11000000', name_, '2ac90000', f'{int(sl_):02x}000000')
            dmg_type = f'{int(kind_):02x}'
        f32 = lambda x: struct.pack('<f', x).hex()
        drop = {190, 750}                            # experiment: the recap is the victim's, the 750 blobs are unknown
        state = {'n453': 0}

        def fix(k, p, v):
            pid = p['pid']
            if pid in drop:
                return None
            if pid in (417, 780):
                v['+0xc'] = f32(dt)
            if pid == 417:
                c = v['+0x10']
                c['+0x4'] = src[0]
                c['+0x8'] = struct.pack('<I', SI.elf(src[1])).hex() if src[1] else '00000000'
                c['+0xc'] = src[2]
                c['+0x10'] = src[3]
                c['+0x14'] = dmg_type                # 0 physical (Darius's attacks, W, bleed), 1 magic
            if pid == 453:
                state['n453'] += 1
                if v['+0xc'] != '00000000':
                    v['+0xc'] = f32(gold)
            if pid == 101:
                v['+0xa'] = f'{mk[0]:02x}'
            if pid == 46:
                v['+0xc'] = f32(xp)
            if pid == 568:
                v['+0xa'], v['+0xb'], v['+0xc'], v['+0x10'] = '01', '00', f32(-1.0), f32(-1.0)   # the victim's, 5 / 6
            if pid == 740:
                v['+0xc'] = '00000000'                 # the victim's target cleared (8 / 8)
            if pid == 215:
                v['+0xc'] = CHAR_HASH.get(hero_names.get(target), v['+0xc'])
                v['+0x10'] = CHAR_HASH.get(hero_names.get(hero), v['+0x10'])
                v['+0x14'] = f'{slot or 1:02x}'
                v['+0x18'] = '64000000'               # team 100 (our hero's team in 574)
            return v
        fix.declared = {417: ['+0xc', '+0x10+0x4', '+0x10+0x8', '+0x10+0xc', '+0x10+0x10', '+0x10+0x14'], 780: ['+0xc'],
                        453: ['+0xc'], 101: ['+0xa'], 215: ['+0xc', '+0x10', '+0x14', '+0x18'], 46: ['+0xc'],
                        568: ['+0xa', '+0xb', '+0xc', '+0x10'], 740: ['+0xc']}
        emit_template(addr, st, 'darius_kill_champion', {0x4000001e: hero, 0x40000023: target}, at + 0.001, fix)
        give_gold(addr, st, gold)
        print(f'champion kill: death time {dt:.2f} s, gold {gold:.0f}, source {source}, multikill {mk[0]}', flush=True)

    def kill_minion(addr, st, target, at, source):
        """a lane minion's death as the replay's (darius_aa_hit: 61 with the killer and the killing source, 453 gold to
        the killer); gold by kind (21 melee / 14 caster / 57 cannon)"""
        import spell_info as SI
        m = minions[target]
        gold = MINION_GOLD.get(m['kind'], 21.0)
        src = KILL_SOURCE.get(source, KILL_SOURCE['attack0x40'])
        dmg_type = '00'
        if source.startswith('spell:'):
            _, sl_, name_, kind_ = source.split(':')
            src = ('11000000', name_, '2ac90000', f'{int(sl_):02x}000000')
            dmg_type = f'{int(kind_):02x}'

        def fix(k, p, v):
            if p['pid'] == 61:
                c = v['+0x10']
                c['+0x4'] = src[0]
                c['+0x8'] = struct.pack('<I', SI.elf(src[1])).hex() if src[1] else '00000000'
                c['+0xc'], c['+0x10'], c['+0x14'] = src[2], src[3], dmg_type
                return v
            if p['pid'] == 453:
                v['+0xc'] = struct.pack('<f', gold).hex()
                return v
            return None
        fix.declared = {61: ['+0x10+0x4', '+0x10+0x8', '+0x10+0xc', '+0x10+0x10', '+0x10+0x14'], 453: ['+0xc']}
        emit_template(addr, st, 'darius_aa_hit', {0x4000001e: hero, 0x4000026b: target}, at + 0.001, fix)
        give_gold(addr, st, gold)
        print(f'minion kill {target:#x} ({m["kind"]}): gold {gold:.0f}, source {source}', flush=True)

    def on_kill(addr, st, target, at, by_w=False, source='attack'):
        """a champion's death as Riot's server sends it (the replay's kill of Jax by Darius at 308.379: 453 300 gold,
        215 OnChampionKill, 101, 46, 190 death recap, 750 events, 417 / 780 / 440 / 568 / 740 on the victim), our ids;
        W's kill also refunds half its cooldown (271, as at 167.196). The replay's packets for the dead unit stop."""
        print(f'{target:#x} killed by {hero:#x}{" (W)" if by_w else ""}', flush=True)
        if hero_names.get(target):
            kill_champion(addr, st, target, at, source)
        elif target in minions:
            kill_minion(addr, st, target, at, source)
        if by_w:
            def only_refund(k, p, v):
                if not (p['pid'] == 271 and k == len(w_hit_pids) - 1):
                    return None
                # W's kill refunds 50 % of its cooldown (effect 3 = 50; 2.5 of 5 in the replay at 167.196)
                v['+0x14'] = struct.pack('<f', cooldown('DariusNoxianTacticsONH', max(st.skills.get(1, 1), 1)) * 0.5).hex()
                return v
            only_refund.declared = {271: ['+0x14']}
            emit_template(addr, st, 'darius_w_hit_minion', {0x4000001e: hero, 0x400006e1: target}, at + 0.002, only_refund)
        dead_units.add(target)
        if '--shots-on-cast' in args:
            for dt in (0.1, 0.6, 1.5, 3.0):
                cast_shots.append(at + dt)
        if getattr(st, 'aa', None) and st.aa.get('target') == target:
            st.aa = None

    # Darius's passive (DariusHemoMarker): every physical hit adds a stack (MaxStacks 5) and renews the bleed
    # (693 DariusHemo 5.1 s at the first hit, then 326 with the new stack count, as in the replay); the bleed ticks
    # every 1.322 s (all of Darius's 244 replay ticks; the data's SecondsPerTick says 1.26), each tick = stacks x
    # (13..30 by level + 0.3 x bonus AD) / (BleedDuration 5 / SecondsPerTick 1.26), through armor -- the formula is
    # the data's; the replay's ticks come out higher (items / armor shred there), so it is not verified yet
    hemo = {}
    import spell_info as _SIh
    hemo_hash = struct.pack('<I', _SIh.elf('DariusHemo')).hex()

    def hemo_hit_at(addr, st, target, at):
        scheduled.append((at, addr, None, lambda: hemo_hit(addr, st, target, at), 'bleed'))

    def hemo_hit(addr, st, target, at):
        if target in dead_units:
            return False
        h = hemo.get(target)
        if h and at < h['expires']:
            h['stacks'] = min(5, h['stacks'] + 1)
            h['expires'] = at + 5.1
            def only326(k, p, v):
                if p['pid'] != 326:
                    return None
                v['+0x14'] = f'{h["stacks"]:02x}'
                v['+0x15'] = f'{h["slot"]:02x}'
                return v
            emit_template(addr, st, 'darius_hemo_refresh', {0x4000001e: hero, 0x40000023: target}, at, only326)
            return False
        hemo[target] = {'stacks': 1, 'expires': at + 5.1, 'next_tick': at + 1.322, 'slot': 0, 'addr': addr, 'st': st}
        def only693(k, p, v):     # the first stack: the attack hit's own 693 DariusHemo
            return v if p['pid'] == 693 and v.get('+0x10') == hemo_hash else None
        emit_template(addr, st, 'darius_aa_hit', {0x4000001e: hero, 0x4000026b: target}, at, only693)
        return True

    def hemo_ticks():
        import math
        now = time.time()
        for target, h in list(hemo.items()):
            if target in dead_units:
                del hemo[target]
                continue
            addr, st = h['addr'], h['st']
            while h['next_tick'] <= min(now, h['expires']):
                at = h['next_tick']
                h['next_tick'] += 1.322
                per = 13.0 / (5 / 1.26)               # level 1, no bonus AD
                tchamp = hero_names.get(target)
                armor = 0.0
                if tchamp:
                    import spell_info as SI
                    tr = SI.char_record(tchamp)
                    armor = char_level_value(float(tr['baseArmor']), float(tr['armorPerLevel']), 1)
                dmg = h['stacks'] * per * 100 / (100 + armor)
                def only263(k, p, v, dmg=dmg):
                    if p['pid'] != 263:
                        return None
                    v['+0x14'] = struct.pack('<f', dmg).hex()
                    v['+0xa'], v['+0x1c'], v['+0x1d'] = '06', '04', '00'   # +0xa 6 = damage over time (replay)
                    return v
                only263.declared = {263: ['+0x14', '+0xa', '+0x1c', '+0x1d']}
                emit_template(addr, st, 'darius_hemo_tick', {0x4000001e: hero, 0x40000023: target}, at, only263)
                print(f'bleed tick on {target:#x}: {h["stacks"]} stacks, {dmg:.2f}', flush=True)
                apply_damage(addr, st, target, dmg, at, source='bleed')
            if now >= h['expires']:
                def only522(k, p, v):
                    return v if p['pid'] == 522 and p['who'] == 'target' and v.get('+0x10') == hemo_hash else None
                emit_template(addr, st, 'darius_aa_hit', {0x4000001e: hero, 0x4000026b: target}, h['expires'], only522)
                print(f'bleed off {target:#x}', flush=True)
                del hemo[target]

    def hit_damage(target, mult=1.0):
        """physical damage of the hero's attack on a target: mult x AD x 100 / (100 + armor), level 1, from the data"""
        import spell_info as SI
        rec = SI.char_record(hero_names.get(hero, 'Darius'))
        ad = char_level_value(float(rec['baseDamage']), float(rec['damagePerLevel']), 1)
        tchamp = hero_names.get(target)
        armor = 0.0
        if tchamp:
            tr = SI.char_record(tchamp)
            armor = char_level_value(float(tr['baseArmor']), float(tr['armorPerLevel']), 1)
        return mult * ad * 100 / (100 + armor), ad, armor

    def fix592(v, st, me_xyz, tg_pos, game_t, windup, slot=None):
        """the varying fields of an attack (592), as for Darius's: counter, slot, positions, timing, ids"""
        f32 = lambda x: struct.pack('<f', x).hex()
        a = v['+0xc']
        st.cast_count = getattr(st, 'cast_count', 0x100) + 1
        a['+0x4'] = struct.pack('<I', st.cast_count).hex()
        if slot is not None:
            a['+0xc'] = f'{slot:02x}'
        a['+0x1c'] = '80'
        a['+0x24'] = tg_pos
        a['+0x20'] = struct.pack('<I', 0x40100001 + 4 * st.cast_count).hex()
        if a.get('+0x10'):
            c = a['+0x10'][0]
            c['+0x78'] = f32(game_t)
            c['+0x8c']['+0x10'] = f32(game_t + windup)
            c['+0x80'] = struct.pack('<I', st.cast_count).hex()
            c['+0x4c'] = tg_pos
            c['+0x60'] = struct.pack('<3f', *me_xyz).hex()
            c['+0x8c']['+0x1c'] = next_instance()
            c['+0x1c'] = c['+0xc4'] = a['+0x20']
        v['+0x3c'] = struct.pack('<ff', me_xyz[0], me_xyz[2]).hex()
        return v

    def auto_attack_tick(addr, st, aa, champ, period, windup, armed):
        """an attack from the champion's own replay templates (auto/<champ>/attack_*.json); an armed attack (a spell
        with 118, e.g. PowerFist) uses its attack spell, its damage comes from the spell's own calculation, and the
        release tick (auto/<champ>/<spell>__release.json) follows at the hit"""
        import math
        import random
        import spell_calc as SCc
        import spell_info as SI
        f32 = lambda x: struct.pack('<f', x).hex()
        now = time.time()
        game_t = stream_t0[1] + (now - stream_t0[0]) * speed if stream_t0 else 0.0
        me2, tp2 = aa.get('me', (554.0, 581.0)), aa.get('tp', (704.0, 631.0))
        face(st, me2, tp2)
        me_xyz = (me2[0], 171.0, me2[1])
        tg_pos = struct.pack('<3f', tp2[0], 171.0, tp2[1]).hex()
        target = aa['target']
        mspeed = SI.basic_attack_missile_speed(champ)
        is_ranged = mspeed > 0
        dist = math.hypot(tp2[0] - me2[0], tp2[1] - me2[1])
        flight = (dist / mspeed) if (is_ranged and mspeed > 0) else 0.0
        hit_at = math.ceil((windup + flight) * 30 - 1e-6) / 30
        if armed:
            name = f'attack_{armed["atk_slot"]:02x}_{armed["attack"]}'
            if not os.path.exists(os.path.join(AUTO_DIR, champ, name + '.json')):
                name = next((f[:-5] for f in os.listdir(os.path.join(AUTO_DIR, champ))
                             if f.startswith(f'attack_{armed["atk_slot"]:02x}_')), 'attack_40')
            slot = None
        else:
            have = [x for x in ('40', '41', '42', '43') if os.path.exists(os.path.join(AUTO_DIR, champ, f'attack_{x}.json'))]
            name = f'attack_{random.choice(have)}'
            slot = None
        tpl = _json2.load(open(os.path.join(AUTO_DIR, champ, name + '.json')))

        def fix(k, p, v):
            if p['pid'] == 592:
                return fix592(v, st, me_xyz, tg_pos, game_t, windup, slot)
            if p['pid'] == 516:
                v['+0xc'] = tg_pos
            return v
        fix.declared = {592: ['+0xc+0x4', '+0xc+0x1c', '+0xc+0x24', '+0xc+0x20', '+0x3c'], 516: ['+0xc']}
        ids = {tpl['caster']: hero}
        tv = tpl['packets'][0]['values']['+0xc']['+0x8']
        ids[int.from_bytes(bytes.fromhex(tv), 'little')] = target
        emit_template(addr, st, f'auto/{champ}/{name}', ids, 0, fix)
        if is_ranged and mspeed > 0:
            attack_id = 0x40100001 + 4 * st.cast_count
            mid = struct.pack('<I', attack_id).hex()
            sc779 = PS2.Schema.load(779)
            pkt779 = struct.pack('<HI', 779, hero) + sc779.encode({'+0xc': mid})
            scheduled.append((now + windup, addr, 1, pkt779, f'779 {champ} attack missile'))
        # damage: an armed attack = the spell's damage calculation; a basic attack = AD; through armor / MR
        kind = 0
        if armed:
            rec = SI.char_record(champ)
            stats = SCc.Stats(ad=(char_level_value(float(rec['baseDamage']), float(rec['damagePerLevel']), 1), 0.0))
            dm = SE.damage(champ, armed['spell'], armed['rank'], 1, stats)
            raw, kind = (dm[0], dm[1]) if dm else (hit_damage(target)[1], 0)
            tr = SI.char_record(hero_names[target]) if hero_names.get(target) else {}
            resist = char_level_value(float(tr.get('baseArmor', 0)), float(tr.get('armorPerLevel', 0)), 1) if kind == 0 else \
                char_level_value(float(tr.get('baseSpellBlock', 30)), float(tr.get('spellBlockPerLevel', 0)), 1)
            dmg = raw * 100 / (100 + resist)
        else:
            dmg = hit_damage(target)[0]

        def only263(k, p, v):
            if p['pid'] != 263:
                return None
            v['+0x14'] = f32(dmg)
            v['+0x10'] = f'{kind:02x}'
            v['+0xa'], v['+0x1c'], v['+0x1d'] = '00', '04', '00' if armed else '01'
            return v
        only263.declared = {263: ['+0x14', '+0x10', '+0xa', '+0x1c', '+0x1d']}
        if world_[0] is None:
            emit_template(addr, st, 'darius_aa_hit', {0x4000001e: hero, 0x4000026b: target}, time.time() + hit_at, only263)
        src = f'spell:{armed["slot"]}:{armed["attack"]}:{kind}' if armed else f'attack0x40'
        apply_damage(addr, st, target, dmg, time.time() + hit_at, source=src)
        if champ == 'Darius':
            hemo_hit_at(addr, st, target, time.time() + hit_at)     # Darius's passive (its own replay-measured rules)
        if armed:
            rel = os.path.join(AUTO_DIR, champ, f'{armed["spell"]}__release.json')
            if os.path.exists(rel):
                rtpl = _json2.load(open(rel))

                def fix_rel(k, p, v):
                    if p['pid'] not in (522, 271, 118, 465, 71, 65):
                        return None                   # gold, kills, other units: not part of the release itself
                    if p['pid'] == 522:
                        sl = armed['buffs'].get(v.get('+0x10'))
                        if sl is None:
                            return None
                        v['+0xa'] = f'{sl:02x}'
                    if p['pid'] == 271 and v.get('+0x14', '00000000') != '00000000':
                        v['+0x14'] = v['+0x18'] = f32(cooldown(armed['spell'], armed['rank']))
                    return v
                fix_rel.declared = {522: ['+0xa'], 271: ['+0x14', '+0x18']}
                emit_template(addr, st, f'auto/{champ}/{armed["spell"]}__release', {rtpl['caster']: hero},
                              time.time() + hit_at, fix_rel)
            st.armed = None
        print(f'auto attack {name} on {target:#x}: damage {dmg:.1f} ({"magic" if kind else "physical"}), hit at +{hit_at:.3f}',
              flush=True)
        aa['next'] = now + period

    def attack_tick(addr, st):
        import math
        import random
        import spell_info as SI
        aa = st.aa
        champ = hero_names.get(hero, 'Darius')
        period, windup = SI.attack_times(champ)
        if getattr(st, 'w_armed', False):
            darius_w(addr, st, aa['target'], 'attack')
            aa['next'] = time.time() + period
            return
        armed = getattr(st, 'armed', None)
        if armed is not None or os.path.exists(os.path.join(AUTO_DIR, champ, 'attack_40.json')):
            auto_attack_tick(addr, st, aa, champ, period, windup, armed)
            return
        rec = SI.char_record(champ)
        attack_range = float(rec.get('attackRange', 125.0))
        mspeed = SI.basic_attack_missile_speed(champ)
        is_ranged = mspeed > 0 or attack_range > 300.0
        me2, tp2 = aa.get('me', (554.0, 581.0)), aa.get('tp', (704.0, 631.0))
        dist = math.hypot(tp2[0] - me2[0], tp2[1] - me2[1])
        flight = (dist / mspeed) if (is_ranged and mspeed > 0) else 0.0
        hit_at = math.ceil((windup + flight) * 30 - 1e-6) / 30
        f32 = lambda x: struct.pack('<f', x).hex()
        now = time.time()
        st.cast_count = getattr(st, 'cast_count', 0x100) + 2
        attack_id = 0x40100001 + 4 * st.cast_count
        slot = random.choice((0x40, 0x41))         # mAttackProbability 0.5 / extraAttacks 0.5
        me_xyz = (me2[0], 171.0, me2[1])
        tg_pos = struct.pack('<3f', tp2[0], 171.0, tp2[1]).hex()

        # Send champion basic attack animation via packet 65
        atk_anim = None
        for atk_k in (f'{champ}BasicAttack', f'{champ}BasicAttack2', f'{champ}CritAttack'):
            if atk_k in SI.spells(champ):
                atk_anim = SI.spells(champ)[atk_k].get('animation')
                if atk_anim:
                    break
        atk_anim = atk_anim or random.choice(['Attack1', 'Attack2'])
        if 65 in cast_tpl and '--no-anim' not in args:
            import copy as _cp
            sc65, v65 = cast_tpl[65]
            v65 = _cp.deepcopy(v65)
            v65['+0xc'] = {'text': atk_anim.encode().hex()}
            send_message(addr, st, cast_tpl['ch65'], struct.pack('<HI', 65, hero) + sc65.encode(v65),
                         f'our 65: {atk_anim} ({champ} basic attack)')

        def fix(k, p, v):
            if p['pid'] == 592:
                a = v['+0xc']
                a['+0x4'] = struct.pack('<I', st.cast_count).hex()
                a['+0xc'] = f'{slot:02x}'
                a['+0x1c'] = '80'
                a['+0x20'] = struct.pack('<I', attack_id).hex()
                a['+0x24'] = tg_pos
                v['+0x3c'] = struct.pack('<ff', me_xyz[0], me_xyz[2]).hex()
            if p['pid'] == 516:
                v['+0xc'] = tg_pos
            return v
        fix.declared = {592: ['+0xc+0x4', '+0xc+0x1c', '+0xc+0x24', '+0xc+0x20', '+0x3c'], 516: ['+0xc']}
        face(st, me2, tp2)
        emit_template(addr, st, 'darius_aa', {0x4000001e: hero, 0x4000026b: aa['target'], 0x400006f2: attack_id}, 0, fix)
        if is_ranged and mspeed > 0:
            mid = struct.pack('<I', attack_id).hex()
            sc779 = PS2.Schema.load(779)
            pkt779 = struct.pack('<HI', 779, hero) + sc779.encode({'+0xc': mid})
            scheduled.append((now + windup, addr, 1, pkt779, f'779 {champ} attack missile'))
        dmg, ad, armor = hit_damage(aa['target'])
        emp = getattr(st, 'next_attack_spell', None)
        if emp and now > emp['until']:
            emp = st.next_attack_spell = None
        if emp:
            # the attack a self-cast spell empowered: that spell's strike animation and its damage calculation
            # (through armor or magic resist as the formula says), then the spell is used up
            import copy
            import spell_calc as SCc_
            import spell_engine as SEng_
            st.next_attack_spell = None
            dm = SEng_.damage(champ, emp['spell'], emp['rank'], 1, SCc_.Stats(ad=(ad, 0.0)))
            if dm:
                tr = SI.char_record(hero_names[aa['target']]) if hero_names.get(aa['target']) else {}
                resist = char_level_value(float(tr.get('baseArmor', 0)), float(tr.get('armorPerLevel', 0)), 1) if dm[1] == 0 else \
                    char_level_value(float(tr.get('baseSpellBlock', 30)), float(tr.get('spellBlockPerLevel', 0)), 1) if tr else 0.0
                dmg = dm[0] * 100 / (100 + resist)
            if emp.get('animation') and 65 in cast_tpl:
                sc65, v65 = cast_tpl[65]
                v65 = copy.deepcopy(v65)
                v65['+0xc'] = {'text': emp['animation'].encode().hex()}
                send_message(addr, st, cast_tpl['ch65'], struct.pack('<HI', 65, hero) + sc65.encode(v65),
                             f'our 65: {emp["animation"]} (the empowered attack of {emp["spell"]})')
            print(f'empowered attack: {emp["spell"]} rank {emp["rank"]}, damage {dmg:.1f}', flush=True)

        def fix_hit(k, p, v):
            if p['pid'] in (453, 61, 522):
                return None
            if p['pid'] == 693:
                return None                         # the bleed's 693 / 326 come from hemo_hit when the hit lands
            if p['pid'] == 263:
                v['+0x14'] = f32(dmg)
                v['+0xa'], v['+0x1c'], v['+0x1d'] = '00', '04', '01'   # +0x1d 1 = a basic attack (replay)
            return v
        fix_hit.declared = {263: ['+0x14', '+0xa', '+0x1c', '+0x1d']}
        apply_damage(addr, st, aa['target'], dmg, time.time() + hit_at, source=f'attack{slot:#x}')
        if champ == 'Darius':
            hemo_hit_at(addr, st, aa['target'], time.time() + hit_at)
        if world_[0] is None:
            emit_template(addr, st, 'darius_aa_hit', {0x4000001e: hero, 0x4000026b: aa['target']}, time.time() + hit_at, fix_hit)
        print(f'attack {slot:#x} on {aa["target"]:#x}: period {period:.3f}, hit at +{hit_at:.3f}, damage {dmg:.2f} '
              f'(AD {ad:.1f}, armor {armor:.1f})', flush=True)
        if '--shots-on-cast' in args and not aa.get('shots'):
            aa['shots'] = True
            for dt in (0.1, 0.2, 0.35, 0.5, 1.0, 1.7, 2.2):
                cast_shots.append(now + dt)
        aa['next'] = now + period

    auto_skill = [int(x) for x in args[args.index('--auto-skill') + 1].split(',')] if '--auto-skill' in args else []
    auto_teleport = []
    if '--teleport' in args:
        for item in args[args.index('--teleport') + 1].split(';'):
            a_, b_ = item.split(':')
            x_, z_ = b_.split(',')
            auto_teleport.append([float(a_), float(x_), float(z_)])
    # --world-do "40:xp=300;60:raze": test aids for our world at those game seconds -- experience for the hero (a
    # level-up without waiting for minions), or the red mid turrets, nexus turrets and nexus falling to the hero one
    # after the other (a turret's fall and the end of the match without playing half an hour)
    world_do = []
    if '--world-do' in args:
        for item in args[args.index('--world-do') + 1].split(';'):
            a_, b_ = item.split(':')
            world_do.append([float(a_), b_])
    auto_attack = []
    if '--auto-attack' in args:
        for item in args[args.index('--auto-attack') + 1].split(';'):
            a_, b_ = item.split(':')
            auto_attack.append([float(a_), int(b_, 16)])

    import spell_templates as _STm
    w_hit_pids = [p['pid'] for p in _STm.load('darius_w_hit_minion')['packets']] if os.path.exists(
        os.path.join(_STm.OUT, 'darius_w_hit_minion.json')) else []
    auto_w = []
    if '--auto-w' in args:
        for item in args[args.index('--auto-w') + 1].split(';'):
            a_, b_ = item.split(':')
            auto_w.append([float(a_), int(b_, 16)])

    # --auto-cast "12:0;14:1:7800,7800": at those game seconds the server casts those slots itself (as if 16
    # came), towards that place when one is given
    auto_cast = []
    if '--auto-cast' in args:
        for item in args[args.index('--auto-cast') + 1].split(';'):
            p_ = item.split(':')
            auto_cast.append([float(p_[0]), int(p_[1])] + ([float(x_) for x_ in p_[2].split(',')] if len(p_) > 2 else [900.0, 900.0]))
    # --no-extra-missile: without the separate missile spell's own cast (see generic_cast)
    EXTRA_MISSILE = '--no-extra-missile' not in args

    # --auto-q <game second>: the server levels Q and casts it by itself at that game time (no input needed)
    auto_q = float(args[args.index('--auto-q') + 1]) if '--auto-q' in args else None
    auto_q_done = 0
    hero_values = {}
    if '--hero-set' in args:
        for item in args[args.index('--hero-set') + 1].split(';'):
            k_, v_ = item.split('=')
            hero_values[k_] = float(v_)
    next_hero_595 = 3.0
    hero_595_counter = int(args[args.index('--hero-counter') + 1]) if '--hero-counter' in args else 1000000
    if own_49 is None:
        hero_skin = 15
        for item in (args[args.index('--set79') + 1].split(';') if '--set79' in args else []):
            if item.startswith('1.skin='):
                hero_skin = int(item.split('=')[1])
    cast_shots = []
    world_ = [None]
    # --shots-at "15.5,16": frames at those server seconds (to see where things are before real input)
    if '--shots-at' in args:
        cast_shots.extend(t0 + float(x) for x in args[args.index('--shots-at') + 1].split(','))
    last_report = 0.0
    while True:
        for x in [c for c in cast_shots if c <= time.time()]:
            cast_shots.remove(x)
            with open('C:/Users/Sorin/Desktop/ProiectBattleArenaPc/game/sponge_capture.txt', 'w') as f:
                f.write('1')
            shot_count = globals().get('_shots', 0) + 1
            globals()['_shots'] = shot_count
            print(f'{time.time() - t0:8.3f}   capture asked (frame {shot_count})', flush=True)
        try:
            d, addr = s.recvfrom(4096)
        except socket.timeout:
            d = None
        except ConnectionResetError:
            d = None                      # the client closed its socket (the match ended): nothing to read
        t = time.time() - t0
        due = sorted([x for x in scheduled if x[0] <= time.time()], key=lambda x: x[0])
        for x in due:
            scheduled.remove(x)
            if callable(x[3]):          # an event computed when it happens (damage: the health at that moment)
                x[3]()
                continue
            send_message(x[1], peers[x[1]], x[2], x[3], x[4])
        if stream_t0 is not None:
            game_now = stream_t0[1] + (time.time() - stream_t0[0]) * speed
            for a, st in peers.items():
                if st.connected:
                    if not getattr(st, 'barrier_down', False) and game_now >= 15.0:
                        st.barrier_down = True
                        print(f'{t:8.3f} [Match Time 0:15] Fountain barrier dropped! Spawn platform opened.', flush=True)
                    pump_stream(a, st)
            game_now = stream_t0[1] + (time.time() - stream_t0[0]) * speed
            if start_only and own_hero_state.get('start_sent') and '--no-world' not in args:
                # our own Summoner's Rift (world.py): lane minion waves
                if world_[0] is None:
                    import world as WORLD
                    world_[0] = WORLD.World()
                    world_[0].counter = hp_counter      # one counter for every replication packet we send
                    if os.environ.get('WORLD_STATE_LOG'):
                        # a test aid: what the world holds, every second and at every death, with the wall clock
                        # (to set against what the client holds: ba_host.dll's census, tools/census.py)
                        world_[0].died = []
                        world_[0].state_log = open(os.environ['WORLD_STATE_LOG'], 'w')
                        world_[0].state_next = 0.0
                for a, st in peers.items():             # where our hero is: turrets and minions may attack it
                    if st.connected and hero is not None:
                        world_[0].set_hero(hero, 'blue', hero_pos(st), alive=not getattr(st, 'dead', False),
                                           radius=unit_radius(hero_champion))
                for ch_, data_, what_ in world_[0].tick(game_now):
                    for a, st in peers.items():
                        if st.connected:
                            send_message(a, st, ch_, data_, what_, quiet=what_[:3] not in ('310', '417', '128', '634', '137'))
                if world_[0].died is not None:
                    w_ = world_[0]
                    for td_, net_, src_ in w_.died:
                        w_.state_log.write(f'D {time.time() * 1000:.0f} {td_:.3f} {net_:x} {src_:x}\n')
                    del w_.died[:]
                    if game_now >= w_.state_next:
                        w_.state_next = game_now + 1.0
                        w_.state_log.write(f'T {time.time() * 1000:.0f} {game_now:.3f}\n')
                        for net_, m_ in w_.minions.items():
                            p_ = m_.pos(game_now) or (0.0, 0.0)
                            w_.state_log.write(f'{net_:x} {m_.team} {m_.lane} {m_.kind} {m_.hp:.1f} {p_[0]:.0f} {p_[1]:.0f} '
                                               f'{m_.target or 0:x} {int(m_.standing)}{int(m_.chasing)}\n')
                        for net_, h_ in w_.heroes.items():
                            w_.state_log.write(f'{net_:x} hero - - 0 {h_["pos"][0]:.0f} {h_["pos"][1]:.0f} 0 00\n')
                        w_.state_log.flush()
                for a, st in peers.items():
                    if st.connected and hero is not None:
                        world_events(a, st)
                        if getattr(st, 'dead', False) and time.time() >= st.alive_at:
                            hero_returns(a, st)
                        if getattr(st, 'recalling', None) and time.time() >= st.recalling:
                            st.recalling = None
                            team_ = 'red' if hero_teams.get(hero) in ('red', 200) else 'blue'
                            fountain = (394.77, 461.57) if team_ == 'blue' else (14340.42, 14391.08)
                            st.hero_pos = fountain
                            if world_[0] is not None:
                                world_[0].set_hero(hero, team_, fountain)
                            send_path(a, st, [fountain], 'recall teleport')
                            r = world_[0].real['respawn_128'][0] if (world_[0] and 'respawn_128' in world_[0].real) else None
                            if r:
                                fpos = struct.pack('<ff', fountain[0], fountain[1]).hex()
                                ch, data, what = r.packet(hero, lambda v: v.update({'+0xc': fpos, '+0x14': '00000000'}), 'respawn_128 recall')
                                send_message(a, st, ch, data, '128 recall to fountain')
                            print(f'{game_now:8.3f}   Recall completed! Champion teleported to fountain.', flush=True)
                        if game_now - own_hero_state.get('regen_t', game_now) >= 1.0 or 'regen_t' not in own_hero_state:
                            hero_regen(a, st, game_now - own_hero_state.get('regen_t', game_now))
                            own_hero_state['regen_t'] = game_now
            if hero_values and hero is not None and game_now >= next_hero_595:
                # --hero-set "mGold=9999;...": our own 595 for the hero, by value name (repl_codec.py), every 2 s
                import repl_codec as RC
                next_hero_595 = game_now + 2.0
                for a, st in peers.items():
                    if st.connected:
                        send_message(a, st, 2, struct.pack('<HI', 595, 0) + RC.packet([(hero, hero_values, RC.HERO)], game_now, hero_595_counter),
                                     f'our 595 {hero_values}')
                        if '--shots-on-cast' in args:
                            cast_shots.extend([time.time() + 0.5, time.time() + 1.0])
            # --auto-skill "1,2": the server levels those slots itself once the game runs (a test aid: the client does
            # not ask to level W / E for champions other than the replay's Darius -- cause not found yet)
            if auto_skill and game_now > 2.0:
                for a, st in peers.items():
                    if st.connected:
                        for sl_ in auto_skill:
                            skill_up(a, st, sl_, t)
                auto_skill.clear()
            # --teleport "90:7100,7100": a test aid, the hero is put there at that game time (Flash's teleport entry)
            for tp_ in auto_teleport:
                if game_now >= tp_[0] and hero is not None:
                    import waypoints as Wt
                    for a, st in peers.items():
                        if st.connected:
                            cell = (int(round((tp_[1] - Wt.CENTER[0]) / Wt.CELL)), int(round((tp_[2] - Wt.CENTER[1]) / Wt.CELL)))
                            teleports[hero] = teleports.get(hero, 1) + 1
                            send_message(a, st, 2, struct.pack('<HI', 552, 0) + LP.encode_552(LP.waypoint_teleport(hero, cell, 340.0, teleports[hero])),
                                         f'552 test teleport to ({tp_[1]:.0f}, {tp_[2]:.0f})')
                            st.pos, st.path = (tp_[1], tp_[2]), None
                    tp_[0] = 1e9
            for wd_ in world_do:
                if game_now >= wd_[0] and world_[0] is not None and hero is not None:
                    for a, st in peers.items():
                        if not st.connected:
                            continue
                        if wd_[1].startswith('xp='):
                            hero_xp(a, st, float(wd_[1][3:]))
                        elif wd_[1] == 'raze':
                            for tier_ in ('outer', 'inner', 'inhibitor', 'nexus', 'hq'):
                                for tu_ in list(world_[0].turrets.values()):
                                    if tu_.team == 'red' and tu_.tier == tier_ and (tier_ in ('nexus', 'hq') or tu_.lane == 'mid'):
                                        for ch_, data_, what_ in world_[0].hit(game_now, hero, tu_.net, 99999.0):
                                            send_message(a, st, ch_, data_, what_)
                    wd_[0] = 1e9
            for aa_ in auto_attack:
                if game_now >= aa_[0] and hero is not None:
                    for a, st in peers.items():
                        if st.connected:
                            st.aa = {'target': aa_[1], 'next': 0}
                    aa_[0] = 1e9
            for a, st in peers.items():
                if st.connected and getattr(st, 'aa', None) and chase(a, st, game_now) and time.time() >= st.aa['next']:
                    aa_now = st.aa
                    attack_tick(a, st)
                    st.aa_ready = aa_now['next']
            hemo_ticks()
            for aw in auto_w:
                if game_now >= aw[0] and hero is not None:
                    for a, st in peers.items():
                        if st.connected:
                            if st.skills.get(1, 0) == 0:
                                skill_up(a, st, 1, t)
                            if getattr(st, 'aa', None):
                                darius_w(a, st, st.aa['target'], 'both')
                            else:
                                darius_w(a, st, aw[1])
                    aw[0] = 1e9
            for ac in auto_cast:
                if game_now >= ac[0] and hero is not None:
                    for a, st in peers.items():
                        if st.connected:
                            if st.skills.get(ac[1], 0) == 0:
                                skill_up(a, st, ac[1], t)
                            generic_cast(a, st, t, ac[1], (ac[2], ac[3]), hero_pos(st))
                    ac[0] = 1e9
            if auto_q is not None and hero is not None:
                for a, st in peers.items():
                    if st.connected and auto_q_done == 0 and game_now >= auto_q:
                        skill_up(a, st, 0, t)
                        auto_q_done = 1
                    elif st.connected and auto_q_done == 1 and game_now >= auto_q + 1.0:
                        cast_q(a, st, t)
                        auto_q_done = 2
            if t - last_report > 2:
                last_report = t
                game_now = stream_t0[1] + (time.time() - stream_t0[0]) * speed
                top = sorted(sent_count.items(), key=lambda kv: -kv[1])[:8]
                print(f'{t:8.3f} replay at game time {game_now:.1f}: {sum(sent_count.values())} packets sent, top {top}', flush=True)
        if d is None:
            if t - last_keepalive > 0.25:
                last_keepalive = t
                for a, st in peers.items():
                    if st.connected:
                        send_data(a, st, b'', 'keepalive', quiet=stream_t0 is not None)
            continue
        prefix, body = d[:id_len], d[id_len:]; s2c[0] = prefix[8:12]
        m = parse(lnp.open(body))
        extra = m['extra'] if m['extra'] is not None else NO_EXTRA
        ok = checksum(m['seq'], PEER, extra, m['payload']) == m['crc']
        p = m['payload']
        seq = m['seq']
        st = peers.setdefault(addr, Peer())
        if seq & 0x8000:
            print(f'{t:8.3f} rcv ack latest {(-seq) & 0xFFFF} mask {m["extra"]:016x} crc {"ok" if ok else "BAD"}', flush=True)
            continue
        print(f'{t:8.3f} rcv {len(d)} seq {seq:#06x} flag {m["flag"]} crc {"ok" if ok else "BAD"} len {len(p)}', flush=True)
        if seq == 0 and len(p) == 500:
            cn, guess = struct.unpack_from('<QQ', p)
            flag = p[16]
            if guess == server_nonce and not st.connected:
                print(f'{t:8.3f} peer {addr} connected (client nonce {cn:016x}, flag {flag})', flush=True)
                st.connected = True
            reply = struct.pack('<QQB', cn, server_nonce, flag).ljust(100, b'\0')
            s.sendto(s2c[0] + build(lnp, 0, reply), addr)
            print(f'{t:8.3f} snd accept', flush=True)
            continue
        if seq == 0:
            print(f'{t:8.3f}   control len {len(p)}: {p[:32].hex()}', flush=True)
            continue
        st.got(seq)
        s.sendto(s2c[0] + build(lnp, (-st.latest) & 0xFFFF, b'', extra=st.mask), addr)
        if m['flag']:   # zstd (the client compresses larger packets; [Network] CompressionLevel 3)
            import zstandard
            p = zstandard.ZstdDecompressor().decompress(p, max_output_size=0x44c)
        for ch, num, frag, data in split_messages(p):
            pid = struct.unpack_from('<H', data)[0] if len(data) >= 2 else None
            print(f'{t:8.3f}   msg ch {ch} num {num} frag {frag} len {len(data)} id {pid}: {data[:40].hex()}', flush=True)
            if pid == 1 and send_574 and not st.sent_574:
                st.sent_574 = True
                body = bytearray(open(REPLAY_574, 'rb').read()) if own_574 is None else bytearray(own_574)
                if slot is not None and own_574 is None:
                    body[2] = SLOT_BYTE[slot]
                send_message(addr, st, 1, struct.pack('<HI', 574, 0) + bytes(body), f'packet 574 (slot {slot})')
            if getattr(st, 'dead', False) and pid in (491, 16):
                continue                              # a dead hero neither walks nor casts
            if pid == 491 and hero is not None:
                if getattr(st, 'recalling', None):
                    st.recalling = None
                    print(f'{t:8.3f}   Recall cancelled by movement!', flush=True)
                o = LP.decode_491(data[6:])
                # order type and target through the codec learnt from the client's writer (c2s_codec.py, c2s_491.json)
                import c2s_codec as CC
                o2 = CC.decode(CC.load(491), data[6:])
                game_now = stream_t0[1] + (time.time() - stream_t0[0]) * speed if stream_t0 else 0.0
                team_ = 'red' if hero_teams.get(hero) in ('red', 200) else 'blue'
                fountain = (394.77, 461.57) if team_ == 'blue' else (14340.42, 14391.08)
                if o2:
                    o_type = o2[0x10][0]
                    o_target = struct.unpack('<I', o2[0x14])[0]
                    print(f'{t:8.3f}   order type {o_type} target {o_target:#x} +0x18 {o2[0x18].hex()}', flush=True)
                    if o_type == 3 and o_target:
                        if game_now < 15.0:
                            print(f'{t:8.3f}   [0:00-0:15 FOUNTAIN BARRIER] attack order outside spawn blocked', flush=True)
                        elif not (getattr(st, 'aa', None) and st.aa.get('target') == o_target):
                            # the same order again leaves the running attack alone; another target keeps the time
                            # the next attack may start (the hero has one attack timer, not one per click)
                            st.aa = {'target': o_target, 'next': getattr(st, 'aa_ready', 0.0)}
                    elif o_type == 2:
                        st.aa = None
                print(f'{t:8.3f}   order {o}', flush=True)
                if o and o['type'] == 2 and o.get('path'):
                    raw_pts = [hero_pos(st)] + [W.to_world(p_) for p_ in o['path'][1:]]
                    if game_now < 15.0:
                        clamped_pts = [raw_pts[0]]
                        for pt in raw_pts[1:]:
                            dx, dz = pt[0] - fountain[0], pt[1] - fountain[1]
                            dist = math.hypot(dx, dz)
                            if dist > 950.0:
                                sc_ = 950.0 / dist
                                clamped_pts.append((fountain[0] + dx * sc_, fountain[1] + dz * sc_))
                            else:
                                clamped_pts.append(pt)
                        raw_pts = clamped_pts
                        print(f'{t:8.3f}   [0:00-0:15 FOUNTAIN BARRIER] movement clamped inside spawn platform', flush=True)
                    send_path(addr, st, raw_pts, 'moves (order)')
            if pid == 782 and hero is not None and own_hero:
                # 782 = the client's purchase request (codec learnt from its writer: c2s_codec, c2s_782.json)
                import c2s_codec as CC
                req = CC.decode(CC.load(782), data[6:])
                if req:
                    buy_item(addr, st, struct.unpack('<I', req[0xc])[0])
            if pid == 384 and hero is not None and len(data) >= 7:
                skill_up(addr, st, LP.decode_384(data[6:]), t)
            if pid == 16 and hero is not None:
                # 16 = the client's cast request, read with the codec learnt from the client's own writer
                # (c2s_codec.py, data/exe133/codec/c2s_16.json)
                import c2s_codec as CC
                req = CC.decode(CC.load(16), data[6:])
                if req:
                    # +0xc the unit a targeted spell is cast on (the hero itself for a self cast), +0x10 the aimed
                    # place, +0x24 the slot, +0x34 the spell; +0x1c / +0x28 hold the hero's place in one and the
                    # aimed place in the other, which of them depends on the kind of cast -- the hero's place
                    # is the server's own (hero_pos), never the request's
                    slot_ = req[0x24][0]
                    tx, tz = struct.unpack('<ff', req[0x10])
                    cx, cz = struct.unpack('<ff', req[0x1c])
                    target_net_ = struct.unpack('<I', req[0xc])[0]
                    spell_hash = struct.unpack('<I', req[0x34])[0]
                    print(f'{t:8.3f}   cast request: slot {slot_}, spell hash {spell_hash:#x}, target ({tx:.0f}, {tz:.0f}), '
                          f'caster at ({cx:.0f}, {cz:.0f}), +0x18 {req[0x18].hex()}', flush=True)
                if not req:
                    continue
                st.spell_cds = getattr(st, 'spell_cds', {})
                if time.time() < st.spell_cds.get(slot_, 0.0):
                    rem_cd = st.spell_cds[slot_] - time.time()
                    print(f'{t:8.3f}   DROP cast request slot {slot_}: on cooldown ({rem_cd:.2f}s remaining)', flush=True)
                    continue
                if spell_hash == 0x0568d0ac or slot_ in (6, 13):
                    st.recalling = time.time() + 8.0
                    print(f'{t:8.3f}   Recall started! Channeling for 8.0s...', flush=True)
                elif not hero_spells and slot_ == 1 and hero_champion == 'Darius':
                    aa_ = getattr(st, 'aa', None)
                    if aa_:
                        darius_w(addr, st, aa_['target'], 'both')
                        import spell_info as SIw
                        aa_['next'] = time.time() + SIw.attack_times('Darius')[0]
                    else:
                        darius_w(addr, st, 0, 'cast')
                elif slot_ in (4, 5):
                    summoner_cast(addr, st, slot_, (tx, tz))
                elif slot_ < len(engine_spells):
                    if st.skills.get(slot_, 0) == 0:
                        print(f'{t:8.3f}   DROP cast request slot {slot_}: spell not learned yet (level 0)', flush=True)
                        continue
                    generic_cast(addr, st, t, slot_, (tx, tz), (cx, cz), target_net_)
                elif q_reply:
                    cast_q(addr, st, t)
            if pid == 527 and stream is not None and stream_t0 is None:
                stream_t0 = (time.time(), start_at)
                print(f'{t:8.3f} client loaded (527): streaming the replay from game time {start_at}', flush=True)
                if '--shots-game' in args:
                    # --shots-game "65,66.5": frames at those GAME seconds (the client's clock starts with the stream)
                    cast_shots.extend(stream_t0[0] + (float(x) - start_at) / speed
                                      for x in args[args.index('--shots-game') + 1].split(','))


if __name__ == '__main__':
    main()
