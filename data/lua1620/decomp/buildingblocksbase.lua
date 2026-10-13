local L0_1, L1_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2, L13_2, L14_2, L15_2, L16_2
  L3_2 = {}
  L4_2 = pairs
  L5_2 = A1_2.Imms
  L4_2, L5_2, L6_2 = L4_2(L5_2)
  for L7_2, L8_2 in L4_2, L5_2, L6_2 do
    L3_2[L7_2] = L8_2
    L9_2 = GetHashedGameObjName
    L10_2 = L7_2
    L9_2 = L9_2(L10_2)
    L3_2[L9_2] = L8_2
  end
  L4_2 = pairs
  L5_2 = A1_2.InVars
  L4_2, L5_2, L6_2 = L4_2(L5_2)
  for L7_2, L8_2 in L4_2, L5_2, L6_2 do
    L9_2 = L8_2.VarTable
    L10_2 = L8_2.Var
    L11_2 = GetTable
    L12_2 = A0_2
    L13_2 = L9_2
    L14_2 = false
    L11_2 = L11_2(L12_2, L13_2, L14_2)
    L12_2 = L11_2[L10_2]
    L3_2[L7_2] = L12_2
    L13_2 = GetHashedGameObjName
    L14_2 = L7_2
    L13_2 = L13_2(L14_2)
    L3_2[L13_2] = L12_2
  end
  L4_2 = A0_2.InstanceVars
  L3_2.InstanceVars = L4_2
  L4_2 = A0_2.CharVars
  L3_2.CharVars = L4_2
  L4_2 = A0_2.NextBuffVars
  L3_2.NextBuffVars = L4_2
  L4_2 = A0_2.NextSpellVars
  L3_2.NextSpellVars = L4_2
  L4_2 = A0_2.AvatarVars
  L3_2.AvatarVars = L4_2
  L4_2 = A0_2.SpellVars
  L3_2.SpellVars = L4_2
  L4_2 = A0_2.WorldVars
  L3_2.WorldVars = L4_2
  L4_2 = A0_2.Target
  L3_2.Target = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "Target"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.Target
  L3_2[L4_2] = L5_2
  L4_2 = A0_2.Attacker
  L3_2.Attacker = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "Attacker"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.Attacker
  L3_2[L4_2] = L5_2
  L4_2 = A0_2.Owner
  L3_2.Owner = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "Owner"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.Owner
  L3_2[L4_2] = L5_2
  L3_2.FunctionSubBlocks = A2_2
  L3_2.CallerPTP = A0_2
  L4_2 = A0_2.Caster
  L3_2.Caster = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "Caster"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.Caster
  L3_2[L4_2] = L5_2
  L4_2 = A0_2.GoldRedirectTarget
  L3_2.GoldRedirectTarget = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "GoldRedirectTarget"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.GoldRedirectTarget
  L3_2[L4_2] = L5_2
  L4_2 = _G
  L5_2 = A1_2.BBFuncModule
  L4_2 = L4_2[L5_2]
  L5_2 = A1_2.BBFuncName
  L5_2 = L4_2[L5_2]
  L6_2 = ExecuteBuildingBlocksModuleFunction
  L7_2 = L5_2
  L8_2 = L3_2
  L6_2(L7_2, L8_2)
  L6_2 = pairs
  L7_2 = A1_2.OutVars
  L6_2, L7_2, L8_2 = L6_2(L7_2)
  for L9_2, L10_2 in L6_2, L7_2, L8_2 do
    L11_2 = L10_2.VarTable
    L12_2 = L10_2.Var
    L13_2 = GetTable2
    L14_2 = A0_2
    L15_2 = L11_2
    L16_2 = true
    L13_2 = L13_2(L14_2, L15_2, L16_2)
    L14_2 = L3_2[L9_2]
    L13_2[L12_2] = L14_2
  end
end

BBExecuteFunction = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2
  L2_2 = A0_2.CallerPTP
  L3_2 = A1_2.Exports
  if L3_2 ~= nil then
    L4_2 = ipairs
    L5_2 = A1_2.Exports
    L4_2, L5_2, L6_2 = L4_2(L5_2)
    for L7_2, L8_2 in L4_2, L5_2, L6_2 do
      L9_2 = A0_2[L8_2]
      L2_2[L8_2] = L9_2
      L10_2 = GetHashedGameObjName
      L11_2 = L8_2
      L10_2 = L10_2(L11_2)
      L2_2[L10_2] = L9_2
    end
  end
  L4_2 = ExecuteBuildingBlocksDefault
  L5_2 = A0_2.FunctionSubBlocks
  L6_2 = L2_2
  L4_2(L5_2, L6_2)
end

BBExecuteFunctionSubBlocks = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = GetParam
  L3_2 = "Required"
  L4_2 = A0_2
  L5_2 = A1_2
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = gDebugMode
  if L3_2 ~= nil and L2_2 == nil then
    L3_2 = A1_2.RequiredVarTable
    if L3_2 == nil then
      L3_2 = "PassThroughParams"
    end
    L4_2 = DebugError
    L5_2 = "Missing Required Variable: "
    L6_2 = L3_2
    L7_2 = "."
    L8_2 = A1_2.RequiredVar
    L5_2 = L5_2 .. L6_2 .. L7_2 .. L8_2
    L4_2(L5_2)
  end
end

BBRequireVar = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = ExecuteBuildingBlocksDefault
  L4_2 = A2_2
  L5_2 = A0_2
  L3_2(L4_2, L5_2)
end

BBCom = L0_1
L0_1 = "#00FF000"
DEBUG_TEXT_COLOR = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2, L4_2, L5_2
  L1_2 = "<font color=\""
  L2_2 = DEBUG_TEXT_COLOR
  L3_2 = "\">"
  L4_2 = A0_2
  L5_2 = "</font>"
  L1_2 = L1_2 .. L2_2 .. L3_2 .. L4_2 .. L5_2
  L2_2 = DebugClientPrint
  L3_2 = L1_2
  L2_2(L3_2)
end

DebugClientPrintColored = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = DebugClientPrintColored
  L2_2 = "(DEBUG) "
  L3_2 = A0_2
  L2_2 = L2_2 .. L3_2
  L1_2(L2_2)
end

DebugClientPrintStyled = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.TableName
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TableName
  if not L3_2 then
    L3_2 = "PassThroughParams"
  end
  L4_2 = DebugClientPrintStyled
  L5_2 = L3_2
  L4_2(L5_2)
  L4_2 = DebugPrintTableToChat
  L5_2 = L2_2
  L4_2(L5_2)
end

BBDebugPrintTableToChat = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2, L13_2, L14_2, L15_2, L16_2, L17_2
  if not A1_2 then
    A1_2 = 0
  end
  if 10 < A1_2 then
    return
  end
  L2_2 = nil
  L3_2 = "|"
  L4_2 = 1
  L5_2 = A1_2
  L6_2 = 1
  for L7_2 = L4_2, L5_2, L6_2 do
    L8_2 = L3_2
    L9_2 = "----"
    L3_2 = L8_2 .. L9_2
  end
  L4_2 = L3_2
  L5_2 = "{"
  L4_2 = L4_2 .. L5_2
  L5_2 = L3_2
  L6_2 = "}"
  L5_2 = L5_2 .. L6_2
  L6_2 = DebugClientPrintColored
  L7_2 = L4_2
  L6_2(L7_2)
  L6_2 = pairs
  L7_2 = A0_2
  L6_2, L7_2, L8_2 = L6_2(L7_2)
  for L9_2, L10_2 in L6_2, L7_2, L8_2 do
    L11_2 = nil
    L12_2 = tostring
    L13_2 = L9_2
    L12_2 = L12_2(L13_2)
    if L12_2 == "PassThroughParams" then
      L11_2 = "{{ PassThroughParams }}"
    else
      L13_2 = type
      L14_2 = L10_2
      L13_2 = L13_2(L14_2)
      if L13_2 == "table" then
        L11_2 = "Table"
      else
        L13_2 = tostring
        L14_2 = L10_2
        L13_2 = L13_2(L14_2)
        L11_2 = L13_2
      end
    end
    L13_2 = L3_2
    L14_2 = L13_2
    L15_2 = L12_2
    L16_2 = ": "
    L17_2 = L11_2
    L13_2 = L14_2 .. L15_2 .. L16_2 .. L17_2
    L14_2 = DebugClientPrintColored
    L15_2 = L13_2
    L14_2(L15_2)
    L14_2 = type
    L15_2 = L10_2
    L14_2 = L14_2(L15_2)
    if L14_2 == "table" then
      L14_2 = DebugPrintTableToChat
      L15_2 = L10_2
      L16_2 = A1_2 + 1
      L14_2(L15_2, L16_2)
    end
  end
  L6_2 = DebugClientPrintStyled
  L7_2 = L5_2
  L6_2(L7_2)
