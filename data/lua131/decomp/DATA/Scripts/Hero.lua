local L0_1, L1_1
L0_1 = 500
FEAR_WANDER_DISTANCE = L0_1

function L0_1()
  local L0_2, L1_2
  L0_2 = GetPercentAttackSpeedMod
  L0_2 = L0_2()
  L0_2 = L0_2 + 1
  L0_2 = 1.6 / L0_2
  checkAttackTimer = L0_2
  L0_2 = checkAttackTimer
  if L0_2 < 0.5 then
    L0_2 = 0.5
    checkAttackTimer = L0_2
  end
  L0_2 = checkAttackTimer
  return L0_2
end

CalculateAttackTimer = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2
  L0_2 = ClearTargetPosInPos
  L0_2()
  L0_2 = SetState
  L1_2 = AI_IDLE
  L0_2(L1_2)
  L0_2 = InitTimer
  L1_2 = "TimerDistanceScan"
  L2_2 = 0.2
  L3_2 = true
  L0_2(L1_2, L2_2, L3_2)
  L0_2 = InitTimer
  L1_2 = "TimerCheckAttack"
  L2_2 = 0.2
  L3_2 = true
  L0_2(L1_2, L2_2, L3_2)
  L0_2 = InitTimer
  L1_2 = "TimerFeared"
  L2_2 = 1
  L3_2 = true
  L0_2(L1_2, L2_2, L3_2)
  L0_2 = StopTimer
  L1_2 = "TimerFeared"
  L0_2(L1_2)
  L0_2 = false
  return L0_2
end

OnInit = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetState
  L2_2 = L2_2()
  L3_2 = AI_HALTED
  if L2_2 == L3_2 then
    L3_2 = false
    return L3_2
  end
  L3_2 = AI_TAUNTED
  if L2_2 ~= L3_2 then
    L3_2 = AI_FEARED
    if L2_2 ~= L3_2 then
      L3_2 = AI_CHARMED
      if L2_2 ~= L3_2 then
        goto lbl_19
      end
    end
  end
  L3_2 = false
  do return L3_2 end
  ::lbl_19::
  L3_2 = ORDER_TAUNT
  if A0_2 == L3_2 then
    L3_2 = SetStateAndCloseToTarget
    L4_2 = AI_HARDATTACK
    L5_2 = A1_2
    L3_2(L4_2, L5_2)
    L3_2 = ClearTargetPosInPos
    L3_2()
    L3_2 = true
    return L3_2
  end
  L3_2 = ORDER_ATTACKTO
  if A0_2 == L3_2 then
    L3_2 = SetStateAndCloseToTarget
    L4_2 = AI_HARDATTACK
    L5_2 = A1_2
    L3_2(L4_2, L5_2)
    L3_2 = AssignTargetPosInPos
    L3_2()
    L3_2 = TargetInAttackRange
    L3_2 = L3_2()
    if L3_2 == true then
      L3_2 = TurnOnAutoAttack
      L4_2 = GetTarget
      L4_2, L5_2 = L4_2()
      L3_2(L4_2, L5_2)
    else
      L3_2 = TurnOffAutoAttack
      L4_2 = STOPREASON_MOVING
      L3_2(L4_2)
    end
    L3_2 = true
    return L3_2
  end
  L3_2 = ORDER_ATTACKMOVE
  if A0_2 == L3_2 then
    L3_2 = FindTargetInAcR
    L3_2 = L3_2()
    newTarget = L3_2
    L3_2 = newTarget
    if L3_2 ~= nil then
      L3_2 = SetStateAndCloseToTarget
      L4_2 = AI_SOFTATTACK
      L5_2 = newTarget
      L3_2(L4_2, L5_2)
      L3_2 = true
      return L3_2
    end
    L3_2 = SetStateAndMoveInPos
    L4_2 = AI_ATTACKMOVESTATE
    L3_2(L4_2)
    L3_2 = AssignTargetPosInPos
    L3_2()
    L3_2 = true
    return L3_2
  end
  L3_2 = ORDER_MOVETO
  if A0_2 == L3_2 then
    L3_2 = SetStateAndMoveInPos
    L4_2 = AI_MOVE
    L3_2(L4_2)
    L3_2 = AssignTargetPosInPos
    L3_2()
    L3_2 = true
    return L3_2
  end
  L3_2 = TimerCheckAttack
  L3_2()
  L3_2 = false
  return L3_2
