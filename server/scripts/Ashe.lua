-- Ashe. Numbers: her spells' own data (Value: mDataValues, EffectValue: mEffectAmount, Calc: mSpellCalculations);
-- behaviour: documented as of patch 14.1 (LoL Wiki, the pages' revisions of January 2024). Effect keys: her skin's
-- ResourceResolver.

-- Frost Shot: Ashe's attacks and spells put Frost on what they hit for SlowDuration: a slow of SlowAmount (by level).
-- Her attacks on a target that has Frost deal DamageBonus times their damage. Her critical strikes deal no more damage
-- but slow by EmpoweredSlowAmount (nothing gives her a critical chance yet; Volley slows that way).
local function frost(u, t, amount)
  if not (IsChampion(t) or IsMinion(t)) then return end
  local seconds = Value(u, "AshePassive", "SlowDuration")
  AddBuff(t, { name = "AsheFrost", source = u, duration = seconds, move_speed = -amount })
  Effect(t, "Ashe_freeze", "", seconds, u)
end

local focus = {}     -- caster -> { stacks of Focus, when the last one came or went }
local flurry = {}    -- caster -> Ranger's Focus is on

Champion "Ashe" {
  OnAttackHit = function(u, target, crit, damage)
    if HasBuff(target, "AsheFrost") then
      -- the attack's damage again, for the share over 1 (a flurry's arrows each carry it)
      local attack = Stat(u, "ad") * (flurry[u] and Value(u, "AsheQ", "DamagePerStrike") or 1)
      Damage(u, target, attack * (Calc(u, "AshePassive", "DamageBonus") - 1), "physical", "AshePassive")
    end
    frost(u, target, Calc(u, "AshePassive", crit and "EmpoweredSlowAmount" or "SlowAmount"))
    -- Focus: a stack with every attack on a unit while Ranger's Focus is learned and not running, up to the spell's
    -- first effect amount (4)
    if Rank(u, 0) > 0 and not flurry[u] and (IsChampion(target) or IsMinion(target)) then
      local f = focus[u] or { stacks = 0 }
      local most = EffectValue(u, "AsheQ", 1)
      f.stacks = math.min(most, f.stacks + 1)
      f.at = Now()
      focus[u] = f
      if f.stacks >= most then Effect(u, "Ashe_Q_ready", "", EffectValue(u, "AsheQ", 2)) end
    end
  end,
  -- the stacks last the second effect amount (4 seconds) from the last attack, then go one a second
  OnTick = function(u)
    local f = focus[u]
    if f and f.stacks > 0 and Rank(u, 0) > 0 and Now() - f.at > EffectValue(u, "AsheQ", 2) then
      f.stacks = f.stacks - 1
      f.at = f.at + 1
      StopEffect(u, "Ashe_Q_ready")
    end
  end,
}

-- Ranger's Focus: it takes all the stacks of Focus; for the third effect amount (6 seconds) Ashe attacks faster by the
-- fourth (25 .. 55 percent) and each attack is a flurry of arrows dealing DamagePerStrike times her attack damage in
-- all. Her attack timer starts over.
Spell "AsheQ" {
  CanCast = function(c)
    local f = focus[c.caster]
    return f ~= nil and f.stacks >= EffectValue(c.caster, "AsheQ", 1)
  end,
  OnCast = function(c)
    local u = c.caster
    local seconds = EffectValue(u, "AsheQ", 3)
    focus[u] = { stacks = 0, at = Now() }
    flurry[u] = true
    StopEffect(u, "Ashe_Q_ready")
    Effect(u, "Ashe_Q_Buf", "", seconds)
    ResetAttack(u)
    AddBuff(u, {
      name = "AsheQ", source = u, duration = seconds, attack_speed = EffectValue(u, "AsheQ", 4) / 100,
      on_attack = function(target)
        return Stat(u, "ad") * (Value(u, "AsheQ", "DamagePerStrike") - 1), false
      end,
      on_expire = function() flurry[u] = nil end,
    })
  end,
}

