local L0_1, L1_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2, L4_2, L5_2
  L0_2 = CreateChildTurret
  L1_2 = "Turret_OrderTurretShrine"
  L2_2 = "OdinOrderTurretShrine"
  L3_2 = TEAM_ORDER
  L4_2 = 1
  L5_2 = 0
  L0_2(L1_2, L2_2, L3_2, L4_2, L5_2)
  L0_2 = CreateChildTurret
  L1_2 = "Turret_ChaosTurretShrine"
  L2_2 = "OdinChaosTurretShrine"
  L3_2 = TEAM_CHAOS
  L4_2 = 1
  L5_2 = 0
  L0_2(L1_2, L2_2, L3_2, L4_2, L5_2)
  L0_2 = CreateChildTurret
  L1_2 = "Turret_OrderTurretShrine1"
  L2_2 = "OdinOrderTurretShrine"
  L3_2 = TEAM_ORDER
  L4_2 = 2
  L5_2 = 0
  L0_2(L1_2, L2_2, L3_2, L4_2, L5_2)
  L0_2 = CreateChildTurret
  L1_2 = "Turret_ChaosTurretShrine1"
  L2_2 = "OdinChaosTurretShrine"
  L3_2 = TEAM_CHAOS
  L4_2 = 2
  L5_2 = 0
  L0_2(L1_2, L2_2, L3_2, L4_2, L5_2)
end

CreateLevelProps = L0_1
