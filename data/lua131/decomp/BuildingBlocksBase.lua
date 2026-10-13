local L0_1, L1_1
L0_1 = -1
gCurrentBuildingBlockNumber = L0_1
L0_1 = ""
gCurrentBuildingBlockString = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  if A0_2 ~= nil then
    L2_2 = gCurrentBuildingBlockString
    A1_2.___BreakExecution___ = false
    L3_2 = 1
    L4_2 = #A0_2
    L5_2 = 1
    for L6_2 = L3_2, L4_2, L5_2 do
      L7_2 = A1_2.___BreakExecution___
      if false == L7_2 then
        gCurrentBuildingBlockNumber = L6_2
        L7_2 = L2_2
        L8_2 = "."
        L9_2 = gCurrentBuildingBlockNumber
        L7_2 = L7_2 .. L8_2 .. L9_2
        gCurrentBuildingBlockString = L7_2
        L7_2 = gCurrentBuildingBlockNumber
        L7_2 = A0_2[L7_2]
        gCurrentBuildingBlock = L7_2
        L7_2 = gCurrentBuildingBlock
        L7_2 = L7_2.Function
        L8_2 = A1_2
        L9_2 = gCurrentBuildingBlock
        L9_2 = L9_2.Params
        L10_2 = gCurrentBuildingBlock
        L10_2 = L10_2.SubBlocks
        L7_2(L8_2, L9_2, L10_2)
      end
    end
    gCurrentBuildingBlockString = L2_2
    L3_2 = -1
    gCurrentBuildingBlockNumber = L3_2
    L3_2 = nil
    gCurrentBuildingBlock = L3_2
  end
end

ExecuteBuildingBlocks = L0_1

function L0_1()
  local L0_2, L1_2
end

BBRequireVar = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = A1_2.IsConditionTrue
  L4_2 = A0_2
  L3_2 = L3_2(L4_2)
  if L3_2 then
    L3_2 = ExecuteBuildingBlocks
    L4_2 = A2_2
    L5_2 = A0_2
    L3_2(L4_2, L5_2)
  end
end

BBConditionallyExecute = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2
  if A1_2 ~= nil then
    L3_2 = A0_2[A1_2]
    if L3_2 == nil and A2_2 then
      L4_2 = {}
      A0_2[A1_2] = L4_2
      L4_2 = A0_2[A1_2]
      return L4_2
    end
  end
  if L3_2 == nil then
    L3_2 = A0_2
  end
  return L3_2
end

GetTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A0_2.Level
  if L3_2 ~= nil then
    L3_2 = A1_2.SrcValueByLevel
    if L3_2 ~= nil then
      L3_2 = A1_2.DestVar
      L4_2 = A1_2.SrcValueByLevel
      L5_2 = A0_2.Level
      L4_2 = L4_2[L5_2]
      L2_2[L3_2] = L4_2
  end
  else
    L3_2 = GetTable
    L4_2 = A0_2
    L5_2 = A1_2.SrcVarTable
    L6_2 = false
    L3_2 = L3_2(L4_2, L5_2, L6_2)
    L4_2 = A1_2.SrcVar
    if L4_2 ~= nil and L3_2 ~= nil then
      L4_2 = A1_2.DestVar
      L5_2 = A1_2.SrcVar
      L5_2 = L3_2[L5_2]
      L2_2[L4_2] = L5_2
    else
      L4_2 = A1_2.DestVar
      L5_2 = A1_2.SrcValue
      L2_2[L4_2] = L5_2
    end
  end
end

BBSetVarInTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = nil
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.SpellSlotVarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.SpellSlotVar
  if L5_2 ~= nil and L4_2 ~= nil then
    L5_2 = A1_2.SpellSlotVar
    L3_2 = L4_2[L5_2]
  else
    L3_2 = A1_2.SpellSlotValue
  end
  L5_2 = A1_2.DestVar
  L6_2 = A1_2.Function
  L7_2 = A1_2.OwnerVar
  L7_2 = A0_2[L7_2]
  L8_2 = L3_2
  L9_2 = A1_2.SpellbookType
  L10_2 = A1_2.SlotType
  L6_2 = L6_2(L7_2, L8_2, L9_2, L10_2)
  L2_2[L5_2] = L6_2
end

BBGetSlotSpellInfo = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.SrcVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = nil
  L4_2 = A1_2.SrcVar
  if L4_2 ~= nil and L2_2 ~= nil then
    L4_2 = A1_2.SrcVar
    L3_2 = L2_2[L4_2]
  else
    L3_2 = A1_2.SrcValue
  end
  L4_2 = nil
  L5_2 = GetTable
  L6_2 = A0_2
  L7_2 = A1_2.SpellSlotVarTable
  L8_2 = false
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L6_2 = A1_2.SpellSlotVar
  if L6_2 ~= nil and L5_2 ~= nil then
    L6_2 = A1_2.SpellSlotVar
    L4_2 = L5_2[L6_2]
  else
    L4_2 = A1_2.SpellSlotValue
  end
  L6_2 = SetSlotSpellCooldownTime
  L7_2 = A1_2.OwnerVar
  L7_2 = A0_2[L7_2]
  L8_2 = L4_2
  L9_2 = A1_2.SpellbookType
  L10_2 = A1_2.SlotType
  L11_2 = L3_2
  L6_2(L7_2, L8_2, L9_2, L10_2, L11_2)
end

