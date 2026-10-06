-- Lux. Numbers: her spells' own data (Value: mDataValues, EffectValue: mEffectAmount, Calc: mSpellCalculations);
-- behaviour: documented as of patch 14.1 (LoL Wiki, the pages' revisions of January 2024). Effect keys: her skin's
-- ResourceResolver.

-- Illumination: Lux's damaging spells mark what they hit for DebuffDuration seconds; her basic attacks and Final Spark
-- set the mark off for TotalDamage magic damage.
local function illuminate(u, t)
  local seconds = Value(u, "LuxIlluminationPassive", "DebuffDuration")
  AddBuff(t, { name = "LuxIllumination", source = u, duration = seconds })
  Effect(t, "Lux_P_debuff", "", seconds, u)
end

local function detonate_mark(u, t)
  if not HasBuff(t, "LuxIllumination") then return end
  RemoveBuff(t, "LuxIllumination")
  StopEffect(t, "Lux_P_debuff")
  Effect(t, "Lux_P_tar", "", 0, u)
  Damage(u, t, Calc(u, "LuxIlluminationPassive", "TotalDamage"), "magic", "LuxIlluminationPassive")
end

Champion "Lux" {
  OnAttackHit = function(u, target) detonate_mark(u, target) end,
}

-- Light Binding: a bolt (LuxLightBindingMis: its range, speed and width) that deals TotalDamageTT to the first two
-- enemies it meets and roots them for the spell's third effect amount (2 seconds).
Spell "LuxLightBinding" {
  OnCast = function(c)
    local u = c.caster
    local hits = 0
    Missile {
      source = u, spell = "LuxLightBinding", effect = "Lux_Q_mis", tx = c.x, tz = c.z,
      speed = SpellInfo(u, "LuxLightBindingMis", "speed"), range = SpellInfo(u, "LuxLightBindingMis", "range"),
      width = SpellInfo(u, "LuxLightBindingMis", "width"),
      on_hit = function(t)
        hits = hits + 1
        local seconds = EffectValue(u, "LuxLightBinding", 3)
        AddBuff(t, { name = "LuxLightBindingRoot", source = u, duration = seconds, root = true })
        Effect(t, "Lux_Q_tar", "", seconds, u)
        Damage(u, t, Calc(u, "LuxLightBinding", "TotalDamageTT"), "magic", "LuxLightBinding")
        illuminate(u, t)
        return hits >= 2
      end,
    }
  end,
}

-- Prismatic Barrier: the wand flies out (LuxPrismaticWaveMissile: it leaves fast and slows) and comes back to Lux;
-- she is shielded for TotalShieldTT when it leaves and again when it returns, each for the third effect amount
-- (2.5 seconds). Allied champions in its path are not shielded yet (there are no allies to shield).
-- [dedus: the way back mirrors the way out: from the slow speed up to the fast one]
Spell "LuxPrismaticWave" {
  OnCast = function(c)
    local u = c.caster
    local out = "LuxPrismaticWaveMissile"
    local seconds = EffectValue(u, "LuxPrismaticWave", 3)
    local function shield(name)
      if IsDead(u) then return end
      AddBuff(u, { name = name, source = u, duration = seconds, shield = Calc(u, "LuxPrismaticWave", "TotalShieldTT") })
      Effect(u, "Lux_W_tar_shield", "", seconds)
    end
    shield("LuxPrismaticWaveShield")
    local function shield_allies(x0, z0, x1, z1, name)
      for _, a in ipairs(AlliesInLine(u, x0, z0, x1, z1, 220, true)) do
        if a ~= u and not IsDead(a) then
          AddBuff(a, { name = name, source = u, duration = seconds, shield = Calc(u, "LuxPrismaticWave", "TotalShieldTT") })
          Effect(a, "Lux_W_tar_shield", "", seconds, u)
        end
      end
    end
    local ux, uz = Pos(u)
    shield_allies(ux, uz, c.x, c.z, "LuxPrismaticWaveShield")
    Missile {
      source = u, spell = "LuxPrismaticWave", effect = "Lux_W_mis", tx = c.x, tz = c.z, width = 0,
      speed = SpellInfo(u, out, "speed"), accel = SpellInfo(u, out, "accel"), speed_limit = SpellInfo(u, out, "speed_limit"),
      range = SpellInfo(u, out, "range"),
      on_end = function(x, z)
        if IsDead(u) then return end
        local rux, ruz = Pos(u)
        shield_allies(x, z, rux, ruz, "LuxPrismaticWaveShieldReturn")
        Missile {
          source = u, spell = "LuxPrismaticWave", effect = "Lux_W_mis_return", x = x, z = z, tx = rux, tz = ruz, width = 0,
          speed = SpellInfo(u, out, "speed_limit"), accel = -SpellInfo(u, out, "accel"), speed_limit = SpellInfo(u, out, "speed"),
          range = math.max(1, math.sqrt((rux - x) ^ 2 + (ruz - z) ^ 2)),
          on_end = function() shield("LuxPrismaticWaveShieldReturn") end,
        }
      end,
    }
  end,
}

-- Lucent Singularity: a ball of light flies to the place and lies there for the third effect amount (5 seconds),
-- slowing enemies within the fourth (310) by the first (25 .. 45 percent); the slow lingers SlowLingerDuration after
-- they leave. Cast again at any time (or at the end) it bursts for TotalDamageTT; cast again in flight, it bursts as
-- it lands. [de măsurat: the cooldown runs from the first cast]
local singularity = {}  -- caster -> the ball lying out

Spell "LuxLightStrikeKugel" {
  OnCast = function(c)
    local u = c.caster
    local spell = "LuxLightStrikeKugel"
    local radius, duration = EffectValue(u, spell, 4), EffectValue(u, spell, 3)
    local slow, linger = -EffectValue(u, spell, 1) / 100, Value(u, spell, "SlowLingerDuration")
    local x, z = c.x, c.z
    local sx, sz = Pos(u)
    local speed = SpellInfo(u, spell, "speed")
    local travel = math.sqrt((x - sx) ^ 2 + (z - sz) ^ 2) / speed
    local ball = { alive = true, landed = false, wanted = false }
    singularity[u] = ball
    SetRecast(u, c.slot, true, 0.25)
    Missile { source = u, spell = spell, effect = "Lux_E_mis", tx = x, tz = z, speed = speed, range = math.max(1, travel * speed), width = 0 }
    ball.burst = function()
      if not ball.alive then return end
      ball.alive = false
      if singularity[u] == ball then
        singularity[u] = nil
        SetRecast(u, c.slot, false)
      end
      if ball.zone then StopEffectAt(ball.zone) end
      EffectAt(u, "Lux_E_tar_nova", x, z)
      for _, t in ipairs(Enemies(u, x, z, radius)) do
        Damage(u, t, Calc(u, spell, "TotalDamageTT"), "magic", spell)
        AddBuff(t, { name = "LuxLightStrikeKugelSlow", source = u, duration = linger, move_speed = slow })
        Effect(t, "Lux_E_tar_hit", "", 0, u)
        illuminate(u, t)
      end
    end
    -- while it lies there, enemies inside are slowed (looked at four times a second)
    local function tick()
      if not ball.alive then return end
      for _, t in ipairs(Enemies(u, x, z, radius)) do
        AddBuff(t, { name = "LuxLightStrikeKugelSlow", source = u, duration = linger, move_speed = slow })
      end
      After(0.25, tick)
    end
    After(travel, function()
      if not ball.alive then return end
      ball.landed = true
      if ball.wanted then return ball.burst() end
      ball.zone = EffectAt(u, "Lux_E_tar_aoe_green", x, z, duration)
      tick()
    end)
    After(travel + duration, ball.burst)
  end,
  OnRecast = function(c)
    local ball = singularity[c.caster]
    if not ball then return SetRecast(c.caster, c.slot, false) end
    if ball.landed then ball.burst() else ball.wanted = true end
  end,
}

-- Final Spark: Lux stands still for the cast (LuxRMis's cast time: a second), then a beam strikes every enemy in a line
-- for TotalDamage; marks of Illumination go off and are set again.
-- [documentat: the beam is 3400 long and 200 wide; the files have castRange 3500 on LuxRMis and mLineWidth 190 on LuxR,
-- neither of which is plainly the beam's]
local kFinalSparkRange, kFinalSparkWidth = 3400, 200

Spell "LuxR" {
  OnStart = function(c)
    local u = c.caster
    local ux, uz = Pos(u)
    local dx, dz = c.x - ux, c.z - uz
    local len = math.sqrt(dx * dx + dz * dz)
    if len < 1 then dx, dz, len = math.sin(Facing(u)), math.cos(Facing(u)), 1 end
    dx, dz = dx / len, dz / len
    local wait = SpellInfo(u, "LuxRMis", "cast")
    SetFacing(u, ux + dx * 100, uz + dz * 100)
    AddBuff(u, { name = "LuxRCast", source = u, duration = wait, root = true, disarm = true, silence = true })
    Effect(u, "Lux_R_cas", "", wait)
    Animate(u, "Spell4", wait + 0.5)
    -- the beam's effect holds the whole second: the thin line of the warning first, then the beam itself
    -- [dedus: it leaves from about the height of her hand (LuxRMis's mStartBoneName is R_hand)]
    EffectAt(u, "Lux_R_mis_beam", ux, uz, 0, ux + dx * kFinalSparkRange, uz + dz * kFinalSparkRange, 100)
    After(wait, function()
      if IsDead(u) then return end
      local x, z = Pos(u)
      local ex, ez = x + dx * kFinalSparkRange, z + dz * kFinalSparkRange
      for _, t in ipairs(EnemiesInLine(u, x, z, ex, ez, kFinalSparkWidth)) do
        detonate_mark(u, t)
        Damage(u, t, Calc(u, "LuxR", "TotalDamage"), "magic", "LuxR")
        Effect(t, "Lux_R_tar", "", 0, u)
        illuminate(u, t)
      end
    end)
  end,
}