end

DebugPrintTableToChat = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2
  L2_2 = A1_2.ToSay
  if not L2_2 then
    L2_2 = ""
  end
  L3_2 = A1_2.Color
  if not L3_2 then
    L3_2 = DEBUG_TEXT_COLOR
  end
  if L3_2 == "FFFFFF" then
    L3_2 = DEBUG_TEXT_COLOR
  end
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.SrcVarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.SrcVar
  L5_2 = L4_2[L5_2]
  L6_2 = "<font color=\""
  L7_2 = L3_2
  L8_2 = "\">"
  L6_2 = L6_2 .. L7_2 .. L8_2
  if L2_2 == "" then
    L7_2 = A1_2.SrcVarTable
    if L7_2 ~= nil then
      L7_2 = L6_2
      L8_2 = "(DEBUG) "
      L9_2 = A1_2.SrcVarTable
      L10_2 = "."
      L11_2 = A1_2.SrcVar
      if not L11_2 then
        L11_2 = ""
      end
      L6_2 = L7_2 .. L8_2 .. L9_2 .. L10_2 .. L11_2
    else
      L7_2 = L6_2
      L8_2 = "(DEBUG) "
      L9_2 = A1_2.SrcVar
      if not L9_2 then
        L9_2 = ""
      end
      L6_2 = L7_2 .. L8_2 .. L9_2
    end
  else
    L7_2 = L6_2
    L8_2 = "(DEBUG) "
    L9_2 = L2_2
    L6_2 = L7_2 .. L8_2 .. L9_2
  end
  L7_2 = type
  L8_2 = L5_2
  L7_2 = L7_2(L8_2)
  if L7_2 ~= "table" then
    L7_2 = type
    L8_2 = L5_2
    L7_2 = L7_2(L8_2)
    if L7_2 ~= "nil" then
      L7_2 = L6_2
      L8_2 = " "
      L9_2 = tostring
      L10_2 = L5_2
      L9_2 = L9_2(L10_2)
      L6_2 = L7_2 .. L8_2 .. L9_2
    end
  end
  L7_2 = L6_2
  L8_2 = "</font>"
  L6_2 = L7_2 .. L8_2
  L7_2 = DebugClientPrint
  L8_2 = L6_2
  L7_2(L8_2)
  L7_2 = type
  L8_2 = L5_2
  L7_2 = L7_2(L8_2)
  if L7_2 == "table" then
    L7_2 = DebugPrintTableToChat
    L8_2 = L5_2
    L7_2(L8_2)
  end
end

BBDebugPrintToChat = L0_1

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

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2
  if A1_2 == "PassThroughParams" then
    return A0_2
  end
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

GetTable2 = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2
  L3_2 = GetTable
  L4_2 = A1_2
  L5_2 = A0_2
  L6_2 = "VarTable"
  L5_2 = L5_2 .. L6_2
  L5_2 = A2_2[L5_2]
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A0_2
  L5_2 = "Var"
  L4_2 = L4_2 .. L5_2
  L4_2 = A2_2[L4_2]
  if L4_2 ~= nil and L3_2 ~= nil then
    L4_2 = A0_2
    L5_2 = "Var"
    L4_2 = L4_2 .. L5_2
    L4_2 = A2_2[L4_2]
    L4_2 = L3_2[L4_2]
    return L4_2
  else
    L4_2 = A2_2[A0_2]
    return L4_2
  end
end

GetParam = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L2_2 = A1_2.ToLog
  if not L2_2 then
    L2_2 = ""
  end
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.SrcVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.SrcVar
  L4_2 = L3_2[L4_2]
  L5_2 = ""
  if L2_2 == "" then
    L6_2 = A1_2.SrcVarTable
    if L6_2 ~= nil then
      L6_2 = A1_2.SrcVarTable
      L7_2 = "."
      L8_2 = A1_2.SrcVar
      if not L8_2 then
        L8_2 = ""
      end
      L5_2 = L6_2 .. L7_2 .. L8_2
    else
      L6_2 = A1_2.SrcVar
      L5_2 = L6_2 or L5_2
      if not L6_2 then
        L5_2 = ""
      end
    end
  else
    L5_2 = L2_2
  end
  L6_2 = L5_2
  L7_2 = " "
  L8_2 = tostring
  L9_2 = L4_2
  L8_2 = L8_2(L9_2)
  L5_2 = L6_2 .. L7_2 .. L8_2
  L6_2 = DebugLogSREEventInfo
  L7_2 = L5_2
  L6_2(L7_2)
end

BBDebugLogSREEventInfo = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2, L13_2, L14_2, L15_2, L16_2, L17_2, L18_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.TableVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = false
  L5_2 = A1_2.TableVar
  L5_2 = L3_2[L5_2]
  L5_2 = L5_2[1]
  if L5_2 ~= nil then
    L4_2 = true
  end
  if L4_2 then
    L5_2 = {}
    L6_2 = false
    L7_2 = true
    L8_2 = ipairs
    L9_2 = A1_2.TableVar
    L9_2 = L3_2[L9_2]
    L8_2, L9_2, L10_2 = L8_2(L9_2)
    for L11_2, L12_2 in L8_2, L9_2, L10_2 do
      if L7_2 then
        L13_2 = RemoveEachFromCustomTableWhere_ExecuteIteration
        L14_2 = L11_2
        L15_2 = L12_2
        L16_2 = A0_2
        L17_2 = A1_2
        L18_2 = A2_2
        L13_2, L14_2 = L13_2(L14_2, L15_2, L16_2, L17_2, L18_2)
        L7_2 = L14_2
        L6_2 = L13_2
        if L6_2 == false then
          L13_2 = table
          L13_2 = L13_2.insert
          L14_2 = L5_2
          L15_2 = L12_2
          L13_2(L14_2, L15_2)
        end
      else
        L13_2 = table
        L13_2 = L13_2.insert
        L14_2 = L5_2
        L15_2 = L12_2
        L13_2(L14_2, L15_2)
      end
    end
    L8_2 = A1_2.TableVar
    L3_2[L8_2] = L5_2
  else
    L5_2 = {}
    L6_2 = false
    L7_2 = true
    L8_2 = pairs
    L9_2 = A1_2.TableVar
    L9_2 = L3_2[L9_2]
    L8_2, L9_2, L10_2 = L8_2(L9_2)
    for L11_2, L12_2 in L8_2, L9_2, L10_2 do
      L13_2 = RemoveEachFromCustomTableWhere_ExecuteIteration
      L14_2 = L11_2
      L15_2 = L12_2
      L16_2 = A0_2
      L17_2 = A1_2
      L18_2 = A2_2
      L13_2, L14_2 = L13_2(L14_2, L15_2, L16_2, L17_2, L18_2)
      L7_2 = L14_2
      L6_2 = L13_2
      if L6_2 == true then
        L13_2 = table
        L13_2 = L13_2.insert
        L14_2 = L5_2
        L15_2 = L11_2
        L13_2(L14_2, L15_2)
      end
      if not L7_2 then
        break
      end
    end
    L8_2 = pairs
    L9_2 = L5_2
    L8_2, L9_2, L10_2 = L8_2(L9_2)
    for L11_2, L12_2 in L8_2, L9_2, L10_2 do
      L13_2 = A1_2.TableVar
      L13_2 = L3_2[L13_2]
      L13_2[L12_2] = nil
    end
  end
end

BBRemoveEachFromCustomTableWhere = L0_1

function L0_1(A0_2, A1_2, A2_2, A3_2, A4_2)
  local L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2
  L5_2 = GetTable
  L6_2 = A2_2
  L7_2 = A3_2.IterKeyVarTable
  L8_2 = true
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L6_2 = A3_2.IterKeyVar
  L5_2[L6_2] = A0_2
  L6_2 = GetTable
  L7_2 = A2_2
  L8_2 = A3_2.IterValueVarTable
  L9_2 = true
  L6_2 = L6_2(L7_2, L8_2, L9_2)
  L7_2 = A3_2.IterValueVar
  L6_2[L7_2] = A1_2
  L7_2 = GetTable
  L8_2 = A2_2
  L9_2 = A3_2.ShouldRemoveVarTable
  L10_2 = true
  L7_2 = L7_2(L8_2, L9_2, L10_2)
  L8_2 = A3_2.ShouldRemoveVar
  L7_2[L8_2] = false
  L8_2 = ExecuteBuildingBlocksLoop
  L9_2 = A4_2
  L10_2 = A2_2
  L8_2 = L8_2(L9_2, L10_2)
  L9_2 = A3_2.ShouldRemoveVar
  L9_2 = L7_2[L9_2]
  L10_2 = L9_2
  L11_2 = L8_2
  return L10_2, L11_2