BBSetSlotSpellCooldownTime = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = A0_2.Level
  if L2_2 ~= nil then
    L2_2 = A1_2.SrcValueByLevel
    if L2_2 ~= nil then
      L2_2 = A1_2.SrcValueByLevel
      L3_2 = A0_2.Level
      L2_2 = L2_2[L3_2]
      A0_2.ReturnValue = L2_2
  end
  else
    L2_2 = GetTable
    L3_2 = A0_2
    L4_2 = A1_2.SrcVarTable
    L5_2 = false
    L2_2 = L2_2(L3_2, L4_2, L5_2)
    L3_2 = A1_2.SrcVar
    if L3_2 ~= nil and L2_2 ~= nil then
      L3_2 = A1_2.SrcVar
      L3_2 = L2_2[L3_2]
      A0_2.ReturnValue = L3_2
    else
      L3_2 = A1_2.SrcValue
      A0_2.ReturnValue = L3_2
    end
  end
end

BBSetReturnValue = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2
  L2_2 = type
  L3_2 = A0_2
  L2_2 = L2_2(L3_2)
  if L2_2 == "string" then
    L2_2 = type
    L3_2 = A1_2
    L2_2 = L2_2(L3_2)
    if L2_2 == "string" then
      L2_2 = string
      L2_2 = L2_2.lower
      L3_2 = A0_2
      L2_2 = L2_2(L3_2)
      A0_2 = L2_2
      L2_2 = string
      L2_2 = L2_2.lower
      L3_2 = A1_2
      L2_2 = L2_2(L3_2)
      A1_2 = L2_2
    end
  end
  L2_2 = A0_2 == A1_2
  return L2_2
end

CO_EQUAL = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2
  L2_2 = type
  L3_2 = A0_2
  L2_2 = L2_2(L3_2)
  if L2_2 == "string" then
    L2_2 = type
    L3_2 = A1_2
    L2_2 = L2_2(L3_2)
    if L2_2 == "string" then
      L2_2 = string
      L2_2 = L2_2.lower
      L3_2 = A0_2
      L2_2 = L2_2(L3_2)
      A0_2 = L2_2
      L2_2 = string
      L2_2 = L2_2.lower
      L3_2 = A1_2
      L2_2 = L2_2(L3_2)
      A1_2 = L2_2
    end
  end
  L2_2 = A0_2 ~= A1_2
  return L2_2
end

CO_NOT_EQUAL = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 < A1_2
  return L2_2
end

CO_LESS_THAN = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A1_2 < A0_2
  return L2_2
end

CO_GREATER_THAN = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 <= A1_2
  return L2_2
end

CO_LESS_THAN_OR_EQUAL = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A1_2 <= A0_2
  return L2_2
end

CO_GREATER_THAN_OR_EQUAL = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = GetTeamID
  L3_2 = A0_2
  L2_2 = L2_2(L3_2)
  L3_2 = GetTeamID
  L4_2 = A1_2
  L3_2 = L3_2(L4_2)
  L2_2 = L2_2 == L3_2
  return L2_2
end

CO_SAME_TEAM = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = GetTeamID
  L3_2 = A0_2
  L2_2 = L2_2(L3_2)
  L3_2 = GetTeamID
  L4_2 = A1_2
  L3_2 = L3_2(L4_2)
  L2_2 = L2_2 ~= L3_2
  return L2_2
end

CO_DIFFERENT_TEAM = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = GetSourceType
  L2_2 = L2_2()
  L2_2 = L2_2 == A1_2
  return L2_2
end

CO_DAMAGE_SOURCETYPE_IS = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = GetSourceType
  L2_2 = L2_2()
  L2_2 = L2_2 ~= A1_2
  return L2_2
end

CO_DAMAGE_SOURCETYPE_IS_NOT = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsObjectAI
  L2_2 = A0_2
  return L1_2(L2_2)
end

CO_IS_TYPE_AI = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsObjectAI
  L2_2 = A0_2
  L1_2 = L1_2(L2_2)
  L1_2 = L1_2 ~= true
  return L1_2
end

CO_IS_NOT_AI = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsObjectHero
  L2_2 = A0_2
  return L1_2(L2_2)
end

CO_IS_TYPE_HERO = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsObjectHero
  L2_2 = A0_2
  L1_2 = L1_2(L2_2)
  L1_2 = L1_2 ~= true
  return L1_2
end

CO_IS_NOT_HERO = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsMelee
  L2_2 = A0_2
  return L1_2(L2_2)
end

CO_IS_MELEE = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsMelee
  L2_2 = A0_2
  L1_2 = L1_2(L2_2)
  L1_2 = L1_2 ~= true
  return L1_2
end

CO_IS_RANGED = L0_1

function L0_1(A0_2)
  local L1_2
  L1_2 = math
  L1_2 = L1_2.random
  L1_2 = L1_2()
  L1_2 = A0_2 > L1_2
  return L1_2
end

CO_RANDOM_CHANCE_LESS_THAN = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsTurretAI
  L2_2 = A0_2
  return L1_2(L2_2)
end

CO_IS_TYPE_TURRET = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsTurretAI
  L2_2 = A0_2
  L1_2 = L1_2(L2_2)
  L1_2 = L1_2 ~= true
  return L1_2
end

CO_IS_NOT_TURRET = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsDead
  L2_2 = A0_2
  return L1_2(L2_2)
end

CO_IS_DEAD = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = IsDead
  L2_2 = A0_2
  L1_2 = L1_2(L2_2)
  L1_2 = L1_2 ~= true
  return L1_2
end

CO_IS_NOT_DEAD = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = BBIsTargetInFrontOfMe
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

