-- Tryndamere. Numbers: his spells' own data (Value: mDataValues, Calc: mSpellCalculations); behaviour: documented as
-- of patch 14.1 (LoL Wiki, the pages' revisions of January 2024). Effect keys: his skin's ResourceResolver.

-- Battle Fury [documentat]: 5 fury for an attack, 10 for a critical strike, 10 more for a kill; after 8 seconds without
-- dealing or taking damage it drains by 5 a second. Each point of fury is critical strike chance: the passive's
-- calculation {dc63b617} (0.4% a point; the files give it no name).
-- Bloodlust's passive half: attack damage, FlatAD and ADPerOnePercentMissingHP for each percent of health missing.
local kFuryAttack, kFuryCrit, kFuryKill, kFuryCalm, kFuryDrain = 5, 10, 10, 8, 5
local last = {}  -- caster -> what refresh last gave, so the buff is only set again when it changes

local function refresh(u)
  local ad = 0
  if Rank(u, 0) > 0 then
    local missing = 100 * (1 - HP(u) / math.max(1, MaxHP(u)))
    ad = Value(u, "TryndamereQ", "FlatAD") + Value(u, "TryndamereQ", "ADPerOnePercentMissingHP") * missing
  end
  local crit = Resource(u) * Calc(u, "TryndamerePassive", "{dc63b617}")
  local was = last[u]
  if was and math.abs(was.ad - ad) < 0.05 and math.abs(was.crit - crit) < 0.0005 and HasBuff(u, "TryndamereBattleFury") then return end
  last[u] = { ad = ad, crit = crit }
  AddBuff(u, { name = "TryndamereBattleFury", source = u, crit = crit, ad = ad })
end

Champion "Tryndamere" {
  OnAttackHit = function(u, target, crit)
    AddResource(u, crit and kFuryCrit or kFuryAttack)
    if crit then
      -- Spinning Slash comes back sooner with every critical strike: ChampCDRefund against champions, NonChampCDRefund
      -- against the rest
      local left = Cooldown(u, 2)
      if left > 0 then
        SetCooldown(u, 2, math.max(0, left - Value(u, "TryndamereE", IsChampion(target) and "ChampCDRefund" or "NonChampCDRefund")))
      end
    end
    refresh(u)
  end,
  OnKill = function(u)
    AddResource(u, kFuryKill)
    refresh(u)
  end,
  OnTick = function(u)
    if not IsDead(u) then
      if SinceFight(u) > kFuryCalm and Resource(u) > 0 then AddResource(u, -kFuryDrain / 4) end
      refresh(u)
    end
  end,
}

-- Bloodlust: Tryndamere spends all his fury to heal: BaseHeal, and HealPerFury for every point.
Spell "TryndamereQ" {
  OnCast = function(c)
    local u = c.caster
    local fury = Resource(u)
    Heal(u, Calc(u, "TryndamereQ", "BaseHeal") + Calc(u, "TryndamereQ", "HealPerFury") * fury)
    AddResource(u, -fury)
    Effect(u, "Tryndamere_Q_Heal_01")
    refresh(u)
  end,
}

-- Mocking Shout: enemy champions within the spell's radius lose ADReduction attack damage for ReductionDuration;
-- those facing away from Tryndamere are also slowed by SlowPotency for SlowDuration.
Spell "TryndamereW" {
  OnCast = function(c)
    local u = c.caster
    local x, z = Pos(u)
    Effect(u, "Tryndamere_W_Cas")
    for _, t in ipairs(Enemies(u, x, z, SpellInfo(u, "TryndamereW", "radius"), true)) do
      AddBuff(t, { name = "TryndamereWWeaken", source = u, duration = Value(u, "TryndamereW", "ReductionDuration"), ad = Value(u, "TryndamereW", "ADReduction") })
      -- it faces away when what lies ahead of it is not on his side
      local tx, tz = Pos(t)
      local f = Facing(t)
      if math.sin(f) * (x - tx) + math.cos(f) * (z - tz) < 0 then
        AddBuff(t, { name = "TryndamereWSlow", source = u, duration = Value(u, "TryndamereW", "SlowDuration"), move_speed = Value(u, "TryndamereW", "SlowPotency") })
        Effect(t, "Tryndamere_W_Tar_01", "", Value(u, "TryndamereW", "SlowDuration"), u)
      end
    end
  end,
}

-- Spinning Slash: Tryndamere spins to a place up to the `slash` spell's range away at its speed (660, 700); the
-- enemies within DamageAoE of his path take TotalDamage, and each gives him fury (ChampFuryGain, NonChampFuryGain).
Spell "TryndamereE" {
  OnCast = function(c)
    local u = c.caster
    local sx, sz = Pos(u)
    local x, z = ClampWalkable(u, c.x, c.z, SpellInfo(u, "slash", "range"))
    local speed = SpellInfo(u, "slash", "speed")
    local seconds = math.sqrt((x - sx) ^ 2 + (z - sz) ^ 2) / speed
    Effect(u, "Tryndamere_E_Slash", "", seconds)
    Animate(u, "Spell3", seconds)
    -- each enemy on the way is struck as he comes level with it
    for _, t in ipairs(EnemiesInLine(u, sx, sz, x, z, 2 * Value(u, "TryndamereE", "DamageAoE"))) do
      local tx, tz = Pos(t)
      After(math.min(seconds, math.sqrt((tx - sx) ^ 2 + (tz - sz) ^ 2) / speed), function()
        if IsDead(u) or IsDead(t) then return end
        Damage(u, t, Calc(u, "TryndamereE", "TotalDamage"), "physical", "TryndamereE")
        AddResource(u, Value(u, "TryndamereE", IsChampion(t) and "ChampFuryGain" or "NonChampFuryGain"))
        refresh(u)
      end)
    end
    Dash(u, x, z, speed)
  end,
}

-- Undying Rage: for TryndRDuration seconds his health cannot fall below TryndRMinHealth, and he gains TryndRFuryGain
-- fury at once.
Spell "UndyingRage" {
  OnCast = function(c)
    local u = c.caster
    local seconds = Value(u, "UndyingRage", "TryndRDuration")
    AddResource(u, Value(u, "UndyingRage", "TryndRFuryGain"))
    AddBuff(u, { name = "UndyingRage", source = u, duration = seconds, min_hp = Value(u, "UndyingRage", "TryndRMinHealth") })
    Effect(u, "Tryndamere_R_buf_01", "", seconds)
    refresh(u)
  end,
}