end

RemoveEachFromCustomTableWhere_ExecuteIteration = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L3_2 = false
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.DestVarVarTable
  L7_2 = true
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.DestVarVar
  L5_2 = L4_2[L5_2]
  if L5_2 == nil then
    L3_2 = true
    L6_2 = A1_2.DestVarVar
    L7_2 = {}
    L4_2[L6_2] = L7_2
  end
  L6_2 = A1_2.DestTempTable
  L7_2 = A1_2.DestVarVar
  L7_2 = L4_2[L7_2]
  A0_2[L6_2] = L7_2
  if L3_2 then
    L6_2 = ExecuteBuildingBlocksDefault
    L7_2 = A2_2
    L8_2 = A0_2
    L6_2(L7_2, L8_2)
  end
end

BBGetAndInitTempTableInVar = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L3_2 = false
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.DestTableVarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = GetParam
  L6_2 = "DestKey"
  L7_2 = A0_2
  L8_2 = A1_2
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L6_2 = A1_2.DestTableVar
  L6_2 = L4_2[L6_2]
  L6_2 = L6_2[L5_2]
  if L6_2 == nil then
    L3_2 = true
    L6_2 = A1_2.DestTableVar
    L6_2 = L4_2[L6_2]
    L7_2 = {}
    L6_2[L5_2] = L7_2
  end
  L6_2 = A1_2.DestTempTable
  L7_2 = A1_2.DestTableVar
  L7_2 = L4_2[L7_2]
  L7_2 = L7_2[L5_2]
  A0_2[L6_2] = L7_2
  if L3_2 then
    L6_2 = ExecuteBuildingBlocksDefault
    L7_2 = A2_2
    L8_2 = A0_2
    L6_2(L7_2, L8_2)
  end
end

BBGetAndInitTempTableInCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.SourceVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.SourceVar
  L3_2 = L2_2[L3_2]
  L4_2 = A1_2.Dest
  A0_2[L4_2] = L3_2
end

BBAttachVarToTempTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.Source
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.DestVarTable
  L6_2 = true
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.DestVar
  L3_2[L4_2] = L2_2
end

BBAttachTempTableToVar = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2, L13_2, L14_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.TableToShuffleVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TableToShuffleVar
  L3_2 = L2_2[L3_2]
  L4_2 = {}
  L5_2 = 0
  L6_2 = pairs
  L7_2 = L3_2
  L6_2, L7_2, L8_2 = L6_2(L7_2)
  for L9_2, L10_2 in L6_2, L7_2, L8_2 do
    L5_2 = L5_2 + 1
    L4_2[L5_2] = L9_2
  end
  L6_2 = #L4_2
  L7_2 = 2
  L8_2 = -1
  for L9_2 = L6_2, L7_2, L8_2 do
    L10_2 = MO_RAND_INT_RANGE
    L11_2 = 1
    L12_2 = L9_2
    L10_2 = L10_2(L11_2, L12_2)
    L11_2 = L4_2[L9_2]
    L12_2 = L4_2[L10_2]
    L13_2 = L3_2[L12_2]
    L14_2 = L3_2[L11_2]
    L3_2[L12_2] = L14_2
    L3_2[L11_2] = L13_2
  end
end

BBShuffleCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestVarTable
  L5_2 = true
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.DestVar
  L4_2 = {}
  L2_2[L3_2] = L4_2
end

BBCreateCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.TableNameVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.TableNameVar
  L2_2[L3_2] = nil
end

BBDestroyCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestTableVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = GetParam
  L4_2 = "Key"
  L5_2 = A0_2
  L6_2 = A1_2
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetParam
  L5_2 = "Value"
  L6_2 = A0_2
  L7_2 = A1_2
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = type
  L6_2 = A1_2.DestTableVar
  L6_2 = L2_2[L6_2]
  L5_2 = L5_2(L6_2)
  if L5_2 == "nil" then
    L5_2 = A1_2.DestTableVar
    L6_2 = {}
    L2_2[L5_2] = L6_2
  end
  L5_2 = type
  L6_2 = A1_2.DestTableVar
  L6_2 = L2_2[L6_2]
  L5_2 = L5_2(L6_2)
  if L5_2 == "table" then
    L5_2 = A1_2.DestTableVar
    L5_2 = L2_2[L5_2]
    L5_2[L3_2] = L4_2
  end
end

BBSetKeyValueInCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.SrcTableVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = GetParam
  L4_2 = "SrcKey"
  L5_2 = A0_2
  L6_2 = A1_2
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = type
  L5_2 = A1_2.SrcTableVar
  L5_2 = L2_2[L5_2]
  L4_2 = L4_2(L5_2)
  if L4_2 == "table" then
    L4_2 = GetTable
    L5_2 = A0_2
    L6_2 = A1_2.DestVarTable
    L7_2 = true
    L4_2 = L4_2(L5_2, L6_2, L7_2)
    L5_2 = A1_2.DestVar
    L6_2 = A1_2.SrcTableVar
    L6_2 = L2_2[L6_2]
    L6_2 = L6_2[L3_2]
    L4_2[L5_2] = L6_2
  end
end

BBGetKeyValueInCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.DestTableVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = GetParam
  L4_2 = "DestIndex"
  L5_2 = A0_2
  L6_2 = A1_2
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetParam
  L5_2 = "Value"
  L6_2 = A0_2
  L7_2 = A1_2
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = type
  L6_2 = A1_2.DestTableVar
  L6_2 = L2_2[L6_2]
  L5_2 = L5_2(L6_2)
  if L5_2 == "nil" then
    L5_2 = A1_2.DestTableVar
    L6_2 = {}
    L2_2[L5_2] = L6_2
  end
  L5_2 = type
  L6_2 = A1_2.DestTableVar
  L6_2 = L2_2[L6_2]
  L5_2 = L5_2(L6_2)
  if L5_2 == "table" then
    if L3_2 then
      L5_2 = table
      L5_2 = L5_2.insert
      L6_2 = A1_2.DestTableVar
      L6_2 = L2_2[L6_2]
      L7_2 = L3_2
      L8_2 = L4_2
      L5_2(L6_2, L7_2, L8_2)
      L5_2 = A1_2.OutIndexVar
      if L5_2 then
        L5_2 = GetTable
        L6_2 = A0_2
        L7_2 = A1_2.OutIndexVarTable
        L8_2 = true
        L5_2 = L5_2(L6_2, L7_2, L8_2)
        L6_2 = A1_2.OutIndexVar
        L5_2[L6_2] = L3_2
      end
    else
      L5_2 = table
      L5_2 = L5_2.insert
      L6_2 = A1_2.DestTableVar
      L6_2 = L2_2[L6_2]
      L7_2 = L4_2
      L5_2(L6_2, L7_2)
      L5_2 = A1_2.OutIndexVar
      if L5_2 then
        L5_2 = GetTable
        L6_2 = A0_2
        L7_2 = A1_2.OutIndexVarTable
        L8_2 = true
        L5_2 = L5_2(L6_2, L7_2, L8_2)
        L6_2 = A1_2.OutIndexVar
        L7_2 = table
        L7_2 = L7_2.getn
        L8_2 = A1_2.DestTableVar
        L8_2 = L2_2[L8_2]
        L7_2 = L7_2(L8_2)
        L5_2[L6_2] = L7_2
      end
    end
  end
end

BBInsertIntoInCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.TableVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = GetParam
  L4_2 = "Index"
  L5_2 = A0_2
  L6_2 = A1_2
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetParam
  L5_2 = "Key"
  L6_2 = A0_2
  L7_2 = A1_2
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = type
  L6_2 = A1_2.TableVar
  L6_2 = L2_2[L6_2]
  L5_2 = L5_2(L6_2)
  if L5_2 == "nil" then
    L5_2 = DebugClientPrint
    L6_2 = "Table specified does not exist: "
    L7_2 = tostring
    L8_2 = A1_2.TableVarTable
    L7_2 = L7_2(L8_2)
    L8_2 = "."
    L9_2 = tostring
    L10_2 = A1_2.TableVar
    L9_2 = L9_2(L10_2)
    L6_2 = L6_2 .. L7_2 .. L8_2 .. L9_2
    L5_2(L6_2)
    return
  end
  L5_2 = type
  L6_2 = A1_2.TableVar
  L6_2 = L2_2[L6_2]
  L5_2 = L5_2(L6_2)
  if L5_2 == "table" then
    if L4_2 then
      L5_2 = A1_2.TableVar
      L5_2 = L2_2[L5_2]
      L5_2[L4_2] = nil
    elseif L3_2 then
      L5_2 = table
      L5_2 = L5_2.remove
      L6_2 = A1_2.TableVar
      L6_2 = L2_2[L6_2]
      L7_2 = L3_2
      L5_2(L6_2, L7_2)
    else
      L5_2 = DebugClientPrint
      L6_2 = "Specified index/key was nil: "
      L7_2 = tostring
      L8_2 = A1_2.IndexVarTable
      L7_2 = L7_2(L8_2)
      L8_2 = "."
      L9_2 = tostring
      L10_2 = A1_2.IndexVar
      L9_2 = L9_2(L10_2)
      L6_2 = L6_2 .. L7_2 .. L8_2 .. L9_2
      L5_2(L6_2)
    end
  end
