local L0_1, L1_1

function L0_1()
  local L0_2, L1_2, L2_2, L3_2, L4_2, L5_2
  L0_2 = CreateChildTurret
  L1_2 = "Turret_T1_C_07"
  L2_2 = "OrderTurretTutorial"
  L3_2 = TEAM_ORDER
  L4_2 = 1
  L5_2 = 1
  L0_2(L1_2, L2_2, L3_2, L4_2, L5_2)
  L0_2 = CreateChildTurret
  L1_2 = "Turret_T1_C_08"
  L2_2 = "OrderTurretTutorial"
  L3_2 = TEAM_ORDER
  L4_2 = 2
  L5_2 = 1
  L0_2(L1_2, L2_2, L3_2, L4_2, L5_2)
  L0_2 = CreateChildTurret
  L1_2 = "Turret_T2_L_01"
  L2_2 = "ChaosTurretTutorial"
  L3_2 = TEAM_CHAOS
  L4_2 = 1
  L5_2 = 1
  L0_2(L1_2, L2_2, L3_2, L4_2, L5_2)
end

CreateLevelProps = L0_1