CO_IS_TARGET_IN_FRONT_OF_ME = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = BBIsTargetBehindMe
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

CO_IS_TARGET_BEHIND_ME = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.Src1VarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.Src2VarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = false
  L6_2 = nil
  if L3_2 ~= nil then
    L7_2 = A1_2.Src1Var
    if L7_2 ~= nil then
      L7_2 = A1_2.Src1Var
      L6_2 = L3_2[L7_2]
  end
  else
    L6_2 = A1_2.Value1
  end
  if L4_2 ~= nil then
    L7_2 = A1_2.Src2Var
    if L7_2 ~= nil then
      L7_2 = A1_2.CompareOp
      L8_2 = L6_2
      L9_2 = A1_2.Src2Var
      L9_2 = L4_2[L9_2]
      L7_2 = L7_2(L8_2, L9_2)
      L5_2 = L7_2
  end
  else
    L7_2 = A1_2.CompareOp
    L8_2 = L6_2
    L9_2 = A1_2.Value2
    L7_2 = L7_2(L8_2, L9_2)
    L5_2 = L7_2
  end
  if L5_2 then
    L7_2 = ExecuteBuildingBlocks
    L8_2 = A2_2
    L9_2 = A0_2
    L7_2(L8_2, L9_2)
    A0_2.LastIfSucceeded = true
  else
    A0_2.LastIfSucceeded = false
  end
end

BBIf = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = A0_2.LastIfSucceeded
  if L3_2 == false then
    L3_2 = ExecuteBuildingBlocks
    L4_2 = A2_2
    L5_2 = A0_2
    L3_2(L4_2, L5_2)
    A0_2.LastIfSucceeded = true
  end
end

BBElse = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L3_2 = A0_2.LastIfSucceeded
  if L3_2 == false then
    L3_2 = GetTable
    L4_2 = A0_2
    L5_2 = A1_2.Src1VarTable
    L6_2 = false
    L3_2 = L3_2(L4_2, L5_2, L6_2)
    L4_2 = GetTable
    L5_2 = A0_2
    L6_2 = A1_2.Src2VarTable
    L7_2 = false
    L4_2 = L4_2(L5_2, L6_2, L7_2)
    L5_2 = false
    L6_2 = nil
    if L3_2 ~= nil then
      L7_2 = A1_2.Src1Var
      if L7_2 ~= nil then
        L7_2 = A1_2.Src1Var
        L6_2 = L3_2[L7_2]
    end
    else
      L6_2 = A1_2.Value1
    end
    if L4_2 ~= nil then
      L7_2 = A1_2.Src2Var
      if L7_2 ~= nil then
        L7_2 = A1_2.CompareOp
        L8_2 = L6_2
        L9_2 = A1_2.Src2Var
        L9_2 = L4_2[L9_2]
        L7_2 = L7_2(L8_2, L9_2)
        L5_2 = L7_2
    end
    else
      L7_2 = A1_2.CompareOp
      L8_2 = L6_2
      L9_2 = A1_2.Value2
      L7_2 = L7_2(L8_2, L9_2)
      L5_2 = L7_2
    end
    if L5_2 then
      L7_2 = ExecuteBuildingBlocks
      L8_2 = A2_2
      L9_2 = A0_2
      L7_2(L8_2, L9_2)
      A0_2.LastIfSucceeded = true
    else
      A0_2.LastIfSucceeded = false
    end
  end
end

BBElseIf = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2
  L4_2 = A1_2.TargetVar
  if L4_2 ~= nil then
    L4_2 = A1_2.TargetVar
    L3_2 = A0_2[L4_2]
  else
    L3_2 = A0_2.Target
  end
  L4_2 = HasBuffOfType
  L5_2 = L3_2
  L6_2 = A1_2.BuffType
  L4_2 = L4_2(L5_2, L6_2)
  if L4_2 then
    L5_2 = ExecuteBuildingBlocks
    L6_2 = A2_2
    L7_2 = A0_2
    L5_2(L6_2, L7_2)
    A0_2.LastIfSucceeded = true
  else
    A0_2.LastIfSucceeded = false
  end
end

BBIfHasBuffOfType = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L5_2 = A1_2.OwnerVar
  if L5_2 ~= nil then
    L5_2 = A1_2.OwnerVar
    L3_2 = A0_2[L5_2]
  else
    L3_2 = A0_2.Owner
  end
  L5_2 = A1_2.AttackerVar
  if L5_2 ~= nil then
    L5_2 = A1_2.AttackerVar
    L4_2 = A0_2[L5_2]
  else
    L4_2 = A0_2.Attacker
  end
  L5_2 = SpellBuffCount
  L6_2 = L3_2
  L7_2 = A1_2.BuffName
  L8_2 = L4_2
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L5_2 = 0 < L5_2
  if L5_2 then
    L6_2 = ExecuteBuildingBlocks
    L7_2 = A2_2
    L8_2 = A0_2
    L6_2(L7_2, L8_2)
    A0_2.LastIfSucceeded = true
  else
    A0_2.LastIfSucceeded = false
  end
end

BBIfHasBuff = L0_1

function L0_1(A0_2, A1_2)
  A0_2.___BreakExecution___ = true
end