end

BBRemoveFromCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2
  A1_2.SizeVar = "_tempSizeVar"
  A1_2.SizeVarTable = "PassThroughParams"
  L2_2 = {}
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.TableVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = 0
  L5_2 = pairs
  L6_2 = A1_2.TableVar
  L6_2 = L3_2[L6_2]
  L5_2, L6_2, L7_2 = L5_2(L6_2)
  for L8_2, L9_2 in L5_2, L6_2, L7_2 do
    L4_2 = L4_2 + 1
    L10_2 = table
    L10_2 = L10_2.insert
    L11_2 = L2_2
    L12_2 = L8_2
    L10_2(L11_2, L12_2)
  end
  L5_2 = MO_RAND_INT_RANGE
  L6_2 = 1
  L7_2 = L4_2
  L5_2 = L5_2(L6_2, L7_2)
  L6_2 = nil
  L7_2 = L2_2[L5_2]
  if L7_2 ~= nil then
    L7_2 = A1_2.TableVar
    L7_2 = L3_2[L7_2]
    L8_2 = L2_2[L5_2]
    L6_2 = L7_2[L8_2]
    L7_2 = A1_2.ShouldRemove
    if L7_2 == true then
      L7_2 = A1_2.TableVar
      L7_2 = L3_2[L7_2]
      L8_2 = L2_2[L5_2]
      L7_2[L8_2] = nil
      L7_2 = table
      L7_2 = L7_2.remove
      L8_2 = A1_2.TableVar
      L8_2 = L3_2[L8_2]
      L9_2 = L2_2[L5_2]
      L7_2(L8_2, L9_2)
    end
  end
  L7_2 = GetTable
  L8_2 = A0_2
  L9_2 = A1_2.DestVarTable
  L10_2 = false
  L7_2 = L7_2(L8_2, L9_2, L10_2)
  L8_2 = A1_2.DestVar
  L7_2[L8_2] = L6_2
  L8_2 = A1_2.KeyDestVar
  if L8_2 ~= nil then
    L8_2 = GetTable
    L9_2 = A0_2
    L10_2 = A1_2.KeyDestVarTable
    L11_2 = false
    L8_2 = L8_2(L9_2, L10_2, L11_2)
    L9_2 = A1_2.KeyDestVar
    L10_2 = L2_2[L5_2]
    L8_2[L9_2] = L10_2
  end
end

BBGetRandomFromCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.TableVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = 0
  L4_2 = 0
  L5_2 = pairs
  L6_2 = A1_2.TableVar
  L6_2 = L2_2[L6_2]
  L5_2, L6_2, L7_2 = L5_2(L6_2)
  for L8_2, L9_2 in L5_2, L6_2, L7_2 do
    L3_2 = L3_2 + 1
    L4_2 = L4_2 + L9_2
  end
  L5_2 = 0
  if 0 < L3_2 then
    L5_2 = L4_2 / L3_2
  end
  L6_2 = GetTable
  L7_2 = A0_2
  L8_2 = A1_2.AverageVarTable
  L9_2 = false
  L6_2 = L6_2(L7_2, L8_2, L9_2)
  L7_2 = A1_2.AverageVar
  L6_2[L7_2] = L5_2
end

BBGetAverageValueInCustomTable = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2, L13_2, L14_2, L15_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.TableVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = type
  L5_2 = A1_2.TableVar
  L5_2 = L3_2[L5_2]
  L4_2 = L4_2(L5_2)
  if L4_2 == "table" then
    L4_2 = A1_2.SortedByKeys
    if L4_2 then
      L4_2 = {}
      L5_2 = pairs
      L6_2 = A1_2.TableVar
      L6_2 = L3_2[L6_2]
      L5_2, L6_2, L7_2 = L5_2(L6_2)
      for L8_2, L9_2 in L5_2, L6_2, L7_2 do
        L10_2 = table
        L10_2 = L10_2.insert
        L11_2 = L4_2
        L12_2 = L8_2
        L10_2(L11_2, L12_2)
      end
      L5_2 = table
      L5_2 = L5_2.sort
      L6_2 = L4_2
      L5_2(L6_2)
      L5_2 = pairs
      L6_2 = L4_2
      L5_2, L6_2, L7_2 = L5_2(L6_2)
      for L8_2, L9_2 in L5_2, L6_2, L7_2 do
        L10_2 = A1_2.TableVar
        L10_2 = L3_2[L10_2]
        L10_2 = L10_2[L9_2]
        L11_2 = GetTable
        L12_2 = A0_2
        L13_2 = A1_2.DestKeyVarTable
        L14_2 = true
        L11_2 = L11_2(L12_2, L13_2, L14_2)
        L12_2 = GetTable
        L13_2 = A0_2
        L14_2 = A1_2.DestValueVarTable
        L15_2 = true
        L12_2 = L12_2(L13_2, L14_2, L15_2)
        L13_2 = A1_2.DestKeyVar
        L11_2[L13_2] = L9_2
        L13_2 = A1_2.DestValueVar
        L12_2[L13_2] = L10_2
        L13_2 = ExecuteBuildingBlocksLoop
        L14_2 = A2_2
        L15_2 = A0_2
        L13_2 = L13_2(L14_2, L15_2)
        if not L13_2 then
          break
        end
      end
    else
      L4_2 = pairs
      L5_2 = A1_2.TableVar
      L5_2 = L3_2[L5_2]
      L4_2, L5_2, L6_2 = L4_2(L5_2)
      for L7_2, L8_2 in L4_2, L5_2, L6_2 do
        L9_2 = GetTable
        L10_2 = A0_2
        L11_2 = A1_2.DestKeyVarTable
        L12_2 = true
        L9_2 = L9_2(L10_2, L11_2, L12_2)
        L10_2 = GetTable
        L11_2 = A0_2
        L12_2 = A1_2.DestValueVarTable
        L13_2 = true
        L10_2 = L10_2(L11_2, L12_2, L13_2)
        L11_2 = A1_2.DestKeyVar
        L9_2[L11_2] = L7_2
        L11_2 = A1_2.DestValueVar
        L10_2[L11_2] = L8_2
        L11_2 = ExecuteBuildingBlocksLoop
        L12_2 = A2_2
        L13_2 = A0_2
        L11_2 = L11_2(L12_2, L13_2)
        if not L11_2 then
          break
        end
      end
    end
  end
end