end

OnOrder = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetState
  L2_2 = L2_2()
  L3_2 = AI_HALTED
  if L2_2 == L3_2 then
    return
  end
  L3_2 = AI_ATTACK_GOING_TO_LAST_KNOWN_LOCATION
  if L3_2 ~= L2_2 then
    L3_2 = LOST_VISIBILITY
    if A0_2 == L3_2 then
      L3_2 = AI_SOFTATTACK
      if L2_2 ~= L3_2 and A1_2 ~= nil then
        L3_2 = SetStateAndCloseToTarget
        L4_2 = AI_ATTACK_GOING_TO_LAST_KNOWN_LOCATION
        L5_2 = A1_2
        L3_2(L4_2, L5_2)
    end
    else
      L3_2 = TimerCheckAttack
      L3_2()
    end
  end
end

OnTargetLost = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2
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
    L1_2 = SetStateAndCloseToTarget
    L2_2 = AI_TAUNTED
    L3_2 = tauntTarget
    L1_2(L2_2, L3_2)
  end
end

OnTauntBegin = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2
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
    L1_2 = SetStateAndCloseToTarget
    L2_2 = AI_SOFTATTACK
    L3_2 = tauntTarget
    L1_2(L2_2, L3_2)
  else
    L1_2 = NetSetState
    L2_2 = AI_IDLE
    L1_2(L2_2)
    L1_2 = TimerDistanceScan
    L1_2()
    L1_2 = TimerCheckAttack
    L1_2()
  end
end

OnTauntEnd = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = MakeWanderPoint
  L2_2 = GetFearLeashPoint
  L2_2 = L2_2()
  L3_2 = FEAR_WANDER_DISTANCE
  L1_2 = L1_2(L2_2, L3_2)
  wanderPoint = L1_2
  L1_2 = SetStateAndMove
  L2_2 = AI_FEARED
  L3_2 = wanderPoint
  L1_2(L2_2, L3_2)
  L1_2 = TurnOffAutoAttack
  L2_2 = STOPREASON_MOVING
  L1_2(L2_2)
  L1_2 = ResetAndStartTimer
  L2_2 = "TimerFeared"
  L1_2(L2_2)
end

OnFearBegin = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = StopTimer
  L2_2 = "TimerFeared"
  L1_2(L2_2)
  L1_2 = NetSetState
  L2_2 = AI_IDLE
  L1_2(L2_2)
  L1_2 = TimerDistanceScan
  L1_2()
  L1_2 = TimerCheckAttack
  L1_2()
end

OnFearEnd = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = MakeWanderPoint
  L2_2 = GetFearLeashPoint
  L2_2 = L2_2()
  L3_2 = FEAR_WANDER_DISTANCE
  L1_2 = L1_2(L2_2, L3_2)
  wanderPoint = L1_2
  L1_2 = SetStateAndMove
  L2_2 = AI_FEARED
  L3_2 = wanderPoint
  L1_2(L2_2, L3_2)
end

TimerFeared = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = NetSetState
  L2_2 = AI_CHARMED
  L1_2(L2_2)
  L1_2 = TurnOffAutoAttack
  L2_2 = STOPREASON_IMMEDIATELY
  L1_2(L2_2)
  L1_2 = TimerCheckAttack
  L1_2()
end

OnCharmBegin = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = NetSetState
  L2_2 = AI_IDLE
  L1_2(L2_2)
  L1_2 = TimerDistanceScan
  L1_2()
  L1_2 = TimerCheckAttack
  L1_2()
end

