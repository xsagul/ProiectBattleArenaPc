local L0_1, L1_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2
  L1_2 = 0.3
  L2_2 = GetMP
  L2_2 = L2_2()
  L3_2 = GetTarget
  L3_2 = L3_2()
  if L3_2 then
    L3_2 = GetMaxMP
    L3_2 = L3_2()
    L3_2 = L2_2 / L3_2
    L3_2 = L3_2 * 0.8
    L3_2 = L3_2 * 2
    L3_2 = L3_2 * L1_2
    A0_2.Priority = L3_2
    L3_2 = true
    return L3_2
  end
  A0_2.Priority = 0
end

UpdatePriority = L0_1

function L0_1(A0_2)
  local L1_2, L2_2, L3_2, L4_2
  L1_2 = 0
  while true do
    L2_2 = math
    L2_2 = L2_2.random
    L3_2 = 0
    L4_2 = 3
    L2_2 = L2_2(L3_2, L4_2)
    L3_2 = CanUseSpell
    L4_2 = L2_2
    L3_2 = L3_2(L4_2)
    if L3_2 == 0 then
      if L2_2 == 0 then
        L3_2 = Say
        L4_2 = "PURITY NOW!"
        L3_2(L4_2)
      end
      if L2_2 == 1 then
        L3_2 = Say
        L4_2 = "I BLESS THEE"
        L3_2(L4_2)
      end
      if L2_2 == 2 then
        L3_2 = Say
        L4_2 = "EAT STARZ!"
        L3_2(L4_2)
      end
      if L2_2 == 3 then
        L3_2 = Say
        L4_2 = "WISH GRANTED!"
        L3_2(L4_2)
      end
      L3_2 = ServerCastSpell
      L4_2 = L2_2
      L3_2(L4_2)
      return
    end
    if 20 < L1_2 then
      return
    end
    L1_2 = L1_2 + 1
  end
end

BeginTask = L0_1

function L0_1(A0_2)
  local L1_2
end

Tick = L0_1

function L0_1()
  local L0_2, L1_2
end

OnLevelUp = L0_1

function L0_1(A0_2)
  local L1_2
end

OnTargetLost = L0_1