BBForEachInCustomTable = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2, L13_2, L14_2, L15_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.TableVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = type
  L5_2 = A1_2.TableVar
  L5_2 = L3_2[L5_2]
  L4_2 = L4_2(L5_2)
  if L4_2 == "table" then
    L4_2 = {}
    L5_2 = pairs
    L6_2 = A1_2.TableVar
    L6_2 = L3_2[L6_2]
    L5_2, L6_2, L7_2 = L5_2(L6_2)
    for L8_2, L9_2 in L5_2, L6_2, L7_2 do
      L10_2 = table
      L10_2 = L10_2.insert
      L11_2 = L4_2
      L12_2 = L8_2
      L10_2(L11_2, L12_2)
    end
    L5_2 = A1_2.Ascending
    if L5_2 then
      L5_2 = table
      L5_2 = L5_2.sort
      L6_2 = L4_2
      
      function L7_2(A0_3, A1_3)
        local L2_3, L3_3, L4_3
        L2_3 = L3_2
        L3_3 = A1_2
        L3_3 = L3_3.TableVar
        L2_3 = L2_3[L3_3]
        L2_3 = L2_3[A0_3]
        L3_3 = L3_2
        L4_3 = A1_2
        L4_3 = L4_3.TableVar
        L3_3 = L3_3[L4_3]
        L3_3 = L3_3[A1_3]
        L2_3 = L2_3 < L3_3
        return L2_3
      end
      
      L5_2(L6_2, L7_2)
    else
      L5_2 = table
      L5_2 = L5_2.sort
      L6_2 = L4_2
      
      function L7_2(A0_3, A1_3)
        local L2_3, L3_3, L4_3
        L2_3 = L3_2
        L3_3 = A1_2
        L3_3 = L3_3.TableVar
        L2_3 = L2_3[L3_3]
        L2_3 = L2_3[A0_3]
        L3_3 = L3_2
        L4_3 = A1_2
        L4_3 = L4_3.TableVar
        L3_3 = L3_3[L4_3]
        L3_3 = L3_3[A1_3]
        L2_3 = L2_3 > L3_3
        return L2_3
      end
      
      L5_2(L6_2, L7_2)
    end
    L5_2 = pairs
    L6_2 = L4_2
    L5_2, L6_2, L7_2 = L5_2(L6_2)
    for L8_2, L9_2 in L5_2, L6_2, L7_2 do
      L10_2 = A1_2.TableVar
      L10_2 = L3_2[L10_2]
      L10_2 = L10_2[L9_2]
      L11_2 = GetTable
      L12_2 = A0_2
      L13_2 = A1_2.DestKeyVarTable
      L14_2 = true
      L11_2 = L11_2(L12_2, L13_2, L14_2)
      L12_2 = GetTable
      L13_2 = A0_2
      L14_2 = A1_2.DestValueVarTable
      L15_2 = true
      L12_2 = L12_2(L13_2, L14_2, L15_2)
      L13_2 = A1_2.DestKeyVar
      L11_2[L13_2] = L9_2
      L13_2 = A1_2.DestValueVar
      L12_2[L13_2] = L10_2
      L13_2 = ExecuteBuildingBlocksLoop
      L14_2 = A2_2
      L15_2 = A0_2
      L13_2 = L13_2(L14_2, L15_2)
      if not L13_2 then
        break
      end
    end
  end
end

BBForEachInSortedCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.SrcTableVarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = GetParam
  L4_2 = "Value"
  L5_2 = A0_2
  L6_2 = A1_2
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.MatchingKeyVarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = GetTable
  L6_2 = A0_2
  L7_2 = A1_2.WasFoundVarTable
  L8_2 = false
  L5_2 = L5_2(L6_2, L7_2, L8_2)
  L6_2 = A1_2.WasFoundVar
  L5_2[L6_2] = false
  L6_2 = type
  L7_2 = A1_2.SrcTableVar
  L7_2 = L2_2[L7_2]
  L6_2 = L6_2(L7_2)
  if L6_2 == "table" then
    L6_2 = GetTable
    L7_2 = A0_2
    L8_2 = A1_2.DestVarTable
    L9_2 = true
    L6_2 = L6_2(L7_2, L8_2, L9_2)
    L7_2 = pairs
    L8_2 = L6_2
    L7_2, L8_2, L9_2 = L7_2(L8_2)
    for L10_2, L11_2 in L7_2, L8_2, L9_2 do
      if L11_2 == L3_2 then
        L12_2 = A1_2.WasFoundVar
        L5_2[L12_2] = true
        L12_2 = A1_2.MatchingKeyVar
        L4_2[L12_2] = L10_2
      end
    end
  end
end

BBCustomTableContainsValue = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.TableVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.SizeVarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = 0
  L6_2 = pairs
  L7_2 = A1_2.TableVar
  L7_2 = L3_2[L7_2]
  L6_2, L7_2, L8_2 = L6_2(L7_2)
  for L9_2, L10_2 in L6_2, L7_2, L8_2 do
    L5_2 = L5_2 + 1
  end
  L6_2 = A1_2.SizeVar
  L4_2[L6_2] = L5_2
end

BBGetSizeOfCustomTable = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.SlotVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.SlotVar
  if L4_2 ~= nil and L3_2 ~= nil then
    L4_2 = A1_2.SlotVar
    L2_2 = L3_2[L4_2]
  else
    L2_2 = A1_2.Slot
  end
  L4_2 = A1_2.Function
  L5_2 = A1_2.OwnerVar
  L5_2 = A0_2[L5_2]
  L6_2 = L2_2
  L7_2 = A1_2.SlotBook
  L8_2 = A1_2.SlotType
  L4_2 = L4_2(L5_2, L6_2, L7_2, L8_2)
  L5_2 = SetVarInTable
  L6_2 = A0_2
  L7_2 = A1_2
  L8_2 = L4_2
  L5_2(L6_2, L7_2, L8_2)
end

BBGetSlotSpellInfo = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.MacroVarTable
  L6_2 = true
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.MacroVar
  L3_2[L4_2] = A2_2
end

BBCreateMacro = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L2_2 = GetParam
  L3_2 = "Macro"
  L4_2 = A0_2
  L5_2 = A1_2
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  if L2_2 ~= nil then
    L3_2 = type
    L4_2 = L2_2
    L3_2 = L3_2(L4_2)
    if L3_2 == "table" then
      L3_2 = ExecuteBuildingBlocksDefault
      L4_2 = L2_2
      L5_2 = A0_2
      L3_2(L4_2, L5_2)
  end
  else
    L3_2 = A1_2.FunctionVarTable
    if L3_2 == nil then
      L3_2 = "PassThroughParams"
    end
    L4_2 = DebugError
    L5_2 = "Macro variable "
    L6_2 = tostring
    L7_2 = L3_2
    L6_2 = L6_2(L7_2)
    L7_2 = "."
    L8_2 = tostring
    L9_2 = A1_2.FunctionVar
    L8_2 = L8_2(L9_2)
    L9_2 = " not initialized."
    L5_2 = L5_2 .. L6_2 .. L7_2 .. L8_2 .. L9_2
    L4_2(L5_2)
  end
end

BBRunMacro = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  if A2_2 == nil then
    L3_2 = {}
    A2_2 = L3_2
  end
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.FunctionVarTable
  L6_2 = true
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = A1_2.FunctionVar
  L3_2[L4_2] = A2_2
  L4_2 = A2_2.InPerBlockParams
  if L4_2 == nil then
    A2_2.InPerBlockParams = A1_2
    L4_2 = 1
    L5_2 = 6
    L6_2 = 1
    for L7_2 = L4_2, L5_2, L6_2 do
      L8_2 = "FunctionParameter"
      L9_2 = L7_2
      L10_2 = "Var"
      L8_2 = L8_2 .. L9_2 .. L10_2
      L9_2 = L8_2
      L10_2 = "Table"
      L9_2 = L9_2 .. L10_2
      L9_2 = A1_2[L9_2]
      if L9_2 ~= nil then
        L9_2 = DebugError
        L10_2 = "CreateFunction can only input parameters to PassThroughParams."
        L9_2(L10_2)
      end
    end
  end
end

BBCreateFunction = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = 1
  L3_2 = 6
  L4_2 = 1
  for L5_2 = L2_2, L3_2, L4_2 do
    L6_2 = "FunctionOutput"
    L7_2 = L5_2
    L8_2 = "Var"
    L6_2 = L6_2 .. L7_2 .. L8_2
    L7_2 = A1_2[L6_2]
    if L7_2 ~= nil then
      L7_2 = A1_2[L6_2]
      if L7_2 ~= "" then
        L7_2 = L6_2
        L8_2 = "Table"
        L7_2 = L7_2 .. L8_2
        L7_2 = A1_2[L7_2]
        if L7_2 ~= nil then
          L7_2 = DebugError
          L8_2 = "EndFunction can only output from PassThroughParams."
          L7_2(L8_2)
        else
          L7_2 = A0_2
          L8_2 = A1_2[L6_2]
          L8_2 = L7_2[L8_2]
          A0_2[L6_2] = L8_2
        end
      end
    end
  end
  L2_2 = EndFunctionInternal
  L3_2 = A0_2
  L2_2(L3_2)
end

