local L0_1, L1_1, L2_1, L3_1
L0_1 = {}
L1_1 = {}
L2_1 = BBIncStat
L1_1.Function = L2_1
L2_1 = {}
L3_1 = IncPercentArmorPenetrationMod
L2_1.Stat = L3_1
L2_1.TargetVar = "Owner"
L2_1.Delta = 0.1
L1_1.Params = L2_1
L0_1[1] = L1_1
UpdateSelfBuffStatsBuildingBlocks = L0_1