OnCharmEnd = L0_1

function L0_1()
  local L0_2, L1_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = ClearTargetPosInPos
  L1_2()
end

OnStopMove = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2, L4_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = AI_SOFTATTACK
  if L0_2 ~= L1_2 then
    L1_2 = AI_HARDATTACK
    if L0_2 ~= L1_2 then
      L1_2 = AI_TAUNTED
      if L0_2 ~= L1_2 then
        L1_2 = AI_CHARMED
        if L0_2 ~= L1_2 then
          goto lbl_96
        end
      end
    end
  end
  L1_2 = IsTargetLost
  L1_2 = L1_2()
  if L1_2 ~= true then
    L1_2 = GetTarget
    L1_2 = L1_2()
    if L1_2 ~= nil then
      goto lbl_78
    end
  end
  L1_2 = LastAutoAttackFinished
  L1_2 = L1_2()
  if L1_2 == false then
    L1_2 = InitTimer
    L2_2 = "TimerCheckAttack"
    L3_2 = 0.1
    L4_2 = true
    L1_2(L2_2, L3_2, L4_2)
    L1_2 = false
    return L1_2
  end
  L1_2 = FindTargetInAcR
  L1_2 = L1_2()
  newTarget = L1_2
  L1_2 = newTarget
  if L1_2 ~= nil then
    L1_2 = AI_CHARMED
    if L0_2 == L1_2 then
      L1_2 = SetStateAndCloseToTarget
      L2_2 = AI_CHARMED
      L3_2 = newTarget
      L1_2(L2_2, L3_2)
    else
      L1_2 = CanSeeMe
      L2_2 = newTarget
      L1_2 = L1_2(L2_2)
      if L1_2 then
        L1_2 = SetStateAndCloseToTarget
        L2_2 = AI_SOFTATTACK
        L3_2 = newTarget
        L1_2(L2_2, L3_2)
      end
    end
    L1_2 = true
    return L1_2
  else
    L1_2 = AI_CHARMED
    if L0_2 == L1_2 then
      L1_2 = SpellBuffRemoveType
      L2_2 = me
      L3_2 = BUFF_Taunt
      L1_2(L2_2, L3_2)
    end
    L1_2 = NetSetState
    L2_2 = AI_STANDING
    L1_2(L2_2)
    L1_2 = true
    return L1_2
  end
  L1_2 = true
  do return L1_2 end
  ::lbl_78::
  L1_2 = TargetInAttackRange
  L1_2 = L1_2()
  if L1_2 == true then
    L1_2 = TurnOnAutoAttack
    L2_2 = GetTarget
    L2_2, L3_2, L4_2 = L2_2()
    L1_2(L2_2, L3_2, L4_2)
    L1_2 = true
    return L1_2
  end
  L1_2 = TargetInCancelAttackRange
  L1_2 = L1_2()
  if L1_2 == false then
    L1_2 = TurnOffAutoAttack
    L2_2 = STOPREASON_MOVING
    L1_2(L2_2)
    goto lbl_102
    ::lbl_96::
    L1_2 = IsMoving
    L1_2 = L1_2()
    if L1_2 then
      L1_2 = false
      return L1_2
    end
  end
  ::lbl_102::
  L1_2 = InitTimer
  L2_2 = "TimerCheckAttack"
  L3_2 = 0.1
  L4_2 = true
  L1_2(L2_2, L3_2, L4_2)
end