BBBreakExecution = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L5_2 = A1_2.OwnerVar
  if L5_2 ~= nil then
    L5_2 = A1_2.OwnerVar
    L3_2 = A0_2[L5_2]
  else
    L3_2 = A0_2.Owner
  end
  L5_2 = A1_2.CasterVar
  if L5_2 ~= nil then
    L5_2 = A1_2.CasterVar
    L4_2 = A0_2[L5_2]
  else
    L4_2 = A0_2.Caster
  end
  L5_2 = SpellBuffCount
  L6_2 = L3_2
  L7_2 = A1_2.BuffName
  L8_2 = L4_2
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L5_2 = L5_2 <= 0
  if L5_2 then
    L6_2 = ExecuteBuildingBlocks
    L7_2 = A2_2
    L8_2 = A0_2
    L6_2(L7_2, L8_2)
    A0_2.LastIfSucceeded = true
  else
    A0_2.LastIfSucceeded = false
  end
end

BBIfNotHasBuff = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L5_2 = A1_2.OwnerVar
  if L5_2 ~= nil then
    L5_2 = A1_2.OwnerVar
    L3_2 = A0_2[L5_2]
  else
    L3_2 = A0_2.Owner
  end
  L5_2 = HasPARType
  L6_2 = L3_2
  L7_2 = A1_2.PARType
  L5_2 = L5_2(L6_2, L7_2)
  if L5_2 then
    L6_2 = ExecuteBuildingBlocks
    L7_2 = A2_2
    L8_2 = A0_2
    L6_2(L7_2, L8_2)
    A0_2.LastIfSucceeded = true
  else
    A0_2.LastIfSucceeded = false
  end
end

BBIfPARTypeEquals = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L5_2 = A1_2.OwnerVar
  if L5_2 ~= nil then
    L5_2 = A1_2.OwnerVar
    L3_2 = A0_2[L5_2]
  else
    L3_2 = A0_2.Owner
  end
  L5_2 = HasPARType
  L6_2 = L3_2
  L7_2 = A1_2.PARType
  L5_2 = L5_2(L6_2, L7_2)
  L5_2 = not L5_2
  if L5_2 then
    L6_2 = ExecuteBuildingBlocks
    L7_2 = A2_2
    L8_2 = A0_2
    L6_2(L7_2, L8_2)
    A0_2.LastIfSucceeded = true
  else
    A0_2.LastIfSucceeded = false
  end
end

BBIfPARTypeNotEquals = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.Src1VarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.Src2VarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = true
  while L5_2 do
    L6_2 = false
    L7_2 = nil
    if L3_2 ~= nil then
      L8_2 = A1_2.Src1Var
      if L8_2 ~= nil then
        L8_2 = A1_2.Src1Var
        L7_2 = L3_2[L8_2]
    end
    else
      L7_2 = A1_2.Value1
    end
    if L4_2 ~= nil then
      L8_2 = A1_2.Src2Var
      if L8_2 ~= nil then
        L8_2 = A1_2.CompareOp
        L9_2 = L7_2
        L10_2 = A1_2.Src2Var
        L10_2 = L4_2[L10_2]
        L8_2 = L8_2(L9_2, L10_2)
        L6_2 = L8_2
    end
    else
      L8_2 = A1_2.CompareOp
      L9_2 = L7_2
      L10_2 = A1_2.Value2
      L8_2 = L8_2(L9_2, L10_2)
      L6_2 = L8_2
    end
    if L6_2 then
      L8_2 = ExecuteBuildingBlocks
      L9_2 = A2_2
      L10_2 = A0_2
      L8_2(L9_2, L10_2)
    else
      L5_2 = false
    end
  end
end

BBWhile = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 * A1_2
  return L2_2
end

MO_MULTIPLY = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 + A1_2
  return L2_2
end

MO_ADD = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 - A1_2
  return L2_2
end

MO_SUBTRACT = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 / A1_2
  return L2_2
end

MO_DIVIDE = L0_1

function L0_1(A0_2, A1_2)
  if A0_2 < A1_2 then
    return A0_2
  else
    return A1_2
  end
end

MO_MIN = L0_1

function L0_1(A0_2, A1_2)
  if A1_2 < A0_2 then
    return A0_2
  else
    return A1_2
  end
end

MO_MAX = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 % A1_2
  return L2_2
end

MO_MODULO = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.floor
  L2_2 = A0_2 + 0.5
  return L1_2(L2_2)
end

MO_ROUND = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.ceil
  L2_2 = A0_2
  return L1_2(L2_2)
end

MO_ROUNDUP = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.floor
  L2_2 = A0_2
  return L1_2(L2_2)
end

MO_ROUNDDOWN = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = math
  L1_2 = L1_2.sin
  L2_2 = math
  L2_2 = L2_2.rad
  L3_2 = A0_2
  L2_2, L3_2 = L2_2(L3_2)
  return L1_2(L2_2, L3_2)
end

MO_SIN = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = math
  L1_2 = L1_2.cos
  L2_2 = math
  L2_2 = L2_2.rad
  L3_2 = A0_2
  L2_2, L3_2 = L2_2(L3_2)
  return L1_2(L2_2, L3_2)
end

MO_COSINE = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = math
  L1_2 = L1_2.tan
  L2_2 = math
  L2_2 = L2_2.rad
  L3_2 = A0_2
  L2_2, L3_2 = L2_2(L3_2)
  return L1_2(L2_2, L3_2)
end

MO_TANGENT = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = GetMathNumber
  L3_2 = A0_2
  L4_2 = A1_2.Src1VarTable
  L5_2 = A1_2.Src1Var
  L6_2 = A1_2.Src1Value
  L2_2 = L2_2(L3_2, L4_2, L5_2, L6_2)
  L3_2 = GetMathNumber
  L4_2 = A0_2
  L5_2 = A1_2.Src2VarTable
  L6_2 = A1_2.Src2Var
  L7_2 = A1_2.Src2Value
  L3_2 = L3_2(L4_2, L5_2, L6_2, L7_2)
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.DestVarTable
  L4_2 = L4_2(L5_2, L6_2)
  L5_2 = A1_2.DestVar
  L6_2 = A1_2.MathOp
  L7_2 = L2_2
  L8_2 = L3_2
  L6_2 = L6_2(L7_2, L8_2)
  L4_2[L5_2] = L6_2
