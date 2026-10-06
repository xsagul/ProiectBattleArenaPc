-- Zed. Numbers: his spells' own data (Value: mDataValues, EffectValue: mEffectAmount, Calc: mSpellCalculations);
-- behaviour: documented as of patch 14.1 (LoL Wiki, the pages' revisions of January 2024). Effect keys: his skin's
-- ResourceResolver. His shadows are the ZedShadow character of his own files.

local shadows = {}   -- caster -> list of { id, x, z, from = "W" | "R" }
local wcast, rcast = {}, {}  -- caster -> the Living Shadow / Death Mark cast whose shadow he may change places with
local marks = {}     -- caster -> { target, dealt } while Death Mark runs
local struck = {}    -- caster -> { [target] = when Contempt for the Weak last struck it }

local function shadows_of(u)
  local live = {}
  for _, s in ipairs(shadows[u] or {}) do
    if Exists(s.id) then live[#live + 1] = s end
  end
  shadows[u] = live
  return live
end

-- (what Zed deals to his marked target counts toward Death Mark's burst)
-- [de măsurat: the documentation counts the damage before the target's armor; this counts what the target took]
local function hurt(u, t, amount, kind, spell)
  local dealt = Damage(u, t, amount, kind, spell)
  local m = marks[u]
  if m and m.target == t then m.dealt = m.dealt + dealt end
  return dealt
end

-- Living Shadow's passive: when Zed and a shadow strike the same enemy with one cast, he gets energy back, once a cast:
-- ZedW's third effect amount (at rank 1 before the spell is learned).
local function shared_hit(u, cast)
  if cast.restored then return end
  cast.restored = true
  AddResource(u, EffectValue(u, "ZedW", 3, math.max(1, Rank(u, 1))))
end

-- Contempt for the Weak: an attack on a unit below CurrentHealthThreshold of its health deals a share of its maximum
-- health as magic damage (the passive's calculation {6a1a62e9}: 6% to 10% by level; the files give it no name), once
-- every PerUnitCD seconds for each target.
Champion "Zed" {
  OnAttackHit = function(u, target, crit, damage)
    local m = marks[u]
    if m and m.target == target then m.dealt = m.dealt + damage end
    if not (IsChampion(target) or IsMinion(target)) or IsDead(target) then return end
    if HP(target) / math.max(1, MaxHP(target)) >= Value(u, "ZedPassive", "CurrentHealthThreshold") then return end
    local seen = struck[u] or {}
    struck[u] = seen
    if seen[target] and Now() - seen[target] < Value(u, "ZedPassive", "PerUnitCD") then return end
    seen[target] = Now()
    Effect(target, "Zed_Passive_Proc_tar", "", 0, u)
    hurt(u, target, MaxHP(target) * Calc(u, "ZedPassive", "{6a1a62e9}"), "magic", "ZedPassive")
  end,
}

-- Razor Shuriken: Zed and his shadows each throw a shuriken (ZedQMissile: its range, speed and width): TotalDamage to
-- the first enemy it meets, PassThroughDamage to those after it.
-- [de măsurat: an enemy struck by several shurikens takes each one's damage in full]
local function shuriken(u, x, z, tx, tz, cast, own)
  local first = true
  Missile {
    source = u, spell = "ZedQ", effect = "Zed_Q_Mis", x = x, z = z, tx = tx, tz = tz,
    speed = SpellInfo(u, "ZedQMissile", "speed"), range = SpellInfo(u, "ZedQMissile", "range"), width = SpellInfo(u, "ZedQMissile", "width"),
    on_hit = function(t)
      hurt(u, t, Calc(u, "ZedQ", first and "TotalDamage" or "PassThroughDamage"), "physical", "ZedQ")
      Effect(t, "Zed_Q_tar", "", 0, u)
      first = false
      local by = cast.hit[t] or {}
      cast.hit[t] = by
      by[own and "zed" or "shadow"] = true
      if by.zed and by.shadow then shared_hit(u, cast) end
      return false
    end,
  }
end

Spell "ZedQ" {
  OnCast = function(c)
    local u = c.caster
    local x, z = Pos(u)
    local cast = { hit = {} }
    shuriken(u, x, z, c.x, c.z, cast, true)
    for _, s in ipairs(shadows_of(u)) do
      Animate(s.id, "Spell1", 0.5)
      if math.abs(c.x - s.x) + math.abs(c.z - s.z) > 1 then shuriken(u, s.x, s.z, c.x, c.z, cast, false) end
    end
  end,
}

-- Living Shadow: a shadow darts to a place up to the spell's range away (ZedWMissile's speed) and stays for the first
-- effect amount (5.25 seconds); cast again, Zed changes places with it. Shadows copy Razor Shuriken and Shadow Slash.
local function leave_shadow(u, x, z, seconds, from)
  local id = SpawnUnit(u, "ZedShadow", x, z, seconds)
  local s = { id = id, x = x, z = z, from = from }
  local list = shadows_of(u)
  list[#list + 1] = s
  return s
end

-- Zed and the shadow change places: he is where it stood, and it stands where he was for the rest of its time
local function swap(u, s, left)
  local x, z = Pos(u)
  Effect(u, "Zed_CloneSwap")
  RemoveUnit(s.id)
  for i, o in ipairs(shadows[u]) do
    if o == s then table.remove(shadows[u], i) break end
  end
  Blink(u, s.x, s.z)
  if left > 0.1 then leave_shadow(u, x, z, left, s.from) end
end

Spell "ZedW" {
  OnCast = function(c)
    local u = c.caster
    -- a new shadow takes the place of the one before
    for _, s in ipairs(shadows_of(u)) do
      if s.from == "W" then RemoveUnit(s.id) end
    end
    local seconds = EffectValue(u, "ZedW", 1)
    local x, z = ClampWalkable(u, c.x, c.z, SpellInfo(u, "ZedW", "range"))
    local sx, sz = Pos(u)
    local speed = SpellInfo(u, "ZedWMissile", "speed")
    local travel = math.sqrt((x - sx) ^ 2 + (z - sz) ^ 2) / speed
    local cast = { born = Now() + travel, seconds = seconds }
    wcast[u] = cast
    Missile { source = u, spell = "ZedW", effect = "Zed_W_Mis", tx = x, tz = z, speed = speed, range = math.max(1, travel * speed), width = 0 }
    SetRecast(u, c.slot, true, travel)
    After(travel, function()
      if wcast[u] ~= cast then return end
      cast.shadow = leave_shadow(u, x, z, seconds, "W")
    end)
    After(travel + seconds, function()
      if wcast[u] == cast then
        wcast[u] = nil
        SetRecast(u, c.slot, false)
      end
    end)
  end,
  OnRecast = function(c)
    local u = c.caster
    if IsRooted(u) or IsStunned(u) then return end
    local cast = wcast[u]
    SetRecast(u, c.slot, false)
    if not cast or not cast.shadow or not Exists(cast.shadow.id) or IsDead(u) then return end
    shadows_of(u)
    wcast[u] = nil
    swap(u, cast.shadow, cast.born + cast.seconds - Now())
  end,
}

-- Shadow Slash: Zed and his shadows slash around them (ZedRadius around Zed, ShadowRadius around a shadow): TotalDamage,
-- once to each enemy however many slashes reach it. A shadow's slash slows by MoveSpeedMod for SlowDuration, by
-- MoveSpeedModBonus when more than one slash reached the enemy. Each enemy champion Zed's own slash hits takes
-- ShadowHitCDR seconds off Living Shadow's cooldown.
Spell "ZedE" {
  OnCast = function(c)
    local u = c.caster
    local x, z = Pos(u)
    local reached = {}  -- target -> { slashes, by a shadow }
    local cast = {}
    Effect(u, "Zed_E_Cas")
    for _, t in ipairs(Enemies(u, x, z, Value(u, "ZedE", "ZedRadius"))) do
      reached[t] = { slashes = 1, own = true }
      if IsChampion(t) then SetCooldown(u, 1, math.max(0, Cooldown(u, 1) - Value(u, "ZedE", "ShadowHitCDR"))) end
    end
    for _, s in ipairs(shadows_of(u)) do
      Effect(s.id, "Zed_E_Cas_Shadow", "", 0, u)
      Animate(s.id, "Spell3", 0.5)
      for _, t in ipairs(Enemies(u, s.x, s.z, Value(u, "ZedE", "ShadowRadius"))) do
        local r = reached[t] or { slashes = 0 }
        reached[t] = r
        r.slashes, r.shadow = r.slashes + 1, true
      end
    end
    for t, r in pairs(reached) do
      hurt(u, t, Calc(u, "ZedE", "TotalDamage"), "physical", "ZedE")
      Effect(t, "Zed_E_tar", "", 0, u)
      if r.shadow then
        AddBuff(t, { name = "ZedESlow", source = u, duration = Value(u, "ZedE", "SlowDuration"),
                     move_speed = Value(u, "ZedE", r.slashes > 1 and "MoveSpeedModBonus" or "MoveSpeedMod") })
        if r.own then shared_hit(u, cast) end
      end
    end
  end,
}

-- Death Mark: Zed leaps onto an enemy champion, leaving a shadow where he stood for RCanSwapBuffDuration seconds; after
-- RReactivateCD, cast again, he changes places with it. After RDeathMarkDuration the mark bursts for
-- RCalculatedDamage plus RDamageAmp of the damage Zed dealt the target meanwhile.
-- Documented: Zed is untargetable for 0.6 seconds before appearing behind the target.
Spell "ZedR" {
  OnCast = function(c)
    local u, t = c.caster, c.target
    if not t or IsDead(t) then return end
    local x, z = Pos(u)
    local tx, tz = Pos(t)
    local seconds = Value(u, "ZedR", "RCanSwapBuffDuration")
    local cast = { born = Now(), seconds = seconds }
    for _, s in ipairs(shadows_of(u)) do
      if s.from == "R" then RemoveUnit(s.id) end
    end
    rcast[u] = cast
    Effect(u, "Zed_R_cas")
    cast.shadow = leave_shadow(u, x, z, seconds, "R")
    AddBuff(u, { name = "ZedRUntargetable", source = u, duration = 0.6, untargetable = true, invulnerable = true, disarm = true, root = true })
    SetFacing(u, tx, tz)
    After(0.6, function()
      if IsDead(u) or not Exists(t) or IsDead(t) then return end
      local nx, nz = Pos(t)
      local len = math.max(1, math.sqrt((nx - x) ^ 2 + (nz - z) ^ 2))
      local bx, bz = ClampWalkable(t, nx + (nx - x) / len * 125, nz + (nz - z) / len * 125, 125)
      Blink(u, bx, bz)
      SetFacing(u, nx, nz)
      AttackOrder(u, t)
      Effect(t, "Zed_R_tar_TargetMarker", "", Value(u, "ZedR", "RDeathMarkDuration"), u)
      marks[u] = { target = t, dealt = 0 }
      SetRecast(u, c.slot, true, Value(u, "ZedR", "RReactivateCD"))
    end)
    After(seconds, function()
      if rcast[u] == cast then
        rcast[u] = nil
        SetRecast(u, c.slot, false)
      end
    end)
    After(0.6 + Value(u, "ZedR", "RDeathMarkDuration"), function()
      local m = marks[u]
      marks[u] = nil
      if not m or not Exists(m.target) or IsDead(m.target) then return end
      Effect(m.target, "Zed_R_tar_Impact", "", 0, u)
      Damage(u, m.target, Calc(u, "ZedR", "RCalculatedDamage") + Value(u, "ZedR", "RDamageAmp") * m.dealt, "physical", "ZedR")
    end)
  end,
  OnRecast = function(c)
    local u = c.caster
    if IsRooted(u) or IsStunned(u) then return end
    local cast = rcast[u]
    SetRecast(u, c.slot, false)
    if not cast or not cast.shadow or not Exists(cast.shadow.id) or IsDead(u) then return end
    shadows_of(u)
    rcast[u] = nil
    swap(u, cast.shadow, cast.born + cast.seconds - Now())
  end,
}
