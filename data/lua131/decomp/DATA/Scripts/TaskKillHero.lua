local L0_1, L1_1
L0_1 = GetAttackRange
L0_1 = L0_1()
HERO_FIGHT_DIST = L0_1
L0_1 = GetAttackRange
L0_1 = L0_1()
L0_1 = L0_1 + 500
HERO_ENGAGE_DIST = L0_1
L0_1 = 0
AI_FOLLOW_HERO = L0_1
L0_1 = 1
AI_ATTACK_HERO = L0_1
L0_1 = 0
TargetHealth = L0_1
L0_1 = false
ReducePriority = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2, L4_2, L5_2
  A0_2.Priority = 0
  L1_2 = math
  L1_2 = L1_2.max
  L2_2 = GetDist
  L3_2 = GetPos
  L3_2 = L3_2()
  L4_2 = GetPos
  L5_2 = A0_2.HeroID
  L4_2, L5_2 = L4_2(L5_2)
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = 1
  L1_2 = L1_2(L2_2, L3_2)
  L2_2 = ReducePriority
  if L2_2 == true then
    A0_2.Priority = 0
    return
  end
  L2_2 = IsDead
  L3_2 = A0_2.HeroID
  L2_2 = L2_2(L3_2)
  if not L2_2 then
    L2_2 = HERO_ENGAGE_DIST
    if L1_2 < L2_2 then
      A0_2.Priority = 0.5
    else
      L2_2 = HERO_ENGAGE_DIST
      L2_2 = L2_2 * 2
      if L1_2 < L2_2 then
        L2_2 = HERO_ENGAGE_DIST
        L2_2 = L1_2 - L2_2
        L3_2 = HERO_ENGAGE_DIST
        L2_2 = L2_2 / L3_2
        L2_2 = 1 - L2_2
        L2_2 = 0.5 * L2_2
        A0_2.Priority = L2_2
      end
    end
  end
end

UpdatePriority = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2, L4_2
  L1_2 = TurnOffAutoAttack
  L2_2 = STOPREASON_MOVING
  L1_2(L2_2)
  L1_2 = SetStateAndCloseToTarget
  L2_2 = AI_FOLLOW_HERO
  L3_2 = A0_2.HeroID
  L1_2(L2_2, L3_2)
  L1_2 = GetTargetHealth
  L1_2 = L1_2()
  TargetHealth = L1_2
  L1_2 = InitTimer
  L2_2 = "AntiKiteTimer"
  L3_2 = 2
  L4_2 = true
  L1_2(L2_2, L3_2, L4_2)
end

BeginTask = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2, L4_2, L5_2
  L1_2 = GetState
  L1_2 = L1_2()
  L2_2 = GetDist
  L3_2 = GetPos
  L3_2 = L3_2()
  L4_2 = GetPos
  L5_2 = A0_2.HeroID
  L4_2, L5_2 = L4_2(L5_2)
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = AI_FOLLOW_HERO
  if L1_2 == L3_2 then
    L3_2 = HERO_FIGHT_DIST
    if L2_2 < L3_2 then
      L3_2 = SetStateAndCloseToTarget
      L4_2 = AI_ATTACK_HERO
      L5_2 = A0_2.HeroID
      L3_2(L4_2, L5_2)
    else
      L3_2 = SetStateAndCloseToTarget
      L4_2 = AI_FOLLOW_HERO
      L5_2 = A0_2.HeroID
      L3_2(L4_2, L5_2)
    end
  else
    L3_2 = AI_ATTACK_HERO
    if L1_2 == L3_2 then
      L3_2 = HERO_FIGHT_DIST
      if L2_2 < L3_2 then
        L3_2 = TurnOnAutoAttack
        L4_2 = A0_2.HeroID
        L3_2(L4_2)
      else
        L3_2 = TurnOffAutoAttack
        L4_2 = STOPREASON_MOVING
        L3_2(L4_2)
        L3_2 = SetStateAndCloseToTarget
        L4_2 = AI_FOLLOW_HERO
        L5_2 = A0_2.HeroID
        L3_2(L4_2, L5_2)
      end
    end
  end
end

Tick = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = GetTargetHealth
  L1_2 = L1_2()
  L2_2 = TargetHealth
  L2_2 = L2_2 - 10
  if L1_2 >= L2_2 then
    L1_2 = IsMoving
    L1_2 = L1_2()
    if L1_2 then
      L1_2 = true
      ReducePriority = L1_2
      L1_2 = GetTargetHealth
      L1_2 = L1_2()
      TargetHealth = L1_2
      return
    end
  end
  L1_2 = ReducePriority
  if L1_2 == true then
    L1_2 = false
    ReducePriority = L1_2
    L1_2 = GetTargetHealth
    L1_2 = L1_2()
    TargetHealth = L1_2
    return
  end
  L1_2 = GetTargetHealth
  L1_2 = L1_2()
  TargetHealth = L1_2
end

AntiKiteTimer = L0_1

function L0_1(A0_2)
  local L1_2
end

OnTargetLost = L0_1