end

BBMath = L0_1

function L0_1(A0_2, A1_2, A2_2, A3_2)
  local L4_2, L5_2, L6_2
  if A2_2 ~= nil then
    L4_2 = GetTable
    L5_2 = A0_2
    L6_2 = A1_2
    L4_2 = L4_2(L5_2, L6_2)
    L5_2 = L4_2[A2_2]
    if L5_2 ~= nil then
      return L5_2
    end
  end
  return A3_2
end

GetMathNumber = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = type
  L3_2 = A1_2
  L2_2 = L2_2(L3_2)
  if L2_2 == "number" then
    return A1_2
  elseif L2_2 == "function" then
    L3_2 = A1_2
    L4_2 = A0_2
    return L3_2(L4_2)
  elseif L2_2 == "string" then
    L3_2 = A0_2[A1_2]
    return L3_2
  end
end

GetNumber = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = A0_2.InstanceVars
  L3_2 = L2_2.InterpDelta
  if L3_2 == nil then
    L3_2 = A1_2.Amount
    L4_2 = A1_2.AmountVar
    if L4_2 ~= nil then
      L4_2 = GetTable
      L5_2 = A0_2
      L6_2 = A1_2.AmountVarTable
      L4_2 = L4_2(L5_2, L6_2)
      L5_2 = A1_2.AmountVar
      L3_2 = L4_2[L5_2]
    end
    L4_2 = GetPosition
    L5_2 = A1_2.TargetVar
    L5_2 = A0_2[L5_2]
    L4_2 = L4_2(L5_2)
    L2_2.KnockBackStart = L4_2
    L4_2 = GetNormalizedPositionDelta
    L5_2 = A1_2.TargetVar
    L5_2 = A0_2[L5_2]
    L6_2 = A1_2.AttackerVar
    L6_2 = A0_2[L6_2]
    L7_2 = true
    L4_2 = L4_2(L5_2, L6_2, L7_2)
    L5_2 = {}
    L6_2 = L4_2.x
    L6_2 = L6_2 * L3_2
    L5_2.x = L6_2
    L5_2.y = 0
    L6_2 = L4_2.z
    L6_2 = L6_2 * L3_2
    L5_2.z = L6_2
    L2_2.InterpDelta = L5_2
    L5_2 = GetTime
    L5_2 = L5_2()
    L2_2.StartTime = L5_2
    L5_2 = A1_2.KnockBackDuration
    L2_2.KnockBackDuration = L5_2
  end
  L3_2 = A1_2.TargetVar
  L3_2 = A0_2[L3_2]
  L4_2 = GetTime
  L4_2 = L4_2()
  L5_2 = L2_2.StartTime
  L4_2 = L4_2 - L5_2
  L5_2 = L2_2.KnockBackDuration
  L4_2 = L4_2 / L5_2
  L5_2 = {}
  L6_2 = L2_2.KnockBackStart
  L6_2 = L6_2.x
  L7_2 = L2_2.InterpDelta
  L7_2 = L7_2.x
  L7_2 = L7_2 * L4_2
  L6_2 = L6_2 + L7_2
  L5_2.x = L6_2
  L6_2 = L2_2.KnockBackStart
  L6_2 = L6_2.y
  L5_2.y = L6_2
  L6_2 = L2_2.KnockBackStart
  L6_2 = L6_2.z
  L7_2 = L2_2.InterpDelta
  L7_2 = L7_2.z
  L7_2 = L7_2 * L4_2
  L6_2 = L6_2 + L7_2
  L5_2.z = L6_2
  L6_2 = SetPosition
  L7_2 = L3_2
  L8_2 = L5_2
  L6_2(L7_2, L8_2)
end

BBKnockback = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = 0
  L3_2 = A1_2.Delta
  if L3_2 ~= nil then
    L3_2 = A1_2.Delta
    L2_2 = L2_2 + L3_2
  end
  L3_2 = A1_2.DeltaByLevel
  if L3_2 ~= nil then
    L3_2 = A0_2.Level
    if L3_2 ~= nil then
      L3_2 = A1_2.DeltaByLevel
      L4_2 = A0_2.Level
      L3_2 = L3_2[L4_2]
      L2_2 = L2_2 + L3_2
    end
  end
  L3_2 = A1_2.DeltaVar
  if L3_2 ~= nil then
    L3_2 = GetTable
    L4_2 = A0_2
    L5_2 = A1_2.DeltaVarTable
    L6_2 = true
    L3_2 = L3_2(L4_2, L5_2, L6_2)
    L4_2 = A1_2.DeltaVar
    L4_2 = L3_2[L4_2]
    L2_2 = L2_2 + L4_2
  end
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.Stat
    L5_2 = L2_2
    L6_2 = A0_2[L3_2]
    L4_2(L5_2, L6_2)
  else
    L4_2 = A1_2.Stat
    L5_2 = L2_2
    L4_2(L5_2)
  end
end