-- Volley: NumberOfArrowsTooltip arrows in a cone (VolleyAttack: their range, speed and width), each stopping at the
-- first enemy it meets: TotalDamage, and Frost at its critical strength. An enemy is hurt by one arrow only, but may
-- stop several.
-- [documentat: 4.625 degrees between one arrow and the next; the files' castConeAngle (20) is not that fan]
local kVolleyDegrees = 4.625

Spell "Volley" {
  OnCast = function(c)
    local u = c.caster
    local ux, uz = Pos(u)
    local base = math.atan2(c.x - ux, c.z - uz)
    local arrows = Value(u, "Volley", "NumberOfArrowsTooltip")
    local hurt = {}
    for i = 0, arrows - 1 do
      local a = base + math.rad(kVolleyDegrees) * (i - (arrows - 1) / 2)
      Missile {
        source = u, spell = "Volley", effect = "Ashe_W_mis", tx = ux + math.sin(a) * 100, tz = uz + math.cos(a) * 100,
        speed = SpellInfo(u, "VolleyAttack", "speed"), range = SpellInfo(u, "VolleyAttack", "range"), width = SpellInfo(u, "VolleyAttack", "width"),
        on_hit = function(t)
          if not hurt[t] then
            hurt[t] = true
            Damage(u, t, Calc(u, "Volley", "TotalDamage"), "physical", "Volley")
            frost(u, t, Calc(u, "AshePassive", "EmpoweredSlowAmount"))
            Effect(t, "Ashe_W_Tar", "", 0, u)
          end
          return true
        end,
      }
    end
  end,
}

-- Hawkshot: a hawk that shows the land it flies over and around where it lands. There is no fog of war yet: it flies,
-- and shows nothing new.
Spell "AsheSpiritOfTheHawk" {
  OnCast = function(c)
    local u = c.caster
    local ux, uz = Pos(u)
    Missile { source = u, spell = "AsheSpiritOfTheHawk", effect = "Ashe_E_mis", tx = c.x, tz = c.z, width = 0,
              speed = SpellInfo(u, "AsheSpiritOfTheHawk", "speed"), range = math.max(100, math.sqrt((c.x - ux) ^ 2 + (c.z - uz) ^ 2)) }
  end,
}

-- Enchanted Crystal Arrow: an arrow across the whole map (its range, width, and a speed that grows as it flies) that
-- stops at the first enemy champion: RMainDamage and a stun of MinStunDuration to MaxStunDuration by how far it flew
-- [documentat: the longest after 2800 units]; the enemies within SlowRadius of it take RAoEDamage and Frost.
local kLongestStunDistance = 2800

Spell "EnchantedCrystalArrow" {
  OnCast = function(c)
    local u = c.caster
    local spell = "EnchantedCrystalArrow"
    local sx, sz = Pos(u)
    Missile {
      source = u, spell = spell, effect = "Ashe_R_mis", tx = c.x, tz = c.z, champions = true,
      speed = SpellInfo(u, spell, "speed"), accel = SpellInfo(u, spell, "accel"), speed_limit = SpellInfo(u, spell, "speed_limit"),
      range = SpellInfo(u, spell, "range"), width = SpellInfo(u, spell, "width"),
      on_hit = function(t)
        local tx, tz = Pos(t)
        local flown = math.sqrt((tx - sx) ^ 2 + (tz - sz) ^ 2)
        local lo, hi = Value(u, spell, "MinStunDuration"), Value(u, spell, "MaxStunDuration")
        AddBuff(t, { name = "EnchantedCrystalArrowStun", source = u, duration = lo + (hi - lo) * math.min(1, flown / kLongestStunDistance), stun = true })
        Effect(t, "Ashe_R_Tar", "", 0, u)
        Damage(u, t, Calc(u, spell, "RMainDamage"), "magic", spell)
        frost(u, t, Calc(u, "AshePassive", "SlowAmount"))
        for _, o in ipairs(Enemies(u, tx, tz, Value(u, spell, "SlowRadius"))) do
          if o ~= t then
            Damage(u, o, Calc(u, spell, "RAoEDamage"), "magic", spell)
            frost(u, o, Calc(u, "AshePassive", "SlowAmount"))
          end
        end
        return true
      end,
    }
  end,
}