BBEndFunction = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2, L12_2, L13_2
  L2_2 = GetParam
  L3_2 = "Function"
  L4_2 = A0_2
  L5_2 = A1_2
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = {}
  L4_2 = A0_2.InstanceVars
  L3_2.InstanceVars = L4_2
  L4_2 = A0_2.CharVars
  L3_2.CharVars = L4_2
  L4_2 = A0_2.NextBuffVars
  L3_2.NextBuffVars = L4_2
  L4_2 = A0_2.NextSpellVars
  L3_2.NextSpellVars = L4_2
  L4_2 = A0_2.AvatarVars
  L3_2.AvatarVars = L4_2
  L4_2 = A0_2.SpellVars
  L3_2.SpellVars = L4_2
  L4_2 = A0_2.WorldVars
  L3_2.WorldVars = L4_2
  L4_2 = A0_2.Target
  L3_2.Target = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "Target"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.Target
  L3_2[L4_2] = L5_2
  L4_2 = A0_2.Attacker
  L3_2.Attacker = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "Attacker"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.Attacker
  L3_2[L4_2] = L5_2
  L4_2 = A0_2.Owner
  L3_2.Owner = L4_2
  L4_2 = GetHashedGameObjName
  L5_2 = "Owner"
  L4_2 = L4_2(L5_2)
  L5_2 = A0_2.Owner
  L3_2[L4_2] = L5_2
  L4_2 = A0_2.Caster
  L3_2.Caster = L4_2
  L4_2 = A0_2.GoldRedirectTarget
  L3_2.GoldRedirectTarget = L4_2
  L4_2 = A0_2.Unit
  L3_2.Unit = L4_2
  L4_2 = A0_2.Other1
  L3_2.Other1 = L4_2
  L4_2 = A0_2.Other2
  L3_2.Other2 = L4_2
  L4_2 = A0_2.Other3
  L3_2.Other3 = L4_2
  L4_2 = A0_2.Nothing
  L3_2.Nothing = L4_2
  if L2_2 ~= nil then
    L4_2 = type
    L5_2 = L2_2
    L4_2 = L4_2(L5_2)
    if L4_2 == "table" then
      L4_2 = L2_2.InPerBlockParams
      if L4_2 ~= nil then
        L4_2 = L2_2.InPerBlockParams
        L5_2 = 1
        L6_2 = 6
        L7_2 = 1
        for L8_2 = L5_2, L6_2, L7_2 do
          L9_2 = "FunctionParameter"
          L10_2 = L8_2
          L11_2 = "Var"
          L9_2 = L9_2 .. L10_2 .. L11_2
          L10_2 = A1_2[L9_2]
          if L10_2 ~= nil then
            L10_2 = A1_2[L9_2]
            if L10_2 ~= "" then
              L10_2 = L4_2[L9_2]
              if L10_2 ~= nil then
                L10_2 = L4_2[L9_2]
                if L10_2 ~= "" then
                  L10_2 = GetTable
                  L11_2 = A0_2
                  L12_2 = L9_2
                  L13_2 = "Table"
                  L12_2 = L12_2 .. L13_2
                  L12_2 = A1_2[L12_2]
                  L13_2 = false
                  L10_2 = L10_2(L11_2, L12_2, L13_2)
                  L11_2 = L3_2
                  L12_2 = L4_2[L9_2]
                  L13_2 = A1_2[L9_2]
                  L13_2 = L10_2[L13_2]
                  L11_2[L12_2] = L13_2
                end
              end
            end
          end
        end
      end
      L4_2 = ExecuteBuildingBlocksFunction
      L5_2 = L2_2
      L6_2 = L3_2
      L4_2(L5_2, L6_2)
      L4_2 = 1
      L5_2 = 6
      L6_2 = 1
      for L7_2 = L4_2, L5_2, L6_2 do
        L8_2 = "FunctionOutput"
        L9_2 = L7_2
        L10_2 = "Var"
        L8_2 = L8_2 .. L9_2 .. L10_2
        L9_2 = A1_2[L8_2]
        if L9_2 ~= nil then
          L9_2 = A1_2[L8_2]
          if L9_2 ~= "" then
            L9_2 = L3_2
            L10_2 = GetTable
            L11_2 = A0_2
            L12_2 = L8_2
            L13_2 = "Table"
            L12_2 = L12_2 .. L13_2
            L12_2 = A1_2[L12_2]
            L13_2 = false
            L10_2 = L10_2(L11_2, L12_2, L13_2)
            L11_2 = A1_2[L8_2]
            L12_2 = L9_2[L8_2]
            L10_2[L11_2] = L12_2
          end
        end
      end
  end
  else
    L4_2 = A1_2.FunctionVarTable
    if L4_2 == nil then
      L4_2 = "PassThroughParams"
    end
    L5_2 = DebugError
    L6_2 = "Function variable "
    L7_2 = tostring
    L8_2 = L4_2
    L7_2 = L7_2(L8_2)
    L8_2 = "."
    L9_2 = tostring
    L10_2 = A1_2.FunctionVar
    L9_2 = L9_2(L10_2)
    L10_2 = " not initialized."
    L6_2 = L6_2 .. L7_2 .. L8_2 .. L9_2 .. L10_2
    L5_2(L6_2)
  end
end

BBRunFunction = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2, L4_2
  L1_2 = string
  L1_2 = L1_2.gsub
  L2_2 = A0_2
  L3_2 = "BBIf"
  L4_2 = "BBElseIf"
  L1_2 = L1_2(L2_2, L3_2, L4_2)
  elseIfFunctionName = L1_2
  L1_2 = _G
  L2_2 = elseIfFunctionName
  
  function L3_2(A0_3, A1_3, A2_3)
    local L3_3, L4_3, L5_3, L6_3
    L3_3 = A0_3._LastIfSucceeded
    if L3_3 == false then
      L3_3 = _G
      L4_3 = A0_2
      L3_3 = L3_3[L4_3]
      L4_3 = A0_3
      L5_3 = A1_3
      L6_3 = A2_3
      L3_3(L4_3, L5_3, L6_3)
    end
  end
  
  L1_2[L2_2] = L3_2
  L1_2 = string
  L1_2 = L1_2.gsub
  L2_2 = A0_2
  L3_2 = "BBIf"
  L4_2 = "BBAndIf"
  L1_2 = L1_2(L2_2, L3_2, L4_2)
  andIfFunctionName = L1_2
  L1_2 = _G
  L2_2 = andIfFunctionName
  
  function L3_2(A0_3, A1_3, A2_3)
    local L3_3, L4_3, L5_3, L6_3
    L3_3 = A0_3._LastIfSucceeded
    if L3_3 == true then
      L3_3 = _G
      L4_3 = A0_2
      L3_3 = L3_3[L4_3]
      L4_3 = A0_3
      L5_3 = A1_3
      L6_3 = A2_3
      L3_3(L4_3, L5_3, L6_3)
    end
  end
  
  L1_2[L2_2] = L3_2
  L1_2 = string
  L1_2 = L1_2.gsub
  L2_2 = A0_2
  L3_2 = "BBIf"
  L4_2 = "BBOrIf"
  L1_2 = L1_2(L2_2, L3_2, L4_2)
  orIfFunctionName = L1_2
  L1_2 = _G
  L2_2 = orIfFunctionName
  
  function L3_2(A0_3, A1_3, A2_3)
    local L3_3, L4_3, L5_3, L6_3
    L3_3 = A0_3._LastIfSucceeded
    if L3_3 == true then
      L3_3 = ExecuteBuildingBlocksDefault
      L4_3 = A2_3
      L5_3 = A0_3
      L3_3(L4_3, L5_3)
      A0_3._LastIfSucceeded = true
    else
      L3_3 = _G
      L4_3 = A0_2
      L3_3 = L3_3[L4_3]
      L4_3 = A0_3
      L5_3 = A1_3
      L6_3 = A2_3
      L3_3(L4_3, L5_3, L6_3)
    end
  end
  
  L1_2[L2_2] = L3_2
end

MakeOtherIfFunctions = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIf"
L0_1(L1_1)

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = A0_2._LastIfSucceeded
  if L3_2 == false then
    L3_2 = ExecuteBuildingBlocksDefault
    L4_2 = A2_2
    L5_2 = A0_2
    L3_2(L4_2, L5_2)
    A0_2._LastIfSucceeded = true
  end
end

BBElse = L0_1

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
    L5_2 = ExecuteBuildingBlocksDefault
    L6_2 = A2_2
    L7_2 = A0_2
    L5_2(L6_2, L7_2)
    A0_2._LastIfSucceeded = true
  else
    A0_2._LastIfSucceeded = false
  end
end

BBIfHasBuffOfType = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasBuffOfType"
L0_1(L1_1)

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L4_2 = A1_2.TargetVar
  if L4_2 ~= nil then
    L4_2 = A1_2.TargetVar
    L3_2 = A0_2[L4_2]
  else
    L3_2 = A0_2.Target
  end
  L4_2 = GetParam
  L5_2 = "Team"
  L6_2 = A0_2
  L7_2 = A1_2
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = nil
  L6_2 = A1_2.ExcludeSelfBuffs
  if L6_2 ~= nil then
    L5_2 = A1_2.ExcludeSelfBuffs
  else
    L5_2 = false
  end
  L6_2 = HasBuffOfTypeFromTeam
  L7_2 = L3_2
  L8_2 = A1_2.BuffType
  L9_2 = L4_2
  L10_2 = L5_2
  L6_2 = L6_2(L7_2, L8_2, L9_2, L10_2)
  if L6_2 then
    L7_2 = ExecuteBuildingBlocksDefault
    L8_2 = A2_2
    L9_2 = A0_2
    L7_2(L8_2, L9_2)
    A0_2._LastIfSucceeded = true
  else
    A0_2._LastIfSucceeded = false
  end
