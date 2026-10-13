local L0_1, L1_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2
  L0_2 = SetState
  L1_2 = AI_HARDIDLE
  L0_2(L1_2)
  L0_2 = InitTimer
  L1_2 = "TimerFindEnemies"
  L2_2 = 0.15
  L3_2 = true
  L0_2(L1_2, L2_2, L3_2)
  L0_2 = false
  return L0_2
end

OnInit = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = FindTargetInAcR
  L1_2 = L1_2()
  newTarget = L1_2
  L1_2 = newTarget
  if L1_2 == nil then
    L1_2 = AI_HARDIDLE_ATTACKING
    if L0_2 ~= L1_2 then
      L1_2 = AI_TAUNTED
    end
    if L0_2 == L1_2 then
      L1_2 = NetSetState
      L2_2 = AI_HARDIDLE
      L1_2(L2_2)
      L1_2 = true
      return L1_2
    end
  else
    L1_2 = AI_HARDIDLE_ATTACKING
    if L0_2 ~= L1_2 then
      L1_2 = AI_TAUNTED
      if L0_2 ~= L1_2 then
        goto lbl_39
      end
    end
    L1_2 = NetSetState
    L2_2 = AI_HARDIDLE_ATTACKING
    L1_2(L2_2)
    L1_2 = SetTarget
    L2_2 = newTarget
    L1_2(L2_2)
    L1_2 = true
    return L1_2
  end
  ::lbl_39::
  L1_2 = NetSetState
  L2_2 = AI_HARDIDLE
  L1_2(L2_2)
  L1_2 = true
  return L1_2
end

OnTargetLost = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = GetState
  L2_2 = L2_2()
  L3_2 = AI_HALTED
  if L2_2 == L3_2 then
    return
  end
  if A1_2 then
    L3_2 = AI_HARDIDLE
    if L2_2 ~= L3_2 then
      L3_2 = AI_HARDIDLE_ATTACKING
      if L2_2 ~= L3_2 then
        goto lbl_21
      end
    end
    L3_2 = NetSetState
    L4_2 = AI_HARDIDLE_ATTACKING
    L3_2(L4_2)
    L3_2 = SetTarget
    L4_2 = A1_2
    L3_2(L4_2)
  end
  ::lbl_21::
end

OnCallForHelp = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = GetTauntTarget
  L1_2 = L1_2()
  tauntTarget = L1_2
  L1_2 = tauntTarget
  if L1_2 ~= nil then
    L1_2 = NetSetState
    L2_2 = AI_TAUNTED
    L1_2(L2_2)
    L1_2 = SetTarget
    L2_2 = tauntTarget
    L1_2(L2_2)
  end
end

OnTauntBegin = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = GetTauntTarget
  L1_2 = L1_2()
  tauntTarget = L1_2
  L1_2 = tauntTarget
  if L1_2 ~= nil then
    L1_2 = NetSetState
    L2_2 = AI_HARDIDLE_ATTACKING
    L1_2(L2_2)
    L1_2 = SetTarget
    L2_2 = tauntTarget
    L1_2(L2_2)
  else
    L1_2 = NetSetState
    L2_2 = AI_HARDIDLE
    L1_2(L2_2)
    L1_2 = TimerFindEnemies
    L1_2()
  end
end

OnTauntEnd = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = NetSetState
  L2_2 = AI_HARDIDLE
  L1_2(L2_2)
  L1_2 = TimerFindEnemies
  L1_2()
end

OnCanMove = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = NetSetState
  L2_2 = AI_HARDIDLE
  L1_2(L2_2)
  L1_2 = TimerFindEnemies
  L1_2()
end

OnCanAttack = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = AI_HARDIDLE
  if L0_2 == L1_2 then
    L1_2 = FindTargetInAcR
    L1_2 = L1_2()
    newTarget = L1_2
    L1_2 = newTarget
    if L1_2 == nil then
      L1_2 = TurnOffAutoAttack
      L2_2 = STOPREASON_TARGET_LOST
      L1_2(L2_2)
      return
    end
    L1_2 = AI_HARDIDLE
    if L0_2 == L1_2 then
      L1_2 = NetSetState
      L2_2 = AI_HARDIDLE_ATTACKING
      L1_2(L2_2)
      L1_2 = SetTarget
      L2_2 = newTarget
      L1_2(L2_2)
    end
  end
  L1_2 = AI_HARDIDLE_ATTACKING
  if L0_2 ~= L1_2 then
    L1_2 = AI_TAUNTED
    if L0_2 ~= L1_2 then
      goto lbl_50
    end
  end
  L1_2 = TargetInAttackRange
  L1_2 = L1_2()
  if L1_2 then
    L1_2 = TurnOnAutoAttack
    L2_2 = GetTarget
    L2_2 = L2_2()
    L1_2(L2_2)
  else
    L1_2 = NetSetState
    L2_2 = AI_HARDIDLE
    L1_2(L2_2)
    L1_2 = TurnOffAutoAttack
    L2_2 = STOPREASON_MOVING
    L1_2(L2_2)
  end
  ::lbl_50::
end

TimerFindEnemies = L0_1

function L0_1()
  local L0_2, L1_2
  L0_2 = StopTimer
  L1_2 = "TimerFindEnemies"
  L0_2(L1_2)
  L0_2 = TurnOffAutoAttack
  L1_2 = STOPREASON_IMMEDIATELY
  L0_2(L1_2)
  L0_2 = NetSetState
  L1_2 = AI_HALTED
  L0_2(L1_2)
end

HaltAI = L0_1
