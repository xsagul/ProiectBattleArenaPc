local L0_1, L1_1, L2_1, L3_1
L0_1 = "Janna_Tailwind.dds"
BuffTextureName = L0_1
L0_1 = "Tailwind"
BuffName = L0_1
L0_1 = {}
L1_1 = {}
L2_1 = BBIncStat
L1_1.Function = L2_1
L2_1 = {}
L3_1 = IncPercentMovementSpeedMod
L2_1.Stat = L3_1
L2_1.TargetVar = "Owner"
L2_1.Delta = 0.03
L1_1.Params = L2_1
L0_1[1] = L1_1
BuffOnUpdateStatsBuildingBlocks = L0_1