end

BBIfHasBuffOfTypeFromTeam = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasBuffOfTypeFromTeam"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasBuffOfTypeHardCC"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasBuffOfTypeCC"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasBuffOfTypeMovementBlocker"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasBuffOfTypeActionBlocker"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfBuffTypeIsHardCC"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfBuffTypeIsCC"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfBuffTypeIsMovementBlocker"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfBuffTypeIsActionBlocker"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfBuffTypeInterruptsChannels"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfLineSegmentIntersectsLineSegment"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfLineSegmentIntersectsCircle"
L0_1(L1_1)

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L3_2 = GetTable
  L4_2 = A0_2
  L5_2 = A1_2.SrcTableVarTable
  L6_2 = false
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetParam
  L5_2 = "SrcKey"
  L6_2 = A0_2
  L7_2 = A1_2
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = false
  L6_2 = type
  L7_2 = A1_2.SrcTableVar
  L7_2 = L3_2[L7_2]
  L6_2 = L6_2(L7_2)
  if L6_2 == "table" then
    L6_2 = A1_2.SrcTableVar
    L6_2 = L3_2[L6_2]
    L6_2 = L6_2[L4_2]
    if L6_2 ~= nil then
      L6_2 = ExecuteBuildingBlocksDefault
      L7_2 = A2_2
      L8_2 = A0_2
      L6_2(L7_2, L8_2)
      L5_2 = true
    end
  end
  A0_2._LastIfSucceeded = L5_2
end

BBIfHasKeyInCustomTable = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasKeyInCustomTable"
L0_1(L1_1)

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2
  L4_2 = A1_2.TargetVar
  if L4_2 ~= nil then
    L4_2 = A1_2.TargetVar
    L3_2 = A0_2[L4_2]
  else
    L3_2 = A0_2.Owner
  end
  L4_2 = HasUnitTag
  L5_2 = L3_2
  L6_2 = A1_2.UnitTag
  L4_2 = L4_2(L5_2, L6_2)
  L5_2 = A1_2.InvertResult
  if L4_2 ~= L5_2 then
    L4_2 = ExecuteBuildingBlocksDefault
    L5_2 = A2_2
    L6_2 = A0_2
    L4_2(L5_2, L6_2)
    A0_2._LastIfSucceeded = true
  else
    A0_2._LastIfSucceeded = false
  end
end

BBIfHasUnitTag = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfHasUnitTag"
L0_1(L1_1)

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
    L6_2 = ExecuteBuildingBlocksDefault
    L7_2 = A2_2
    L8_2 = A0_2
    L6_2(L7_2, L8_2)
    A0_2._LastIfSucceeded = true
  else
    A0_2._LastIfSucceeded = false
  end
end

BBIfPARTypeNotEquals = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfPARTypeNotEquals"
L0_1(L1_1)

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

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.log10
  L2_2 = A0_2
  return L1_2(L2_2)
end

MO_LOG = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2
  L2_2 = math
  L2_2 = L2_2.floor
  L3_2 = A0_2 / A1_2
  return L2_2(L3_2)
end

MO_INT_DIVIDE = L0_1

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

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = math
  L1_2 = L1_2.deg
  L2_2 = math
  L2_2 = L2_2.asin
  L3_2 = A0_2
  L2_2, L3_2 = L2_2(L3_2)
  return L1_2(L2_2, L3_2)
end

MO_ASIN = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = math
  L1_2 = L1_2.deg
  L2_2 = math
  L2_2 = L2_2.acos
  L3_2 = A0_2
  L2_2, L3_2 = L2_2(L3_2)
  return L1_2(L2_2, L3_2)
end

MO_ACOS = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = math
  L1_2 = L1_2.deg
  L2_2 = math
  L2_2 = L2_2.atan
  L3_2 = A0_2
  L2_2, L3_2 = L2_2(L3_2)
  return L1_2(L2_2, L3_2)
end

MO_ATAN = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = math
  L2_2 = L2_2.pow
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

MO_POW = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.sqrt
  L2_2 = A0_2
  return L1_2(L2_2)
end

MO_SQUARE_ROOT = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 or nil
  if A0_2 then
    L2_2 = A1_2
  end
  return L2_2
end

MO_BOOLEAN_AND = L0_1

function L0_1(A0_2, A1_2)
  local L2_2
  L2_2 = A0_2 or nil
  if not A0_2 then
    L2_2 = A1_2
  end
  return L2_2
end

MO_BOOLEAN_OR = L0_1

function L0_1(A0_2)
  local L1_2
  L1_2 = not A0_2
  return L1_2
end

MO_BOOLEAN_NOT = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.abs
  L2_2 = A0_2
  return L1_2(L2_2)
end

MO_ABS = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = GetRandomIntInRangeLua
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

MO_RAND_INT_RANGE = L0_1

function L0_1(A0_2)
  local L1_2
  L1_2 = 1
  out = L1_2
  while 0 < A0_2 do
    L1_2 = out
    L1_2 = L1_2 * A0_2
    out = L1_2
    A0_2 = A0_2 - 1
  end
  L1_2 = out
  return L1_2
end

MO_FACTORIAL = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.rad
  L2_2 = A0_2
  return L1_2(L2_2)
end

MO_DEGTORAD = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = math
  L1_2 = L1_2.deg
  L2_2 = A0_2
  return L1_2(L2_2)
end

MO_RADTODEG = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = ExecuteBuildingBlocksDefault
  L4_2 = A2_2
  L5_2 = A0_2
  L3_2(L4_2, L5_2)
end

BBFreeformMath = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2
  L2_2 = GetMathNumber
  L3_2 = A0_2
  L4_2 = A1_2.Src1VarTable
  L5_2 = A1_2.Src1Var
  L6_2 = A1_2.Src1
  L2_2 = L2_2(L3_2, L4_2, L5_2, L6_2)
  L3_2 = GetMathNumber
  L4_2 = A0_2
  L5_2 = A1_2.Src2VarTable
  L6_2 = A1_2.Src2Var
  L7_2 = A1_2.Src2
  L3_2 = L3_2(L4_2, L5_2, L6_2, L7_2)
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.DestVarTable
  L4_2 = L4_2(L5_2, L6_2)
  L5_2 = nil
  L6_2 = nil
  L7_2 = pcall
  L8_2 = A1_2.MathOp
  L9_2 = L2_2
  L10_2 = L3_2
  L7_2, L8_2 = L7_2(L8_2, L9_2, L10_2)
  L5_2 = L8_2
  L6_2 = L7_2
  if not L6_2 then
    L7_2 = ReportError
    L8_2 = L5_2
    L7_2(L8_2)
    return
  end
  L7_2 = SetVarInTable
  L8_2 = A0_2
  L9_2 = A1_2
  L10_2 = L5_2
  L7_2(L8_2, L9_2, L10_2)
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
  local L2_2, L3_2, L4_2
  L2_2 = VectorAdd
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_ADD = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = VectorSubtract
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_SUBTRACT = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = VectorScalarMultiply
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_SCALAR_MULTIPLY = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = VectorScalarDivide
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_SCALAR_DIVIDE = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = VectorRotateY
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_ROTATE = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = VectorNormalizeIgnoreY
  L2_2 = A0_2
  return L1_2(L2_2)
end

VEC_NORMALIZE = L0_1

function L0_1(A0_2)
  local L1_2, L2_2
  L1_2 = VectorLengthIgnoreY
  L2_2 = A0_2
  return L1_2(L2_2)
end

VEC_LENGTH = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = VectorDotProductIgnoreY
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_DOT_IGNORE_Y = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = VectorCrossProductIgnoreY
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_CROSS_IGNORE_Y = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = VectorAngleIgnoreY
  L3_2 = A0_2
  L4_2 = A1_2
  return L2_2(L3_2, L4_2)
end

VEC_ANGLE_IGNORE_Y = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  L2_2 = BBMath
  L3_2 = A0_2
  L4_2 = A1_2
  L2_2(L3_2, L4_2)
end

BBVectorMath = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = ExecuteBuildingBlocksDefault
  L4_2 = A2_2
  L5_2 = A0_2
  L3_2(L4_2, L5_2)