TimerCheckAttack = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2, L4_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 ~= L1_2 then
    L1_2 = AI_HARDIDLE
    if L0_2 ~= L1_2 then
      goto lbl_10
    end
  end
  do return end
  ::lbl_10::
  L1_2 = AI_STANDING
  if L0_2 ~= L1_2 then
    L1_2 = AI_IDLE
    if L0_2 ~= L1_2 then
      goto lbl_31
    end
  end
  L1_2 = GetTargetOrFindTargetInAcR
  L1_2 = L1_2()
  if L1_2 ~= nil then
    L2_2 = CanSeeMe
    L3_2 = L1_2
    L2_2 = L2_2(L3_2)
    if L2_2 then
      L2_2 = SetStateAndCloseToTarget
      L3_2 = AI_SOFTATTACK
      L4_2 = L1_2
      L2_2(L3_2, L4_2)
      L2_2 = true
      return L2_2
    end
  end
  ::lbl_31::
  L1_2 = AI_MOVE
  if L0_2 == L1_2 then
    L1_2 = IsMovementStopped
    L1_2 = L1_2()
    if L1_2 then
      L1_2 = GetTargetOrFindTargetInAcR
      L1_2 = L1_2()
      if L1_2 ~= nil then
        L2_2 = CanSeeMe
        L3_2 = L1_2
        L2_2 = L2_2(L3_2)
        if L2_2 then
          L2_2 = SetStateAndCloseToTarget
          L3_2 = AI_SOFTATTACK
          L4_2 = L1_2
          L2_2(L3_2, L4_2)
          L2_2 = TurnOnAutoAttack
          L3_2 = L1_2
          L2_2(L3_2)
          L2_2 = true
          return L2_2
        end
      end
      L2_2 = NetSetState
      L3_2 = AI_IDLE
      L2_2(L3_2)
      L2_2 = false
      return L2_2
    end
  end
  L1_2 = AI_ATTACKMOVESTATE
  if L0_2 == L1_2 then
    L1_2 = GetTargetOrFindTargetInAcR
    L1_2 = L1_2()
    if L1_2 ~= nil then
      L2_2 = SetStateAndCloseToTarget
      L3_2 = AI_SOFTATTACK
      L4_2 = L1_2
      L2_2(L3_2, L4_2)
      L2_2 = true
      return L2_2
    else
      L2_2 = DistanceBetweenObjectAndTargetPosSq
      L3_2 = me
      L2_2 = L2_2(L3_2)
      if L2_2 <= 100 then
        L2_2 = NetSetState
        L3_2 = AI_STANDING
        L2_2(L3_2)
        L2_2 = ClearTargetPosInPos
        L2_2()
        L2_2 = true
        return L2_2
      end
    end
  end
  L1_2 = AI_ATTACK_GOING_TO_LAST_KNOWN_LOCATION
  if L0_2 == L1_2 then
    L1_2 = GetLostTargetIfVisible
    L1_2 = L1_2()
    if L1_2 ~= nil then
      L2_2 = SetStateAndCloseToTarget
      L3_2 = AI_HARDATTACK
      L4_2 = L1_2
      L2_2(L3_2, L4_2)
    end
  end
end

TimerDistanceScan = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = GetState
  L2_2 = L2_2()
  L3_2 = AI_HALTED
  if L2_2 == L3_2 then
    return
  end
  L3_2 = Say
  L4_2 = A0_2
  L3_2(L4_2)
end

OnAICommand = L0_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = GetState
  L0_2 = L0_2()
  L1_2 = AI_HALTED
  if L0_2 == L1_2 then
    return
  end
  L1_2 = NetSetState
  L2_2 = AI_IDLE
  L1_2(L2_2)
  L1_2 = TimerDistanceScan
  L1_2()
  L1_2 = TimerCheckAttack
  L1_2()
end

OnReachedDestinationForGoingToLastLocation = L0_1

function L0_1()
  local L0_2, L1_2
  L0_2 = StopTimer
  L1_2 = "TimerDistanceScan"
  L0_2(L1_2)
  L0_2 = StopTimer
  L1_2 = "TimerCheckAttack"
  L0_2(L1_2)
  L0_2 = StopTimer
  L1_2 = "TimerFeared"
  L0_2(L1_2)
  L0_2 = TurnOffAutoAttack
  L1_2 = STOPREASON_IMMEDIATELY
  L0_2(L1_2)
  L0_2 = NetSetState
  L1_2 = AI_HALTED
  L0_2(L1_2)
end

HaltAI = L0_1
