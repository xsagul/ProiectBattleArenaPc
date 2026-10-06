-- Garen. The numbers are his spells' own data (Value: mDataValues, Calc: mSpellCalculations); what each spell does is
-- the documented behaviour as of patch 14.1 (LoL Wiki, January 2024). Effect keys are those of his skin's
-- ResourceResolver, picked by their names.

-- Perseverance: out of combat with anything but minions for DamageTimer seconds, Garen regenerates a share of his
-- maximum health every 5 seconds (the passive's calculation: 1.5% at level 1 to 10.1% at 18).
local garen_w_stacks = {}

Champion "Garen" {
  OnKill = function(u, target, is_champion)
    if Rank(u, 1) > 0 then
      local s = garen_w_stacks[u] or 0
      if s < 30.0 then
        local gain = is_champion and 1.0 or 0.2
        s = math.min(30.0, s + gain)
        garen_w_stacks[u] = s
        local at_max = (s >= 30.0)
        AddBuff(u, {
          name = "GarenWPassive",
          source = u,
          armor = s,
          mr = s,
          armor_pct = at_max and 0.10 or 0,
          mr_pct = at_max and 0.10 or 0,
        })
      end
    end
  end,
  OnTick = function(u)
    if SinceHurt(u) < Value(u, "GarenPassive", "DamageTimer") then return end
    if HP(u) >= MaxHP(u) then return end
    -- RegenCalc is the share for 5 seconds; this runs four times a second
    Heal(u, MaxHP(u) * Calc(u, "GarenPassive", "RegenCalc") / 5 / 4)
  end,
}

-- Decisive Strike: Garen sheds every slow and runs faster for a while; his next attack within AttackWindow seconds
-- deals TotalDamage in place of its own and silences the target. The attack timer starts over.
Spell "GarenQ" {
  OnCast = function(c)
    local u = c.caster
    RemoveSlows(u)
    AddBuff(u, { name = "GarenQHaste", source = u, duration = Value(u, "GarenQ", "MovementSpeedDuration"), move_speed = Value(u, "GarenQ", "MovementSpeedAmount") })
    Effect(u, "Garen_Q_Cas")
    Effect(u, "Garen_Q_Cas_Sword", "BUFFBONE_WEAPON_1", Value(u, "GarenQ", "AttackWindow"))
    ResetAttack(u)
    AddBuff(u, {
      name = "GarenQ", source = u, duration = Value(u, "GarenQ", "AttackWindow"),
      on_attack = function(target)
        -- the whole of TotalDamage replaces the attack's own damage: the bonus is what it adds over one attack
        local bonus = Calc(u, "GarenQ", "TotalDamage") - Stat(u, "ad")
        AddBuff(target, { name = "GarenQSilence", source = u, duration = Value(u, "GarenQ", "SilenceDuration"), silence = true })
        Effect(target, "Garen_Q_Tar", "", 0, u)
        StopEffect(u, "Garen_Q_Cas_Sword")
        return bonus, true
      end,
      on_expire = function() StopEffect(u, "Garen_Q_Cas_Sword") end,
    })
  end,
}

-- Courage: for DRDuration seconds Garen takes DRPercent less damage; for the first UpfrontDuration he also has a
-- shield (ShieldBase plus a share of his bonus health). The passive resistances from kills are not counted yet.
Spell "GarenW" {
  OnCast = function(c)
    local u = c.caster
    AddBuff(u, { name = "GarenW", source = u, duration = Value(u, "GarenW", "DRDuration"), damage_taken = -Value(u, "GarenW", "DRPercent") })
    AddBuff(u, { name = "GarenWShield", source = u, duration = Value(u, "GarenW", "UpfrontDuration"), shield = Calc(u, "GarenW", "TotalShield"), tenacity = Value(u, "GarenW", "UpfrontTenacity") })
    Effect(u, "Garen_W_Cas")
    Effect(u, "Garen_W_Buff", "", Value(u, "GarenW", "DRDuration"))
  end,
}

-- Judgment: Garen spins for Duration seconds, striking NumberOfStrikes times (more with bonus attack speed) everything
-- within 325 units for TotalDamage; the nearest enemy takes TotalDamageNearest. He cannot attack while spinning; casting
-- again stops it. The cooldown runs from the cast; the time not spun comes off it.
local kJudgmentRadius = 325  -- documented: the data carries no radius for it

Spell "GarenE" {
  OnCast = function(c)
    local u = c.caster
    if HasBuff(u, "GarenE") then
      RemoveBuff(u, "GarenE")
      return
    end
    local duration = Value(u, "GarenE", "Duration")
    local ticks = math.max(1, math.floor(Calc(u, "GarenE", "NumberOfStrikes")))
    local cooldown = Cooldown(u, c.slot)
    local started = Now()
    local spinning = true
    SetCooldown(u, c.slot, 0.5)  -- it may be cast again to stop
    Animate(u, "Spell3", duration)
    Effect(u, "Garen_E_Spin", "", duration)
    AddBuff(u, {
      name = "GarenE", source = u, duration = duration, disarm = true,
      on_expire = function()
        spinning = false
        StopEffect(u, "Garen_E_Spin")
        Animate(u, "", 0)
        SetCooldown(u, c.slot, math.max(0.5, cooldown - (Now() - started)))
      end,
    })
    local shred_hits = {}
    local function strike()
      if not spinning or IsDead(u) then return end
      local x, z = Pos(u)
      local hit = Enemies(u, x, z, kJudgmentRadius)
      for i, t in ipairs(hit) do
        local dmg = Calc(u, "GarenE", "TotalDamage")
        if i == 1 then dmg = dmg * (1.0 + Value(u, "GarenE", "NearestEnemyBonus")) end
        Damage(u, t, dmg, "physical", "GarenE")
        Effect(t, "Garen_E_Tar", "", 0, u)
        local count = (shred_hits[t] or 0) + 1
        shred_hits[t] = count
        if count == 6 then
          AddBuff(t, { name = "GarenEShred", source = u, duration = 6.0, armor_pct = -0.25 })
          Effect(t, "Garen_E_ArmorShred", "", 6.0, u)
        end
      end
    end
    for i = 0, ticks - 1 do After(duration * i / ticks, strike) end
  end,
}

-- Demacian Justice: true damage to an enemy champion: BaseDamage plus ExecuteDamage of the health it is missing.
Spell "GarenR" {
  OnCast = function(c)
    local u, t = c.caster, c.target
    if not t or IsDead(t) then return end
    Effect(t, "Garen_R_Tar_Impact", "", 0, u)
    local missing = MaxHP(t) - HP(t)
    Damage(u, t, Value(u, "GarenR", "BaseDamage") + Value(u, "GarenR", "ExecuteDamage") * missing, "true", "GarenR")
  end,
}