end

BBFormatString = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2
  L3_2 = A1_2.TargetVar
  if L3_2 ~= nil then
    L4_2 = GetTeamID
    L5_2 = A0_2[L3_2]
    L4_2 = L4_2(L5_2)
    L2_2 = L4_2
  else
    L4_2 = GetTeamID
    L4_2 = L4_2()
    L2_2 = L4_2
  end
  L4_2 = SetVarInTable
  L5_2 = A0_2
  L6_2 = A1_2
  L7_2 = L2_2
  L4_2(L5_2, L6_2, L7_2)
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
  L4_2 = nil
  if L3_2 ~= nil then
    L5_2 = GetTeamID
    L6_2 = A0_2[L3_2]
    L5_2 = L5_2(L6_2)
    L4_2 = L5_2
  else
    L5_2 = GetTeamID
    L5_2 = L5_2()
    L4_2 = L5_2
  end
  L5_2 = TEAM_ORDER
  if L4_2 == L5_2 then
    L5_2 = A1_2.DestVar
    L6_2 = TEAM_CHAOS
    L2_2[L5_2] = L6_2
  else
    L5_2 = TEAM_CHAOS
    if L4_2 == L5_2 then
      L5_2 = A1_2.DestVar
      L6_2 = TEAM_ORDER
      L2_2[L5_2] = L6_2
    end
  end
end

BBGetEnemyTeamID = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L3_2 = 0
  L4_2 = GetParam
  L5_2 = "TimeBetweenExecutions"
  L6_2 = A0_2
  L7_2 = A1_2
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = GetTime
  L5_2 = L5_2()
  L6_2 = GetTable
  L7_2 = A0_2
  L8_2 = A1_2.TrackTimeVarTable
  L9_2 = false
  L6_2 = L6_2(L7_2, L8_2, L9_2)
  L7_2 = A1_2.TrackTimeVar
  L7_2 = L6_2[L7_2]
  if L7_2 == nil then
    L7_2 = A1_2.TrackTimeVar
    L6_2[L7_2] = L5_2
    L3_2 = L5_2
    L7_2 = A1_2.ExecuteImmediately
    if L7_2 == true then
      L7_2 = ExecuteBuildingBlocksDefault
      L8_2 = A2_2
      L9_2 = A0_2
      L7_2(L8_2, L9_2)
    end
  else
    L7_2 = A1_2.TrackTimeVar
    L3_2 = L6_2[L7_2]
  end
  L7_2 = L3_2 + L4_2
  if L5_2 >= L7_2 then
    L7_2 = A1_2.TrackTimeVar
    L8_2 = L3_2 + L4_2
    L6_2[L7_2] = L8_2
    L7_2 = ExecuteBuildingBlocksDefault
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

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2, L6_2
  L3_2 = IfDamageHasTags
  L4_2 = A1_2.RequiredTags
  L5_2 = A1_2.ExcludedTags
  L3_2 = L3_2(L4_2, L5_2)
  if L3_2 then
    L4_2 = ExecuteBuildingBlocksDefault
    L5_2 = A2_2
    L6_2 = A0_2
    L4_2(L5_2, L6_2)
    A0_2._LastIfSucceeded = true
  else
    A0_2._LastIfSucceeded = false
  end
end

BBIfDamageHasTags = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfDamageHasTags"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfRunningNpcScript"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfNotRunningNpcScript"
L0_1(L1_1)

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2
  A1_2.TimeoutInFOW = 999999
  A1_2.BindFlexToOwnerPAR = false
  A1_2.Flags = 0
  A1_2.FollowsGroundTilt = false
  A1_2.FacesTarget = false
  A1_2.HideFromSpectator = false
  A1_2.SendIfOnScreenOrDiscard = true
  A1_2.PersistsThroughReconnect = false
  A1_2.FOWVisibilityRadius = 10
  A1_2.Scale = 1
  L2_2 = A1_2.FOWTeamVar
  A1_2.FOWTeamOverrideVar = L2_2
  L2_2 = A1_2.ParticleFile
  A1_2.EffectName = L2_2
  L2_2 = A1_2.ParticleFileForOtherTeam
  A1_2.EffectNameForOtherTeam = L2_2
  L2_2 = A1_2.BindObjectBoneName
  A1_2.BoneName = L2_2
  L2_2 = BBSpellEffectCreate
  L3_2 = A0_2
  L4_2 = A1_2
  L2_2(L3_2, L4_2)
end

BBSpellEffectCreate_EasyHit = L0_1

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
  local L2_2, L3_2, L4_2, L5_2
  L2_2 = GetParam
  L3_2 = "NewRange"
  L4_2 = A0_2
  L5_2 = A1_2
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = SetSpellCastRange
  L4_2 = L2_2
  L3_2(L4_2)
end

BBSetSpellCastRange = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2
  L2_2 = GetParam
  L3_2 = "Point1"
  L4_2 = A0_2
  L5_2 = A1_2
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = GetParam
  L4_2 = "Point2"
  L5_2 = A0_2
  L6_2 = A1_2
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.DestVarTable
  L7_2 = true
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.DestVar
  L6_2 = DistanceBetweenPoints
  L7_2 = L2_2
  L8_2 = L3_2
  L6_2 = L6_2(L7_2, L8_2)
  L4_2[L5_2] = L6_2
end

BBDistanceBetweenPoints = L0_1

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = A0_2.EmoteId
  L4_2 = A1_2.EmoteId
  if L3_2 == L4_2 then
    L3_2 = ExecuteBuildingBlocksDefault
    L4_2 = A2_2
    L5_2 = A0_2
    L3_2(L4_2, L5_2)
    A0_2._LastIfSucceeded = true
  else
    A0_2._LastIfSucceeded = false
  end
end

BBIfEmoteIs = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfEmoteIs"
L0_1(L1_1)

function L0_1(A0_2, A1_2, A2_2)
  local L3_2, L4_2, L5_2
  L3_2 = A0_2.EmoteId
  L4_2 = A1_2.EmoteId
  if L3_2 ~= L4_2 then
    L3_2 = ExecuteBuildingBlocksDefault
    L4_2 = A2_2
    L5_2 = A0_2
    L3_2(L4_2, L5_2)
    A0_2._LastIfSucceeded = true
  else
    A0_2._LastIfSucceeded = false
  end
end

BBIfEmoteIsNot = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfEmoteIsNot"
L0_1(L1_1)

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2
  L2_2 = GetTable
  L3_2 = A0_2
  L4_2 = A1_2.String1VarTable
  L5_2 = false
  L2_2 = L2_2(L3_2, L4_2, L5_2)
  L3_2 = A1_2.String1Var
  L3_2 = L2_2[L3_2]
  L4_2 = GetTable
  L5_2 = A0_2
  L6_2 = A1_2.String2VarTable
  L7_2 = false
  L4_2 = L4_2(L5_2, L6_2, L7_2)
  L5_2 = A1_2.String2Var
  L5_2 = L4_2[L5_2]
  L6_2 = GetTable
  L7_2 = A0_2
  L8_2 = A1_2.ResultVarTable
  L9_2 = false
  L6_2 = L6_2(L7_2, L8_2, L9_2)
  L7_2 = A1_2.ResultVar
  L8_2 = L3_2
  L9_2 = L5_2
  L8_2 = L8_2 .. L9_2
  L6_2[L7_2] = L8_2
end

BBConcatenateStrings = L0_1

function L0_1(A0_2, A1_2)
  local L2_2, L3_2, L4_2, L5_2, L6_2
  L2_2 = BBGetMinionKills
  L3_2 = A0_2
  L4_2 = A1_2
  L2_2(L3_2, L4_2)
  L2_2 = A0_2.MinionsKilled
  L3_2 = GetParam
  L4_2 = "MinionKills"
  L5_2 = A0_2
  L6_2 = A1_2
  L3_2 = L3_2(L4_2, L5_2, L6_2)
  L4_2 = GetParam
  L5_2 = "MinionKillTarget"
  L4_2 = L4_2(L5_2)
  A0_2.MinionKillSource = L4_2
  L4_2 = L2_2 + L3_2
  A0_2.MinionKills = L4_2
  L4_2 = BBSetMinionKills
  L5_2 = A0_2
  L6_2 = A1_2
  L4_2(L5_2, L6_2)
end

BBIncreaseMinionKills = L0_1

function L0_1(A0_2, A1_2)
end

BBForcePreload = L0_1
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfUnitIsInCombat"
L0_1(L1_1)
L0_1 = MakeOtherIfFunctions
L1_1 = "BBIfUnitIsNOTInCombat"
L0_1(L1_1)
