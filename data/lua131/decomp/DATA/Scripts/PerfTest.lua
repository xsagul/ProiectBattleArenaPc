local L0_1, L1_1

function L0_1()
  local L0_2, L1_2, L2_2
  L0_2 = ClientCheat_SpawnMinion
  L1_2 = "Bear"
  L2_2 = 100
  L0_2(L1_2, L2_2)
  L0_2 = ClientCheat_SpawnMinion
  L1_2 = "Skeleton_Minion_Melee"
  L2_2 = 100
  L0_2(L1_2, L2_2)
  L0_2 = ClientCheat_SpawnMinion
  L1_2 = "Skeleton_Minion_Rider"
  L2_2 = 100
  L0_2(L1_2, L2_2)
  L0_2 = ClientCheat_SpawnMinion
  L1_2 = "Skeleton_Minion_Archer"
  L2_2 = 100
  L0_2(L1_2, L2_2)
  L0_2 = ClientCheat_SpawnMinion
  L1_2 = "Order_Minion_Archer"
  L2_2 = 100
  L0_2(L1_2, L2_2)
  L0_2 = ClientCheat_SpawnMinion
  L1_2 = "Order_Minion_Melee"
  L2_2 = 100
  L0_2(L1_2, L2_2)
  L0_2 = ClientCheat_SpawnMinion
  L1_2 = "Order_Minion_Rider"
  L2_2 = 100
  L0_2(L1_2, L2_2)
end

SpawnSomeMinions = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2, L4_2, L5_2, L6_2, L7_2, L8_2, L9_2, L10_2, L11_2
  L0_2 = 200
  spacing = L0_2
  L0_2 = 5
  numRows = L0_2
  L0_2 = 5
  numColumns = L0_2
  L0_2 = spacing
  L1_2 = numRows
  L1_2 = L1_2 - 1
  L0_2 = L0_2 * L1_2
  L0_2 = L0_2 / 2
  L0_2 = 6044 - L0_2
  xo = L0_2
  L0_2 = 62.5
  yo = L0_2
  L0_2 = spacing
  L1_2 = numColumns
  L1_2 = L1_2 - 1
  L0_2 = L0_2 * L1_2
  L0_2 = L0_2 / 2
  L0_2 = 5983 - L0_2
  zo = L0_2
  L0_2 = 0
  L1_2 = numRows
  L1_2 = L1_2 - 1
  L2_2 = 1
  for L3_2 = L0_2, L1_2, L2_2 do
    L4_2 = zo
    L5_2 = spacing
    L5_2 = L3_2 * L5_2
    L4_2 = L4_2 + L5_2
    z = L4_2
    L4_2 = 0
    L5_2 = numColumns
    L5_2 = L5_2 - 1
    L6_2 = 1
    for L7_2 = L4_2, L5_2, L6_2 do
      L8_2 = xo
      L9_2 = spacing
      L9_2 = L7_2 * L9_2
      L8_2 = L8_2 + L9_2
      x = L8_2
      L8_2 = Make3DPoint
      L9_2 = x
      L10_2 = yo
      L11_2 = z
      L8_2 = L8_2(L9_2, L10_2, L11_2)
      spawnLocation = L8_2
      L8_2 = CreateGameObject
      L9_2 = "obj_GeneralParticleEmmiter"
      L10_2 = "Data\\Particles\\WorkInProgress.troy"
      L11_2 = spawnLocation
      L8_2(L9_2, L10_2, L11_2)
    end
  end
end

SpawnSomeParticles = L0_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2
  L0_2 = ClientCheat_ToggleFogOfWar
  L0_2()
  L0_2 = ClientCheat_ToggleInvulnerable
  L0_2()
  L0_2 = ClientCheat_ToggleBarracks
  L0_2()
  L0_2 = SpawnSomeParticles
  L0_2()
  L0_2 = r3dParticleSystem_SetFlags
  L1_2 = 1
  L0_2(L1_2)
  L0_2 = ParticleSystem_SetFlags
  L1_2 = 1
  L0_2(L1_2)
  L0_2 = InitTimer
  L1_2 = "PerfTest_BeginMeasurement"
  L2_2 = 15
  L3_2 = false
  L0_2(L1_2, L2_2, L3_2)
  L0_2 = InitTimer
  L1_2 = "PerfTest_EndMeasurement"
  L2_2 = 30
  L3_2 = false
  L0_2(L1_2, L2_2, L3_2)
end

PerfTest_Run = L0_1