BBIncStat = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = 0
  L3_2 = A1_2.Delta
  if L3_2 ~= nil then
    L3_2 = A1_2.Delta
    L2_2 = L2_2 + L3_2
  end
  L3_2 = A1_2.DeltaByLevel
  if L3_2 ~= nil then
    L3_2 = A0_2.Level
    if L3_2 ~= nil then
      L3_2 = A1_2.DeltaByLevel
      L4_2 = A0_2.Level
      L3_2 = L3_2[L4_2]
      L2_2 = L2_2 + L3_2
    end
  end
  L3_2 = A1_2.DeltaVar
  if L3_2 ~= nil then
    L3_2 = GetTable
    L4_2 = A0_2
    L5_2 = A1_2.DeltaVarTable
    L6_2 = true
    L3_2 = L3_2(L4_2, L5_2, L6_2)
    L4_2 = A1_2.DeltaVar
    L4_2 = L3_2[L4_2]
    L2_2 = L2_2 + L4_2
  end
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.Stat
    L5_2 = L2_2
    L6_2 = A0_2[L3_2]
    L4_2(L5_2, L6_2)
  else
    L4_2 = A1_2.Stat
    L5_2 = L2_2
    L4_2(L5_2)
  end
end

BBIncPermanentStat = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.DestVar
    L5_2 = A1_2.Stat
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L2_2[L4_2] = L5_2
  else
    L4_2 = A1_2.DestVar
    L5_2 = A1_2.Stat
    L5_2 = L5_2()
    L2_2[L4_2] = L5_2
  end
end

BBGetStat = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.DestVar
    L5_2 = GetLevel
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L2_2[L4_2] = L5_2
  else
    L4_2 = A1_2.DestVar
    L5_2 = GetLevel
    L5_2 = L5_2()
    L2_2[L4_2] = L5_2
  end
end

BBGetLevel = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.DestVar
    L5_2 = GetArmor
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L2_2[L4_2] = L5_2
  else
    L4_2 = A1_2.DestVar
    L5_2 = GetArmor
    L5_2 = L5_2()
    L2_2[L4_2] = L5_2
  end
end

BBGetArmor = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.DestVar
    L5_2 = GetSpellBlock
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L2_2[L4_2] = L5_2
  else
    L4_2 = A1_2.DestVar
    L5_2 = GetSpellBlock
    L5_2 = L5_2()
    L2_2[L4_2] = L5_2
  end
end

BBGetSpellBlock = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.DestVar
    L5_2 = GetTeamID
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L2_2[L4_2] = L5_2
  else
    L4_2 = A1_2.DestVar
    L5_2 = GetTeamID
    L5_2 = L5_2()
    L2_2[L4_2] = L5_2
  end
end

BBGetTeamID = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.DestVar
    L5_2 = GetUnitSkinName
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L2_2[L4_2] = L5_2
  end
end

BBGetUnitSkinName = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = A1_2.DestVar
    L5_2 = GetTotalAttackDamage
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L2_2[L4_2] = L5_2
  else
    L4_2 = A1_2.DestVar
    L5_2 = GetTotalAttackDamage
    L5_2 = L5_2()
    L2_2[L4_2] = L5_2
  end
end

BBGetTotalAttackDamage = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.DestVar
  L4_2 = A1_2.Status
  L5_2 = A1_2.TargetVar
  L5_2 = A0_2[L5_2]
  L4_2 = L4_2(L5_2)
  L2_2[L3_2] = L4_2
end

BBGetStatus = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.DestVar
  L4_2 = A1_2.Info
  L5_2 = A1_2.TargetVar
  L5_2 = A0_2[L5_2]
  L4_2 = L4_2(L5_2)
  L2_2[L3_2] = L4_2
end

BBGetCastInfo = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2
  L2_2 = SetCanCastWhileDisabled
  L3_2 = A1_2.CanCast
  L2_2(L3_2)
end

BBSetCanCastWhileDisabled = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.TrackTimeVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetTime
  L4_2 = L4_2()
  L5_2 = A1_2.ExecuteImmediately
  L6_2 = A1_2.TimeBetweenExecutions
  L7_2 = A1_2.TickTimeVar
  if L7_2 ~= nil then
    L7_2 = GetTable
    L8_2 = A0_2
    L9_2 = A1_2.TickTimeVarTable
    L10_2 = false
    L7_2 = L7_2(L8_2, L9_2, L10_2)
    L8_2 = A1_2.TickTimeVar
    L8_2 = L7_2[L8_2]
    if L8_2 ~= nil then
      L6_2 = L8_2
    end
  end
  L7_2 = A1_2.TrackTimeVar
  L7_2 = L3_2[L7_2]
  if L7_2 == nil then
    L7_2 = A1_2.TrackTimeVar
    L3_2[L7_2] = L4_2
    if L5_2 == true then
      L7_2 = ExecuteBuildingBlocks
      L8_2 = A2_2
      L9_2 = A0_2
      L7_2(L8_2, L9_2)
    end
  end
  L7_2 = A1_2.TrackTimeVar
  L7_2 = L3_2[L7_2]
  L7_2 = L7_2 + L6_2
  if L4_2 >= L7_2 then
    L7_2 = A1_2.TrackTimeVar
    L8_2 = A1_2.TrackTimeVar
    L8_2 = L3_2[L8_2]
    L8_2 = L8_2 + L6_2
    L3_2[L7_2] = L8_2
    L7_2 = ExecuteBuildingBlocks
    L8_2 = A2_2
    L9_2 = A0_2
    L7_2(L8_2, L9_2)
  end
end

BBExecutePeriodically = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.TrackTimeVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.TrackTimeVar
  L3_2[L4_2] = nil
end

BBExecutePeriodicallyReset = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = A1_2.SrcValue
  L3_2 = A1_2.SrcVar
  if L3_2 ~= nil then
    L3_2 = GetTable
    L4_2 = A0_2
    L5_2 = A1_2.SrcTable
    L6_2 = true
    L3_2 = L3_2(L4_2, L5_2, L6_2)
    L4_2 = A1_2.SrcVar
    L2_2 = L3_2[L4_2]
  end
  L3_2 = A1_2.Status
  L4_2 = A1_2.TargetVar
  L4_2 = A0_2[L4_2]
  L5_2 = L2_2
  L3_2(L4_2, L5_2)
end

BBSetStatus = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = A1_2.ToAlert
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.SrcVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  if L3_2 ~= nil then
    L4_2 = A1_2.SrcVar
    if L4_2 ~= nil then
      L4_2 = L2_2
      L5_2 = A1_2.SrcVar
      L5_2 = L3_2[L5_2]
      L2_2 = L4_2 .. L5_2
    end
  end
  L4_2 = _ALERT
  L5_2 = L2_2
  L4_2(L5_2)
end

BBAlert = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2
  L2_2 = A1_2.ToSay
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.SrcVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  if L3_2 ~= nil then
    L4_2 = A1_2.SrcVar
    if L4_2 ~= nil then
      L4_2 = L2_2
      L5_2 = tostring
      L6_2 = A1_2.SrcVar
      L6_2 = L3_2[L6_2]
      L5_2 = L5_2(L6_2)
      L2_2 = L4_2 .. L5_2
    end
  end
  L4_2 = nil
  L5_2 = A1_2.OwnerVar
  if L5_2 ~= nil then
    L5_2 = A1_2.OwnerVar
    L4_2 = A0_2[L5_2]
  else
    L4_2 = A0_2.Owner
  end
  L5_2 = Say
  L6_2 = L4_2
  L7_2 = L2_2
  L5_2(L6_2, L7_2)
end

BBSay = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2
  L2_2 = A1_2.ToSay
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.SrcVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  if L3_2 ~= nil then
    L4_2 = A1_2.SrcVar
    if L4_2 ~= nil then
      L4_2 = L2_2
      L5_2 = tostring
      L6_2 = A1_2.SrcVar
      L6_2 = L3_2[L6_2]
      L5_2 = L5_2(L6_2)
      L2_2 = L4_2 .. L5_2
    end
  end
  L4_2 = nil
  L5_2 = A1_2.OwnerVar
  if L5_2 ~= nil then
    L5_2 = A1_2.OwnerVar
    L4_2 = A0_2[L5_2]
  else
    L4_2 = A0_2.Owner
  end
  L5_2 = Say
  L6_2 = L4_2
  L7_2 = L2_2
  L5_2(L6_2, L7_2)
end

BBDebugSay = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.DestVar
  L4_2 = BBLuaGetGold
  L5_2 = A0_2
  L6_2 = A1_2
  L4_2 = L4_2(L5_2, L6_2)
  L2_2[L3_2] = L4_2
end

BBGetGold = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.XVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.XVar
  if L3_2 ~= nil and L2_2 ~= nil then
    L3_2 = A1_2.XVar
    L3_2 = L2_2[L3_2]
    Xloc = L3_2
  else
    L3_2 = A1_2.X
    Xloc = L3_2
  end
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.YVarTable
  L6_2 = true
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.YVar
  if L4_2 ~= nil and L3_2 ~= nil then
    L4_2 = A1_2.YVar
    L4_2 = L3_2[L4_2]
    Yloc = L4_2
  else
    L4_2 = A1_2.Y
    Yloc = L4_2
  end
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.ZVarTable
  L7_2 = true
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.ZVar
  if L5_2 ~= nil and L4_2 ~= nil then
    L5_2 = A1_2.ZVar
    L5_2 = L4_2[L5_2]
    Zloc = L5_2
  else
    L5_2 = A1_2.Z
    Zloc = L5_2
  end
  L5_2 = A1_2.OwnerVar
  L6_2 = Make3DPoint
  L7_2 = Xloc
  L8_2 = Yloc
  L9_2 = Zloc
  L6_2 = L6_2(L7_2, L8_2, L9_2)
  A0_2.position = L6_2
  A1_2.OwnerVar = L5_2
  A1_2.CastPositionName = "position"
  L7_2 = BBTeleportToPosition
  L8_2 = A0_2
  L9_2 = A1_2
  L7_2(L8_2, L9_2)
end

BBTeleportToPoint = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.CenterTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = DefUpdateAura
  L4_2 = A1_2.CenterVar
  L4_2 = L2_2[L4_2]
  L5_2 = A1_2.Range
  L6_2 = A1_2.UnitScan
  L7_2 = A1_2.BuffName
  L3_2(L4_2, L5_2, L6_2, L7_2)
end

BBDefUpdateAura = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.TargetTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = ReincarnateNonDeadHero
  L4_2 = A1_2.TargetVar
  L4_2 = L2_2[L4_2]
  L3_2(L4_2)
end

BBReincarnateHero = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.DestVar
  L4_2 = A1_2.Function
  L5_2 = A1_2.OwnerVar
  L5_2 = A0_2[L5_2]
  L6_2 = A1_2.PARType
  L4_2 = L4_2(L5_2, L6_2)
  L2_2[L3_2] = L4_2
end

BBGetPAROrHealth = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = A1_2.WhomToOrderVar
  L2_2 = A0_2[L2_2]
  L3_2 = A1_2.TargetOfOrderVar
  L3_2 = A0_2[L3_2]
  L4_2 = IssueOrder
  L5_2 = L2_2
  L6_2 = A1_2.Order
  L7_2 = GetPosition
  L8_2 = L3_2
  L7_2 = L7_2(L8_2)
  L8_2 = L3_2
  L4_2(L5_2, L6_2, L7_2, L8_2)
end

BBIssueOrder = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2
  L2_2 = SetSpellCastRange
  L3_2 = A1_2.NewRange
  L2_2(L3_2)
end

BBSetSpellCastRange = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.DestVar
  L4_2 = GetTime
  L4_2 = L4_2()
  L2_2[L3_2] = L4_2
end

BBGetTime = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = A1_2.ObjectVar1
  L2_2 = A0_2[L2_2]
  L3_2 = A1_2.ObjectVar2
  L3_2 = A0_2[L3_2]
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.DestVarTable
  L7_2 = true
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.DestVar
  L6_2 = DistanceBetweenObjects
  L7_2 = L2_2
  L8_2 = L3_2
  L6_2 = L6_2(L7_2, L8_2)
  L4_2[L5_2] = L6_2
end

BBDistanceBetweenObjects = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L2_2 = A1_2.ObjectVar
  L2_2 = A0_2[L2_2]
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.PointVarTable
  L6_2 = true
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.PointVar
  L4_2 = L3_2[L4_2]
  L5_2 = GetTable
  L6_2 = A0_2
  L7_2 = A1_2.DestVarTable
  L8_2 = true
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L6_2 = A1_2.DestVar
  L7_2 = DistanceBetweenObjectAndPoint
  L8_2 = L2_2
  L9_2 = L4_2
  L7_2 = L7_2(L8_2, L9_2)
  L5_2[L6_2] = L7_2
end

BBDistanceBetweenObjectAndPoint = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.Point1VarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.Point1Var
  L3_2 = L2_2[L3_2]
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.Point2VarTable
  L7_2 = true
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.Point2Var
  L5_2 = L4_2[L5_2]
  L6_2 = GetTable
  L7_2 = A0_2
  L8_2 = A1_2.DestVarTable
  L9_2 = true
  L6_2 = L6_2(L7_2, L8_2, L9_2)
  L7_2 = A1_2.DestVar
  L8_2 = DistanceBetweenPoints
  L9_2 = L3_2
  L10_2 = L5_2
  L8_2 = L8_2(L9_2, L10_2)
  L6_2[L7_2] = L8_2
end

BBDistanceBetweenPoints = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L2_2 = A1_2.TargetVar
  L2_2 = A0_2[L2_2]
  L3_2 = A1_2.CasterVar
  L3_2 = A0_2[L3_2]
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.DestVarTable
  L7_2 = true
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.DestVar
  L6_2 = SpellBuffCount
  L7_2 = L2_2
  L8_2 = A1_2.BuffName
  L9_2 = L3_2
  L6_2 = L6_2(L7_2, L8_2, L9_2)
  L4_2[L5_2] = L6_2
end

BBGetBuffCountFromCaster = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = A1_2.TargetVar
  L2_2 = A0_2[L2_2]
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.DestVarTable
  L6_2 = true
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.DestVar
  L5_2 = SpellBuffCount
  L6_2 = L2_2
  L7_2 = A1_2.BuffName
  L8_2 = caster
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L3_2[L4_2] = L5_2
end

BBGetBuffCountFromAll = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.ScaleVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = nil
  L4_2 = A1_2.OwnerVar
  if L4_2 ~= nil then
    L4_2 = A1_2.OwnerVar
    L3_2 = A0_2[L4_2]
  else
    L3_2 = A0_2.Owner
  end
  L4_2 = A1_2.ScaleVar
  if L4_2 ~= nil then
    L4_2 = A1_2.ScaleVarTable
    if L4_2 ~= nil then
      L4_2 = SetScaleSkinCoef
      L5_2 = A1_2.ScaleVar
      L5_2 = L2_2[L5_2]
      L6_2 = L3_2
      L4_2(L5_2, L6_2)
  end
  else
    L4_2 = SetScaleSkinCoef
    L5_2 = A1_2.Scale
    L6_2 = L3_2
    L4_2(L5_2, L6_2)
  end
end

BBSetScaleSkinCoef = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L2_2 = SpellBuffAdd
  L3_2 = A1_2.TargetVar
  L3_2 = A0_2[L3_2]
  L4_2 = A1_2.TargetVar
  L4_2 = A0_2[L4_2]
  L5_2 = "SpellShieldMarker"
  L6_2 = 0
  L7_2 = 1
  L8_2 = 37037
  L9_2 = A0_2.NextBuffVars
  L2_2(L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2)
end

BBBreakSpellShields = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L3_2 = A1_2.TargetVar
  L3_2 = A0_2[L3_2]
  L4_2 = A1_2.NumStacks
  L5_2 = A1_2.NumStacks
  if L5_2 == 0 then
    L5_2 = SpellBuffCount
    L6_2 = L3_2
    L7_2 = A1_2.BuffName
    L8_2 = caster
    L5_2 = L5_2(L6_2, L7_2, L8_2)
    L4_2 = L5_2
  end
  while 0 < L4_2 do
    L5_2 = SpellBuffRemove
    L6_2 = L3_2
    L7_2 = A1_2.BuffName
    L8_2 = A1_2.AttackerVar
    L8_2 = A0_2[L8_2]
    L5_2(L6_2, L7_2, L8_2)
    L4_2 = L4_2 - 1
  end
end

BBSpellBuffRemoveStacks = L0_1
